# -*- coding: utf-8 -*-
"""
TTS Tool — Metni sese cevirir (edge-tts).
ReYMeN icin native TTS araci.

Kullanim:
    from reymen.sistem.tts_tool_text import metni_sese_cevir
    dosya = metni_sese_cevir("Merhaba dunya")
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import edge_tts

logger = logging.getLogger(__name__)

# Varsayilan ses
VARSAYILAN_SES = "tr-TR-EmelNeural"
VARSAYILAN_HIZ = "+0%"  # normal hiz
PROJE_KOKU = Path(__file__).resolve().parent.parent.parent
SES_ORNEKLEM = Path(PROJE_KOKU, "reymen", "ses_orneklem")
SES_ORNEKLEM.mkdir(parents=True, exist_ok=True)

# Ses listesi (onbellekli)
_SES_LISTESI: Optional[list[dict[str, str]]] = None


async def _sesleri_getir() -> list[dict[str, str]]:
    """edge-tts'den ses listesini al ve onbellekle."""
    global _SES_LISTESI
    if _SES_LISTESI is None:
        sesler = await edge_tts.list_voices()
        _SES_LISTESI = [
            {"ad": s["ShortName"], "dil": s.get("Locale", ""), "isim": s.get("FriendlyName", "")}
            for s in sesler
        ]
    return _SES_LISTESI


async def _metni_sese_cevir_async(
    metin: str,
    ses: str = VARSAYILAN_SES,
    hiz: str = VARSAYILAN_HIZ,
    ses_volumu: float = 1.0,
    cikti_yolu: Optional[str] = None,
) -> str:
    """Async olarak metni edge-tts ile sese cevir.

    Args:
        metin: Seslendirilecek metin.
        ses: Ses adi (ornek: tr-TR-EmelNeural).
        hiz: Hiz ayari (+0%, +20%, -10% gibi).
        ses_volumu: Ses seviyesi (0.0-1.0).
        cikti_yolu: Cikti dosya yolu (None=otomatik).

    Returns:
        Olusturulan ses dosyasinin yolu.
    """
    if not metin or not metin.strip():
        return "[HATA] metin parametresi gerekli."

    # Cikti yolu
    if cikti_yolu:
        cikti = Path(cikti_yolu)
    else:
        zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
        cikti = SES_ORNEKLEM / f"ses_{zaman}.mp3"

    try:
        ses_noktali = ses.replace("-", "+", 1) if "-" in ses and ses.count("-") > 1 else ses
        iletisim = edge_tts.Communicate(
            text=metin,
            voice=ses,
            rate=hiz,
            volume=f"+{int(ses_volumu * 100)}%" if ses_volumu > 0 else f"-{int(abs(ses_volumu - 1) * 100)}%",
        )
        await iletisim.save(str(cikti))

        if cikti.exists() and cikti.stat().st_size > 0:
            logger.info("[TTS] Ses olusturuldu: %s (%d bytes, ses=%s)", cikti, cikti.stat().st_size, ses)
            return str(cikti)
        return "[HATA] Ses dosyasi olusturulamadi."

    except Exception as e:
        logger.exception("[TTS] Ses olusturma hatasi: %s", e)
        return f"[HATA] {type(e).__name__}: {e}"


def metni_sese_cevir(
    metin: str,
    ses: str = VARSAYILAN_SES,
    hiz: str = VARSAYILAN_HIZ,
    ses_volumu: float = 1.0,
) -> str:
    """Metni sese cevir (senkron wrapper).

    Parametreler:
        metin: Seslendirilecek metin (zorunlu).
        ses: Ses adi (opsiyonel, varsayilan: tr-TR-EmelNeural).
        hiz: Hiz ayari (opsiyonel, varsayilan: +0%).
        ses_volumu: Ses seviyesi 0.0-1.0 (opsiyonel, varsayilan: 1.0).

    Doner:
        Ses dosyasi yolu veya hata mesaji.
    """
    return asyncio.run(_metni_sese_cevir_async(metin, ses, hiz, ses_volumu))


def ses_listesi(dil_filtre: str = "") -> str:
    """Kullanilabilir sesleri listele.

    Parametre:
        dil_filtre: Dil kodu filtresi (ornek: 'tr', 'en').
                    Bos birakilirsa tum sesler listelenir.

    Doner:
        Ses listesi (metin).
    """
    sesler = asyncio.run(_sesleri_getir())
    if dil_filtre:
        sesler = [s for s in sesler if s["dil"].startswith(dil_filtre)]
    if not sesler:
        return "Ses bulunamadi."

    satirlar = ["=== Kullanilabilir Sesler ==="]
    for s in sesler:
        satirlar.append(f"  {s['ad']} ({s['dil']})")
    return "\n".join(satirlar[:30]) + (f"\n  ... +{len(sesler)-30} ses daha" if len(sesler) > 30 else "")


# ── Motor kayit ──────────────────────────────────────────────────────────────

def motor_kaydet(motor: Any) -> None:
    """Motor'a TTS araclarini kaydet."""

    def _tts_konus(metin: str, ses: str = VARSAYILAN_SES) -> str:
        """TTS_KONUS: Metni sese cevir.

        Parametreler:
            metin (str, zorunlu) — Seslendirilecek metin.
            ses (str, opsiyonel) — Ses adi (varsayilan: tr-TR-EmelNeural).

        Doner: Ses dosyasi yolu.
        """
        return metni_sese_cevir(metin, ses)

    def _tts_sesler(dil: str = "") -> str:
        """TTS_SESLER: Kullanilabilir sesleri listele.

        Parametre:
            dil (str, opsiyonel) — Dil kodu (ornek: 'tr', 'en').
        """
        return ses_listesi(dil)

    def _tts_test() -> str:
        """TTS_TEST: TTS sistemini test et. Kisa bir test sesi olusturur."""
        sonuc = metni_sese_cevir("Merhaba, ben ReyMen. Ses sistemim calisiyor.")
        if sonuc.startswith("[HATA]"):
            return f"❌ TTS test basarisiz: {sonuc}"
        return f"✅ TTS test basarili: {sonuc}"

    if hasattr(motor, "_plugin_arac_kaydet"):
        motor._plugin_arac_kaydet("TTS_KONUS", _tts_konus,
            "Metni sese cevirir (edge-tts). "
            "Parametreler: metin (str, zorunlu) — seslendirilecek metin; "
            "ses (str, opsiyonel) — ses adi (varsayilan: tr-TR-EmelNeural). "
            "Doner: ses dosyasi yolu.")
        motor._plugin_arac_kaydet("TTS_SESLER", _tts_sesler,
            "Kullanilabilir sesleri listeler. "
            "Parametre: dil (str, opsiyonel) — dil kodu filtresi (ornek: 'tr', 'en').")
        motor._plugin_arac_kaydet("TTS_TEST", _tts_test,
            "TTS sistemini test eder. Kisa bir test sesi olusturur.")

        logger.info("[TTS] Motor araclari kaydedildi: TTS_KONUS, TTS_SESLER, TTS_TEST")


if __name__ == "__main__":
    # Test
    print(metni_sese_cevir("Merhaba, bu bir test konusmasi."))
    print(ses_listesi("tr"))
