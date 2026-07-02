"""ReYMeN tools.tts_tool shim — Hermes TTS fonksiyonlarını ReYMeN voice_engine'e yönlendirir.

Bu modül, Hermes Agent'in tools/tts_tool.py'sini taklit eder.
Tüm işlevler ReYMeN'in voice_engine.py'sine yönlendirilir.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TTS Config
# ---------------------------------------------------------------------------

def _load_tts_config() -> Dict[str, Any]:
    """Hermes TTS config formatını taklit eder. Env var'dan okur."""
    return {
        "provider": os.getenv("REYMEN_TTS_PROVIDER", "edge"),
        "voice": os.getenv("REYMEN_TTS_VOICE", "tr-TR-AhmetNeural"),
        "model": os.getenv("REYMEN_TTS_MODEL", "tts-1"),
    }


def _get_provider(config: Dict[str, Any]) -> str:
    """Hermes _get_provider fonksiyonunu taklit eder."""
    return config.get("provider", "edge")


def _import_elevenlabs() -> None:
    """ElevenLabs SDK kontrolü — yoksa ImportError."""
    try:
        import elevenlabs  # noqa: F401
    except ImportError:
        raise ImportError("elevenlabs not installed. pip install elevenlabs")


def _import_sounddevice() -> None:
    """sounddevice kontrolü — yoksa ImportError."""
    try:
        import sounddevice  # noqa: F401
    except ImportError:
        raise ImportError("sounddevice not installed. pip install sounddevice")


def stream_tts_to_speaker(
    text_queue,
    voice: str = "alloy",
    model: str = "tts-1",
    stream_callback=None,
    stop_event=None,
) -> None:
    """Hermes stream_tts_to_speaker — ReYMeN voice_engine'e yönlendirir.

    Basit implementasyon: ses dosyasına kaydedip oynatır.
    Gerçek streaming için elevenlabs veya başka bir streaming TTS gerekir.
    """
    try:
        from reymen.arac.voice_engine import VoiceRegistry

        registry = VoiceRegistry()
        text = ""
        while not stop_event or not stop_event.is_set():
            try:
                chunk = text_queue.get(timeout=1)
                if chunk is None:
                    break
                text += chunk
            except Exception:
                if text and stop_event and stop_event.is_set():
                    break
                continue

        if text.strip():
            result = registry.seslendir("edge", text, voice)
            logger.info("TTS completed: %s", result[:80] if result else "empty")
    except Exception as e:
        logger.warning("stream_tts_to_speaker failed: %s", e)


# ---------------------------------------------------------------------------
# text_to_speech_tool — ana TTS fonksiyonu
# ---------------------------------------------------------------------------

def text_to_speech_tool(
    text: str,
    voice: Optional[str] = None,
    output_path: Optional[str] = None,
    provider: Optional[str] = None,
) -> str:
    """Hermes text_to_speech_tool — ReYMeN voice_engine'e yönlendirir.

    Args:
        text: Sese çevrilecek metin
        voice: Ses adı (opsiyonel)
        output_path: Çıktı dosyası yolu (opsiyonel)
        provider: TTS sağlayıcısı ('edge', 'openai', vb.)

    Returns:
        str: JSON formatında sonuç
    """
    import json

    try:
        from reymen.arac.voice_engine import VoiceRegistry

        registry = VoiceRegistry()
        effective_provider = provider or os.getenv("REYMEN_TTS_PROVIDER", "edge")
        effective_voice = voice or os.getenv("REYMEN_TTS_VOICE", "tr-TR-AhmetNeural")

        result = registry.seslendir(effective_provider, text, effective_voice)

        if output_path and result and not result.startswith("[") and os.path.exists(result):
            import shutil
            shutil.copy(result, output_path)

        return json.dumps({"success": True, "output": result})
    except Exception as e:
        logger.error("text_to_speech_tool error: %s", e)
        return json.dumps({"success": False, "error": str(e)})


# ---------------------------------------------------------------------------
# speech_to_text_tool
# ---------------------------------------------------------------------------

def speech_to_text_tool(
    audio_path: str,
    language: str = "tr",
    provider: Optional[str] = None,
) -> str:
    """Hermes speech_to_text_tool — ReYMeN voice_engine'e yönlendirir.

    Args:
        audio_path: Ses dosyası yolu
        language: Dil kodu
        provider: STT sağlayıcısı ('whisper', 'openai', vb.)

    Returns:
        str: JSON formatında sonuç
    """
    import json

    try:
        from reymen.arac.voice_engine import VoiceRegistry

        registry = VoiceRegistry()
        effective_provider = provider or os.getenv("REYMEN_STT_PROVIDER", "whisper")

        result = registry.yaziya_cevir(effective_provider, audio_path, language)

        return json.dumps({"success": True, "text": result})
    except Exception as e:
        logger.error("speech_to_text_tool error: %s", e)
        return json.dumps({"success": False, "error": str(e)})
