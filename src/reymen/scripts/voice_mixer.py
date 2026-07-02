# -*- coding: utf-8 -*-
"""voice_mixer.py — Pure-PCM voice mixer for Discord audio.

Exports:
  FRAME_SIZE       = 3840
  SAMPLES_PER_FRAME = 960
  SILENCE_FRAME     = bytes(FRAME_SIZE)
  VoiceMixer        — audio mixing class
  synth_ambient_pcm — ambient audio generator
"""
import struct
import math

FRAME_SIZE = 3840
SAMPLES_PER_FRAME = 960
SILENCE_FRAME = bytes(FRAME_SIZE)


def synth_ambient_pcm(seconds: float = 0.5, sample_rate: int = 48000) -> bytes:
    """Synthesize ambient pink-noise-like PCM audio."""
    total_samples = int(sample_rate * seconds)
    frames = []
    for i in range(total_samples):
        t = i / sample_rate
        # Simple brownish noise + soft tone
        val = int(
            math.sin(t * 220 * 2 * math.pi) * 800
            + math.sin(t * 330 * 2 * math.pi) * 400
            + (hash(i) % 200 - 100) * 0.3
        )
        val = max(-32768, min(32767, val))
        frames.extend([val, val])  # stereo
    return struct.pack('<' + 'h' * len(frames), *frames)


class VoiceMixer:
    """Pure-PCM stereo audio mixer for Discord voice."""

    def __init__(self, ambient_gain: float = 0.0,
                 duck_gain: float = 0.0, duck_release_ms: int = 500):
        self._ambient: bytes = b''
        self._ambient_gain = ambient_gain
        self._duck_gain = duck_gain
        self._duck_release_ms = duck_release_ms
        self._buffer: list[bytes] = []
        self._pos = 0

    def set_ambient(self, pcm_data: bytes):
        self._ambient = pcm_data

    def add_frame(self, frame: bytes):
        self._buffer.append(frame)

    def read(self) -> bytes:
        if self._buffer:
            return self._buffer.pop(0)
        if self._ambient and self._ambient_gain > 0:
            return self._ambient
        return SILENCE_FRAME

    def is_opus(self) -> bool:
        return False
