# -*- coding: utf-8 -*-
"""
reymen_agent.py — ReYMeN ana agent modülü.
DeepSoek API, agent orchestrator, beceri bağlamı ve format temizleme.
"""

import json
import logging
import os
import sys
import traceback
from typing import Any, Optional

import requests


# ── Global state ──────────────────────────────────────────────
_agent = None
_logger = None

# ── Sabitler ──────────────────────────────────────────────────
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
MAX_YANIT_UZUNLUK = 4000
MAX_BECERI_UZUNLUK = 1500
MAX_MESAJ_UZUNLUK = 500


# ═══════════════════════════════════════════════════════════════
# _get_logger
# ═══════════════════════════════════════════════════════════════


def _get_logger(name: str = "reymen_agent") -> logging.Logger:
    """Singleton logger oluşturur/döndürür."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger(name)
        if not _logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
            handler.setFormatter(formatter)
            _logger.addHandler(handler)
            _logger.setLevel(logging.INFO)
    return _logger


# ═══════════════════════════════════════════════════════════════
# _agent_instance
# ═══════════════════════════════════════════════════════════════


def _agent_instance(config: Optional[dict] = None) -> Any:
    """Agent singleton — AIAgentOrchestrator instance'ı döndürür."""
    global _agent
    if _agent is not None:
        return _agent
    try:
        from main import AIAgentOrchestrator

        _agent = AIAgentOrchestrator()
        return _agent
    except Exception as e:
        _get_logger().error(f"Agent baslatilamadi: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# _beceri_baglami_al
# ═══════════════════════════════════════════════════════════════


def _beceri_baglami_al(hedef: str) -> str:
    """closed_learning_loop._beceri_ara üzerinden beceri bağlamı alır."""
    try:
        from closed_learning_loop import _beceri_ara

        # Mesajı 500 karaktere kısalt
        sorgu = hedef[:MAX_MESAJ_UZUNLUK] if hedef else ""

        sonuc = _beceri_ara(sorgu)

        # Beceri bulunamadi / toplam kontrolü
        if not sonuc or "beceri bulunamadi" in sonuc.lower():
            return ""
        if "toplam" in sonuc.lower():
            return ""

        # Uzun metni kısalt
        if len(sonuc) > MAX_BECERI_UZUNLUK:
            sonuc = sonuc[:MAX_BECERI_UZUNLUK] + "..."

        return f"\n\n## İLGİLİ BECERİLER:\n{sonuc}\n"
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════
# _deepseek_sohbet
# ═══════════════════════════════════════════════════════════════


def _deepseek_sohbet(messages: Any, config: Optional[dict] = None) -> str:
    """DeepSeek API'ye sohbet isteği gönderir."""
    logger = _get_logger()

    # API anahtarı kontrolü
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        logger.warning("DeepSeek API anahtarı bulunamadı")
        return "API anahtarı bulunamadı"

    # Mesajı string'den listeye çevir
    if isinstance(messages, str):
        user_message = messages
    elif isinstance(messages, list):
        # Eğer messages bir liste ise son user mesajını bul
        user_texts = [
            m["content"]
            for m in messages
            if isinstance(m, dict) and m.get("role") == "user"
        ]
        user_message = user_texts[-1] if user_texts else str(messages)
    else:
        user_message = str(messages)

    # Beceri bağlamını al
    beceri_baglama = _beceri_baglami_al(user_message)

    # System mesajı oluştur
    system_content = (
        "Sen yardımsever bir ReYMeN asistansın. "
        "Kullanıcıya net ve doğrudan yanıtlar ver."
    )
    if beceri_baglama:
        system_content += beceri_baglama

    # API isteği
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_message},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        logger.info("DeepSeek API çağrısı yapılıyor...")
        resp = requests.post(
            DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        yanit = data["choices"][0]["message"]["content"]
        logger.info("DeepSeek API yanıtı başarılı")
        return yanit
    except Exception as e:
        logger.error(f"DeepSeek API hatası: {e}")
        return f"API hatası: {e}"


# ═══════════════════════════════════════════════════════════════
# _agent_loop
# ═══════════════════════════════════════════════════════════════


def _agent_loop(hedef: str, config: Optional[dict] = None) -> str:
    """Agent loop — orchestrator üzerinden konuşma çalıştırır."""
    logger = _get_logger()
    logger.info(f"Agent loop başlatılıyor: {hedef[:50]}...")

    try:
        agent = _agent_instance(config)
        if agent is None:
            logger.warning("Agent yok, fallback kullanılıyor")
            return _deepseek_fallback(hedef)

        # Agent ile konuşmayı çalıştır
        agent.run_conversation(hedef)

        # Yanıtı conversation_history'den al
        yanit = None
        if hasattr(agent, "conversation_history") and agent.conversation_history:
            for msg in reversed(agent.conversation_history):
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    yanit = msg.get("content", "")
                    break

        # Fallback: last_response
        if not yanit and hasattr(agent, "last_response") and agent.last_response:
            yanit = agent.last_response

        # Fallback: _yanit_ayikla
        if not yanit:
            raw = str(getattr(agent, "conversation_history", ""))
            yanit = _yanit_ayikla(raw)

        # 4000 karakter sınırı
        if yanit and len(yanit) > MAX_YANIT_UZUNLUK:
            yanit = yanit[:MAX_YANIT_UZUNLUK]

        return yanit or ""
    except Exception as e:
        logger.error(f"Agent loop hatası: {e}")
        return _deepseek_fallback(str(e))


# ═══════════════════════════════════════════════════════════════
# _yanit_ayikla
# ═══════════════════════════════════════════════════════════════


def _yanit_ayikla(raw: str) -> str:
    """Ham çıktıdan yanıt metnini ayıklar."""
    if not raw:
        return ""

    satirlar = raw.split("\n")

    # Markör öncelik sırası (en yüksek → düşük)
    markorler = [
        ("[TAMAMLANDI]", 3),
        ("[SONUC]", 2),
        ("[YANIT]", 1),
    ]

    for markor, oncelik in markorler:
        for satir in satirlar:
            if markor in satir:
                icerik = satir.split(markor, 1)[1].strip()
                if len(icerik) >= 3:
                    return icerik

    # Markör bulunamadı — son 5 satırdan en uzun içerikli satır
    son_satirlar = satirlar[-5:]

    # Filtrele: kısa/kalıp satırları atla
    filtrelenmis = []
    for satir in son_satirlar:
        satir_stripped = satir.strip()
        if not satir_stripped:
            continue
        if satir_stripped == "---":
            continue
        if satir_stripped == "===":
            continue
        if "[Budget]" in satir_stripped or "[Bütçe]" in satir_stripped:
            continue
        if "--- TUR" in satir_stripped:
            continue
        filtrelenmis.append(satir_stripped)

    if not filtrelenmis:
        # Hepsi filtrelendiyse son satırı al
        return son_satirlar[-1].strip() if son_satirlar else ""

    # En uzun içerikli satırı seç
    return max(filtrelenmis, key=len)


# ═══════════════════════════════════════════════════════════════
# _deepseek_fallback
# ═══════════════════════════════════════════════════════════════


def _deepseek_fallback(
    error: str, messages: Any = None, config: Optional[dict] = None
) -> str:
    """Fallback — agent başarısız olursa direkt DeepSeek API çağrısı."""
    logger = _get_logger()
    logger.warning(f"Fallback kullanılıyor: {error}")

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return "API anahtarı bulunamadı"

    # Kullanılacak mesaj
    if messages is None:
        mesaj = f"Hata oluştu: {error}. Lütfen kullanıcıya yardımcı ol."
    elif isinstance(messages, str):
        mesaj = messages
    else:
        mesaj = str(messages)

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Sen bir fallback asistansın. Ana sistem hatası nedeniyle "
                    "devreye girdin. Kullanıcıya yardımcı ol."
                ),
            },
            {"role": "user", "content": mesaj},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Fallback API hatası: {e}")
        return f"API hatası: {e}"


# ═══════════════════════════════════════════════════════════════
# _format_temizle
# ═══════════════════════════════════════════════════════════════


def _format_temizle(text: str) -> str:
    """Metin formatını temizler — backtick ve kod bloklarını düzeltir."""
    if not text:
        return text

    # Kod bloğu içinde olup olmadığımızı takip et
    def _kod_ici_indexler(satirlar):
        """Kod bloğu içindeki satırların index setini döndürür."""
        kod_ici = set()
        acik = False
        for i, satir in enumerate(satirlar):
            if satir.startswith("```"):
                acik = not acik
            elif acik:
                kod_ici.add(i)
        return kod_ici

    satirlar = text.split("\n")
    kod_ici = _kod_ici_indexler(satirlar)

    yeni_satirlar = []
    for i, satir in enumerate(satirlar):
        if i in kod_ici:
            # Kod bloğu içindeki satırları değiştirme
            yeni_satirlar.append(satir)
            continue

        yeni_satir = satir

        # 4+ backtick → 3 backtick
        if yeni_satir.startswith("````"):
            # Kaç backtick var?
            count = 0
            for ch in yeni_satir:
                if ch == "`":
                    count += 1
                else:
                    break
            if count >= 4:
                gerisi = yeni_satir[count:]
                yeni_satir = "```" + gerisi

        # Çift backtick + dil → üçlü backtick + dil (açılış)
        if yeni_satir.startswith("``") and not yeni_satir.startswith("```"):
            gerisi = yeni_satir[2:]
            if gerisi and not gerisi.startswith("`"):
                yeni_satir = "```" + gerisi

        # Satır başı tek backtick → üçlü backtick
        if yeni_satir.startswith("`") and not yeni_satir.startswith("``"):
            # Kod bloğu açma mı yoksa inline kod mu?
            gerisi = yeni_satir[1:]
            if gerisi.strip():
                yeni_satir = "```" + gerisi

        yeni_satirlar.append(yeni_satir)

    # Kod bloğu kapanışını düzelt: tek backtick → üçlü
    metin = "\n".join(yeni_satirlar)
    if metin.rstrip().endswith("`") and not metin.rstrip().endswith("```"):
        # Son satır tek backtick ile bitiyor
        # ``` ile başlayan bir bloğun kapanışı mı?
        satirlar_yeni = metin.split("\n")
        acik_blok_sayisi = 0
        for s in satirlar_yeni:
            if s.startswith("```") and s.strip() == "```":
                acik_blok_sayisi += 1
            elif s.startswith("```"):
                acik_blok_sayisi += 1

        if acik_blok_sayisi % 2 != 0:
            # Açık blok var, kapat
            for j in range(len(satirlar_yeni) - 1, -1, -1):
                s = satirlar_yeni[j]
                if s.rstrip().endswith("`") and not s.rstrip().endswith("```"):
                    # Tek backtick ile biten satır
                    if s.rstrip().endswith("`"):
                        # Son backtick(ler)i say
                        sondaki_backtick = 0
                        for ch in reversed(s.rstrip()):
                            if ch == "`":
                                sondaki_backtick += 1
                            else:
                                break
                        if sondaki_backtick == 1:
                            satirlar_yeni[j] = s.rstrip()[:-1].rstrip() + "```"
                            break
            metin = "\n".join(satirlar_yeni)

    # 2+ ardışık Python kodu satırını blokla (kod bloğu dışında)
    satirlar_son = metin.split("\n")
    kod_ici2 = _kod_ici_indexler(satirlar_son)
    yeni_satirlar2 = []
    i = 0
    while i < len(satirlar_son):
        if i in kod_ici2:
            yeni_satirlar2.append(satirlar_son[i])
            i += 1
            continue

        # 2+ ardışık Python kodu satırı ara
        python_satirlari = []
        j = i
        while j < len(satirlar_son) and j not in kod_ici2:
            s = satirlar_son[j]
            # Python kodu: indent (4 boşluk) veya def/class/if/for/with ile başlayan
            if (
                s.startswith("    ")
                or s.startswith("\t")
                or s.startswith("def ")
                or s.startswith("class ")
                or s.startswith("if ")
                or s.startswith("for ")
                or s.startswith("while ")
                or s.startswith("with ")
                or s.startswith("try:")
                or s.startswith("except")
                or s.startswith("elif ")
                or s.startswith("else:")
                or s.startswith("return ")
                or s.startswith("import ")
                or s.startswith("from ")
                or s.startswith("async ")
                or s.startswith("@")
            ):
                python_satirlari.append(s)
                j += 1
            else:
                break

        if len(python_satirlari) >= 2:
            yeni_satirlar2.append("```python")
            yeni_satirlar2.extend(python_satirlari)
            yeni_satirlar2.append("```")
            i = j
        else:
            yeni_satirlar2.append(satirlar_son[i])
            i += 1

    return "\n".join(yeni_satirlar2).strip()


# ═══════════════════════════════════════════════════════════════
# isleyen_gorev
# ═══════════════════════════════════════════════════════════════


def isleyen_gorev(
    task: str, use_agent: bool = False, chat_id: Optional[str] = None
) -> str:
    """Ana işlev — görevi işler ve yanıt döndürür."""
    logger = _get_logger()
    logger.info(f"Görev işleniyor: {task[:50]}... (use_agent={use_agent}, chat_id={chat_id})")

    if use_agent:
        return _agent_loop(task)
    else:
        return _deepseek_sohbet(task)


# ═══════════════════════════════════════════════════════════════
# kopru_deepseek_istek
# ═══════════════════════════════════════════════════════════════


def kopru_deepseek_istek(messages: Any, config: Optional[dict] = None) -> str:
    """Köprü entegrasyonu — isleyen_gorev'e yönlendirir."""
    logger = _get_logger()
    logger.info("Köprü isteği alındı, isleyen_gorev'e yönlendiriliyor...")

    if isinstance(messages, str):
        return isleyen_gorev(messages, chat_id="kopru")
    elif isinstance(messages, list):
        # Liste ise son user mesajını çıkar
        user_texts = [
            m["content"]
            for m in messages
            if isinstance(m, dict) and m.get("role") == "user"
        ]
        mesaj = user_texts[-1] if user_texts else str(messages)
        return isleyen_gorev(mesaj, chat_id="kopru")
    else:
        return isleyen_gorev(str(messages), chat_id="kopru")
