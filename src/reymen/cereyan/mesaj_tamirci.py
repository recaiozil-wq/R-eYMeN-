# -*- coding: utf-8 -*-
"""Mesaj sıralı tamiri ve sanitizasyon.

ReYMeN agent'ın agent_runtime_helpers.py'sindeki aşağıdaki fonksiyonların
ReYMeN için adapte edilmiş versiyonları:
  - sanitize_tool_call_arguments  → arac_cagri_argumanlarini_temizle
  - repair_message_sequence       → mesaj_siralamasi_tamir_et

Hem ReYMeN'in text-parse döngüsünde hem de FC (native function calling)
modunda API'ye göndermeden önce mesaj geçmişini güvenli hale getirir.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger("conversation_loop")

# Corrupted tool call arguments için eklenen işaret
_BOZUK_ARGUMAN_ISARETI = "[Uyarı: orijinal araç çağrısı argümanları bozuktu — boş {} kullanıldı]"


def arac_cagri_argumanlarini_temizle(
    mesajlar: list,
    *,
    oturum_id: str = "",
) -> int:
    """Bozuk assistant tool-call argüman JSON'ını yerinde onar.

    LLM bazen geçersiz JSON üretebilir (eksik kapanış, surrogate chars, vb.).
    Bu fonksiyon mesaj geçmişini tarar, bozuk argümanları `{}` ile değiştirir
    ve karşılık gelen tool result mesajına uyarı işareti ekler.

    Returns:
        Tamir edilen tool call sayısı.
    """
    if not isinstance(mesajlar, list):
        return 0

    tamirler = 0

    def _isaret_ekle(arac_mesaj: dict) -> None:
        mevcut = arac_mesaj.get("content")
        if isinstance(mevcut, str):
            if not mevcut:
                arac_mesaj["content"] = _BOZUK_ARGUMAN_ISARETI
            elif not mevcut.startswith(_BOZUK_ARGUMAN_ISARETI):
                arac_mesaj["content"] = f"{_BOZUK_ARGUMAN_ISARETI}\n{mevcut}"
            return
        if mevcut is None:
            arac_mesaj["content"] = _BOZUK_ARGUMAN_ISARETI
            return
        try:
            mevcut_metin = json.dumps(mevcut)
        except TypeError:
            mevcut_metin = str(mevcut)
        arac_mesaj["content"] = f"{_BOZUK_ARGUMAN_ISARETI}\n{mevcut_metin}"

    idx = 0
    while idx < len(mesajlar):
        msg = mesajlar[idx]
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            idx += 1
            continue

        arac_cagrilari = msg.get("tool_calls")
        if not isinstance(arac_cagrilari, list) or not arac_cagrilari:
            idx += 1
            continue

        ekle_konumu = idx + 1
        for arac_cagrisi in arac_cagrilari:
            if not isinstance(arac_cagrisi, dict):
                continue
            fonk = arac_cagrisi.get("function")
            if not isinstance(fonk, dict):
                continue

            argumanlar = fonk.get("arguments")
            if argumanlar is None or argumanlar == "":
                fonk["arguments"] = "{}"
                continue
            if isinstance(argumanlar, str) and not argumanlar.strip():
                fonk["arguments"] = "{}"
                continue
            if not isinstance(argumanlar, str):
                continue

            try:
                json.loads(argumanlar)
            except json.JSONDecodeError:
                cagri_id = arac_cagrisi.get("id")
                fonk_adi = fonk.get("name", "?")
                on_izleme = argumanlar[:80]
                log.warning(
                    "Bozuk tool_call argümanları API isteğinden önce tamir edildi "
                    "(oturum=%s, mesaj_idx=%s, cagri_id=%s, fonk=%s, onizleme=%r)",
                    oturum_id or "-",
                    idx,
                    cagri_id or "-",
                    fonk_adi,
                    on_izleme,
                )
                fonk["arguments"] = "{}"

                mevcut_arac_msg = None
                tarama_idx = idx + 1
                while tarama_idx < len(mesajlar):
                    aday = mesajlar[tarama_idx]
                    if not isinstance(aday, dict) or aday.get("role") != "tool":
                        break
                    if aday.get("tool_call_id") == cagri_id:
                        mevcut_arac_msg = aday
                        break
                    tarama_idx += 1

                if mevcut_arac_msg is None:
                    mesajlar.insert(
                        ekle_konumu,
                        _arac_sonuc_mesaji_olustur(
                            fonk_adi if fonk_adi != "?" else "",
                            _BOZUK_ARGUMAN_ISARETI,
                            cagri_id,
                        ),
                    )
                    ekle_konumu += 1
                else:
                    _isaret_ekle(mevcut_arac_msg)

                tamirler += 1

        idx += 1

    return tamirler


# ReYMeN uyumluluğu için alias
sanitize_tool_call_arguments = arac_cagri_argumanlarini_temizle


def mesaj_siralamasi_tamir_et(mesajlar: List[Dict]) -> int:
    """Canlı geçmişte kalan bozuk rol sırasını düzelt.

    Provider'lar (OpenAI, Anthropic, vb.) katı user/assistant sıralaması bekler:
    - İki ardışık user mesajı olmamalı
    - tool result, tool_calls içeren assistant'ı takip etmeli
    - Yetim tool mesajları (eşleşen assistant tool_call_id'si olmayan) silinmeli

    Uygulanan onarımlar:
      1. Yetim ``tool`` mesajları — atılır.
      2. Ardışık ``user`` mesajları — yeni satır ile birleştirilir.

    Returns:
        Uygulanan onarım sayısı.
    """
    if not mesajlar:
        return 0

    tamirler = 0

    # Geçiş 1: Bilinen assistant tool_call_id'lerine uymayan yetim
    # tool mesajlarını at.
    bilinen_arac_idleri: set = set()
    filtrelenmis: List[Dict] = []
    for msg in mesajlar:
        if not isinstance(msg, dict):
            filtrelenmis.append(msg)
            continue
        rol = msg.get("role")
        if rol == "assistant":
            bilinen_arac_idleri = set()
            for tc in (msg.get("tool_calls") or []):
                tc_id = tc.get("id") if isinstance(tc, dict) else None
                if tc_id:
                    bilinen_arac_idleri.add(tc_id)
            filtrelenmis.append(msg)
        elif rol == "tool":
            tc_id = msg.get("tool_call_id")
            if tc_id and tc_id in bilinen_arac_idleri:
                filtrelenmis.append(msg)
            else:
                tamirler += 1
                log.debug(
                    "Yetim tool mesajı atıldı (tool_call_id=%r bilinen ID'lerde yok)",
                    tc_id,
                )
        else:
            if rol == "user":
                bilinen_arac_idleri = set()
            filtrelenmis.append(msg)

    # Geçiş 2: Ardışık user mesajlarını birleştir (kullanıcı girdisi kaybolmasın).
    birlestirilmis: List[Dict] = []
    for msg in filtrelenmis:
        if (
            birlestirilmis
            and isinstance(msg, dict)
            and msg.get("role") == "user"
            and isinstance(birlestirilmis[-1], dict)
            and birlestirilmis[-1].get("role") == "user"
        ):
            onceki = birlestirilmis[-1]
            onceki_icerik = onceki.get("content", "")
            yeni_icerik = msg.get("content", "")
            # Yalnızca düz metin içeriği birleştir; multimodal (list) içeriği bırak
            if isinstance(onceki_icerik, str) and isinstance(yeni_icerik, str):
                onceki["content"] = (
                    (onceki_icerik + "\n\n" + yeni_icerik)
                    if onceki_icerik and yeni_icerik
                    else (onceki_icerik or yeni_icerik)
                )
                tamirler += 1
            else:
                birlestirilmis.append(msg)
        else:
            birlestirilmis.append(msg)

    # Sonuçları yerinde uygula
    mesajlar[:] = birlestirilmis
    return tamirler


# ReYMeN uyumluluğu için alias
repair_message_sequence = mesaj_siralamasi_tamir_et


def _arac_sonuc_mesaji_olustur(
    arac_adi: str,
    icerik: str,
    arac_cagri_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Bir tool result mesajı dict'i oluştur."""
    msg: Dict[str, Any] = {
        "role": "tool",
        "content": icerik,
    }
    if arac_cagri_id:
        msg["tool_call_id"] = arac_cagri_id
    if arac_adi:
        msg["name"] = arac_adi
    return msg


def surrogate_karakterleri_temizle(metin: str) -> str:
    """String'deki surrogate karakterleri güvenli şekilde kaldır.

    LLM yanıtlarında bazen geçersiz Unicode surrogate karakterler
    olabilir (özellikle bazı local modeller). Bunları encode/decode
    ile temizle.
    """
    if not isinstance(metin, str):
        return metin
    try:
        return metin.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return metin.encode("ascii", errors="replace").decode("ascii")
