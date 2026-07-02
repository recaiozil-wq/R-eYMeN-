# -*- coding: utf-8 -*-
"""
tts_stt_tool.py — ReYMeN TTS (Text-to-Speech) ve STT (Speech-to-Text) araclari.

TTS: edge-tts (Microsoft Edge TTS motoru, 100+ ses, 50+ dil)
STT: speech_recognition (Google Speech API, ucretsiz, API key gerekmez)

Kullanim (motor):
    TTS_KONUS(metin, ses="tr-TR-EmelNeural")
    STT_DINLE(dosya_yolu)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Varsayilan ayarlar ─────────────────────────────────────────────────
VARSAYILAN_SES = "tr-TR-EmelNeural"  # Turkce kadin sesi
CIKTI_DIZINI = Path(tempfile.gettempdir()) / "reymen_tts"
CIKTI_DIZINI.mkdir(parents=True, exist_ok=True)


# ── TTS (Text-to-Speech) ──────────────────────────────────────────────

async def _tts_async(metin: str, ses: str, dosya_yolu: str) -> str:
    """edge-tts ile metni sese cevir (asyncio)."""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(metin, ses)
        await communicate.save(dosya_yolu)
        return dosya_yolu
    except ImportError:
        raise ImportError("edge-tts kurulu degil. 'pip install edge-tts' ile kur.")
    except Exception as e:
        raise RuntimeError(f"TTS hatasi: {e}")


def konus(metin: str, ses: str = VARSAYILAN_SES, dosya_adi: str = "") -> str:
    """Metni sese cevirir ve dosya yolunu dondurur.

    Args:
        metin: Seslendirilecek metin (maks 1000 karakter)
        ses: Ses adi (varsayilan: tr-TR-EmelNeural)
        dosya_adi: Ozel dosya adi (bos birakilirsa otomatik)

    Returns:
        Ses dosyasinin tam yolu
    """
    if not metin or not metin.strip():
        return "❌ Metin bos."

    metin = metin.strip()[:1000]  # edge-tts limiti ~3000

    if not dosya_adi:
        import hashlib
        kod = hashlib.md5(metin.encode()).hexdigest()[:8]
        dosya_adi = f"tts_{kod}.mp3"

    dosya_yolu = str(CIKTI_DIZINI / dosya_adi)

    try:
        asyncio.run(_tts_async(metin, ses, dosya_yolu))
        boyut = os.path.getsize(dosya_yolu)
        logger.info("TTS: %s -> %s (%d byte)", dosya_adi, ses, boyut)
        return dosya_yolu
    except Exception as e:
        logger.error("TTS hatasi: %s", e)
        return f"❌ TTS hatasi: {e}"


def ses_liste() -> str:
    """Kullanilabilir sesleri listele."""
    try:
        import edge_tts
        sesler = asyncio.run(edge_tts.list_voices())
        turkce = [s for s in sesler if "TR" in s.get("Locale", "")]
        satirlar = ["🔊 Kullanilabilir Sesler:", ""]
        if turkce:
            satirlar.append("Turkce Sesler:")
            for s in turkce:
                ad = s.get("ShortName", "?")
                cinsiyet = s.get("Gender", "?")
                satirlar.append(f"  • {ad} ({cinsiyet})")
        satirlar.append("")
        satirlar.append(f"Toplam: {len(sesler)} ses ({len(turkce)} Turkce)")
        return "\n".join(satirlar)
    except ImportError:
        return "❌ edge-tts kurulu degil."
    except Exception as e:
        return f"❌ Ses listesi hatasi: {e}"


# ── STT (Speech-to-Text) ──────────────────────────────────────────────

def dinle(dosya_yolu: str, dil: str = "tr-TR") -> str:
    """Ses dosyasini metne cevirir.

    Args:
        dosya_yolu: Ses dosyasinin yolu (.wav, .mp3, .ogg)
        dil: Dil kodu (varsayilan: tr-TR)

    Returns:
        Taninan metin
    """
    try:
        import speech_recognition as sr
    except ImportError:
        return "❌ speech_recognition kurulu degil. 'pip install SpeechRecognition' ile kur."

    if not os.path.exists(dosya_yolu):
        return f"❌ Dosya bulunamadi: {dosya_yolu}"

    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(dosya_yolu) as kaynak:
            recognizer.adjust_for_ambient_noise(kaynak)
            ses = recognizer.record(kaynak)

        # Google Speech API (ucretsiz)
        metin = recognizer.recognize_google(ses, language=dil)
        logger.info("STT: %s -> %s", dosya_yolu, metin[:50])
        return metin

    except sr.UnknownValueError:
        return "❌ Ses taninamadi."
    except sr.RequestError as e:
        return f"❌ Google Speech API hatasi: {e}"
    except Exception as e:
        logger.error("STT hatasi: %s", e)
        return f"❌ STT hatasi: {e}"


# ── Motor tool'lari ────────────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    """Motor tarafindan otomatik cagrilir."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    try:
        motor._plugin_arac_kaydet(
            "TTS_KONUS",
            lambda metin="", ses=VARSAYILAN_SES: konus(metin, ses),
            "Metni sese cevir. Kullanim: TTS_KONUS(metin, ses='tr-TR-EmelNeural') -> dosya_yolu"
        )
        motor._plugin_arac_kaydet(
            "TTS_SES_LISTE",
            ses_liste,
            "Kullanilabilir TTS seslerini listele."
        )
        motor._plugin_arac_kaydet(
            "STT_DINLE",
            lambda dosya="", dil="tr-TR": dinle(dosya, dil),
            "Ses dosyasini metne cevir. Kullanim: STT_DINLE(dosya_yolu, dil='tr-TR')"
        )
        logger.info("[TTS/STT] 3 tool kaydedildi.")
    except Exception as e:
        logger.warning("[TTS/STT] Motor kayit hatasi: %s", e)


# ── CLI (dogrudan calistirma) ──────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Kullanim: tts_stt_tool.py [konus|dinle|sesler] [args]")
        sys.exit(1)

    komut = sys.argv[1]
    if komut == "konus" and len(sys.argv) > 2:
        print(konus(sys.argv[2]))
    elif komut == "sesler":
        print(ses_liste())
    elif komut == "dinle" and len(sys.argv) > 2:
        print(dinle(sys.argv[2]))
    else:
        print("Gecersiz komut.")
