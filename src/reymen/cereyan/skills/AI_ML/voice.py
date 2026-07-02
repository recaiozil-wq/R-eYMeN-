# -*- coding: utf-8 -*-
"""
voice.py — AI_ML skill: Ses (TTS/STT) motoru.

Bağımlılıklar:
  - reymen.arac.voice_engine — OpenAI TTS, Edge TTS, Whisper STT engine'leri

Kullanım:
  from reymen.cereyan.skills.AI_ML.voice import seslendir, yaziya_cevir
  sonuc = seslendir("Merhaba dunya", voice="alloy", backend="openai")
  metin = yaziya_cevir("ses.mp3", backend="whisper")
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# Engine'i içe aktar
try:
    from reymen.arac.voice_engine import (
        EdgeTTS,
        OpenAITTS,
        StubVoice,
        VoiceEngine,
        VoiceRegistry,
        WhisperSTT,
        seslendir,
        voice_engine_listele,
        yaziya_cevir,
    )
except ImportError as e:
    log.warning("[AI_ML/voice] voice_engine yuklenemedi: %s", e)
    EdgeTTS = None  # type: ignore
    OpenAITTS = None  # type: ignore
    StubVoice = None  # type: ignore
    VoiceEngine = None  # type: ignore
    VoiceRegistry = None  # type: ignore
    WhisperSTT = None  # type: ignore
    seslendir = lambda text, voice="alloy", backend="": f"[Voice] Motor yuklenemedi: {text}"
    yaziya_cevir = lambda ses_dosyasi, backend="whisper": f"[Voice] Motor yuklenemedi: {ses_dosyasi}"
    voice_engine_listele = lambda: "[Voice] Motor yuklenemedi."


__all__ = [
    "EdgeTTS",
    "OpenAITTS",
    "StubVoice",
    "VoiceEngine",
    "VoiceRegistry",
    "WhisperSTT",
    "seslendir",
    "voice_engine_listele",
    "yaziya_cevir",
]
