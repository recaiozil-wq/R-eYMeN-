"""ReYMeN tools.voice_mode shim — Hermes voice mode fonksiyonlarını yönlendirir."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def check_voice_requirements() -> Dict[str, Any]:
    """Hermes check_voice_requirements — ses gereksinimlerini kontrol eder."""
    result = {
        "microphone": False,
        "speaker": False,
        "tts_available": False,
        "stt_available": False,
    }
    try:
        import speech_recognition  # noqa: F401
        result["microphone"] = True
    except ImportError as _e:
        logger.warning("[VoiceMode] Modul yuklenemedi (L22): %s", ImportError)
        pass
    try:
        from reymen.arac.voice_engine import VoiceRegistry
        registry = VoiceRegistry()
        result["tts_available"] = True
        result["stt_available"] = True
    except ImportError:
        try:
            import edge_tts  # noqa: F401
            result["tts_available"] = True
        except ImportError as _e:
            logger.warning("[VoiceMode] Modul yuklenemedi (L33): %s", ImportError)
            pass
    return result


def detect_audio_environment() -> Dict[str, Any]:
    """Hermes detect_audio_environment — ses ortamını algılar."""
    return check_voice_requirements()


def stop_playback(*args, **kwargs) -> None:
    """Hermes stop_playback — oynatmayı durdurur."""
    logger.debug("stop_playback — ReYMeN stub")
