# -*- coding: utf-8 -*-
"""
voice.py — ReYMeN tool arayüzü: Ses (TTS/STT) araçları.

Bu modül, reymen.arac.voice_engine motorunu ReYMeN'in tool
sistemine bağlar. Motor tarafından otomatik kaydedilir.

Kullanım:
  SESLENDIR(text="Merhaba Dunya", voice="alloy", backend="openai")
  YAZIYA_CEVIR(ses_dosyasi="ses.mp3", backend="whisper")
  SESLENDIR_BACKEND_LISTELE()
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

try:
    from reymen.arac.voice_engine import (
        motor_kaydet,
        seslendir,
        voice_engine_listele,
        yaziya_cevir,
    )
except ImportError as e:
    log.warning("[arac/voice] voice_engine yuklenemedi: %s", e)
    motor_kaydet = lambda motor: None
    seslendir = lambda text, voice="alloy", backend="": (
        f"[SESLENDIR] Motor yuklenemedi: {text}"
    )
    yaziya_cevir = lambda ses_dosyasi, backend="whisper": (
        f"[YAZIYA_CEVIR] Motor yuklenemedi: {ses_dosyasi}"
    )
    voice_engine_listele = lambda: "[SESLENDIR] Motor yuklenemedi."


__all__ = [
    "motor_kaydet",
    "seslendir",
    "yaziya_cevir",
    "voice_engine_listele",
]
