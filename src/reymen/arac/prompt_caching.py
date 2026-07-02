# -*- coding: utf-8 -*-
"""
prompt_caching.py — Prompt Onbellekleme.

Ayni prompt'lari LLM'e tekrar gondermemek icin hash tabanli
onbellek. TTL ve LRU ile bellek yonetimi.

Ayrica Anthropic prompt caching stratejisi (system_and_3) icin
cache_control marker fonksiyonlari icerir.
"""

import copy
import hashlib
import json
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional


class PromptCache:
    """Prompt onbellegi (LRU + TTL)."""

    def __init__(self, max_boyut: int = 100, ttl_saniye: int = 300):
        self._max_boyut = max_boyut
        self._ttl = ttl_saniye
        self._cache: OrderedDict[str, tuple[float, str]] = OrderedDict()
        self._hit = 0
        self._miss = 0

    def _hash(self, prompt: str, mesajlar: list) -> str:
        """Prompt + mesajlardan hash uret."""
        veri = prompt + "|" + json.dumps(mesajlar, sort_keys=True)
        return hashlib.md5(veri.encode("utf-8"), usedforsecurity=False).hexdigest()

    def al(self, prompt: str, mesajlar: list) -> Optional[str]:
        """Onbellekten yanit al.

        Returns:
            Yanit metni veya None (onbellekte yok/sure dolmus)
        """
        anahtar = self._hash(prompt, mesajlar)
        if anahtar not in self._cache:
            self._miss += 1
            return None

        zaman, yanit = self._cache[anahtar]
        if time.time() - zaman > self._ttl:
            del self._cache[anahtar]
            self._miss += 1
            return None

        # LRU: son kullanima tasi
        self._cache.move_to_end(anahtar)
        self._hit += 1
        return yanit

    def ekle(self, prompt: str, mesajlar: list, yanit: str):
        """Onbellege yanit ekle."""
        anahtar = self._hash(prompt, mesajlar)
        self._cache[anahtar] = (time.time(), yanit)

        # LRU eviction
        while len(self._cache) > self._max_boyut:
            self._cache.popitem(last=False)

    def istatistik(self) -> dict:
        toplam = self._hit + self._miss
        return {
            "boyut": len(self._cache),
            "hit": self._hit,
            "miss": self._miss,
            "hit_orani": round(self._hit / toplam * 100, 1) if toplam > 0 else 0,
        }

    def sifirla(self):
        self._cache.clear()
        self._hit = 0
        self._miss = 0


# ══════════════════════════════════════════════════════════════════════
# Anthropic Prompt Caching — cache_control marker fonksiyonlari
# ══════════════════════════════════════════════════════════════════════

def _apply_cache_marker(msg: dict, cache_marker: dict, native_anthropic: bool = False) -> None:
    """Add cache_control to a single message, handling all format variations."""
    role = msg.get("role", "")
    content = msg.get("content")

    if role == "tool":
        if native_anthropic:
            msg["cache_control"] = cache_marker
        return

    if content is None or content == "":
        msg["cache_control"] = cache_marker
        return

    if isinstance(content, str):
        msg["content"] = [
            {"type": "text", "text": content, "cache_control": cache_marker}
        ]
        return

    if isinstance(content, list) and content:
        last = content[-1]
        if isinstance(last, dict):
            last["cache_control"] = cache_marker


def _build_marker(ttl: str) -> Dict[str, str]:
    """Build a cache_control marker dict for the given TTL ('5m' or '1h')."""
    marker: Dict[str, str] = {"type": "ephemeral"}
    if ttl == "1h":
        marker["ttl"] = "1h"
    return marker


def apply_anthropic_cache_control(
    api_messages: List[Dict[str, Any]],
    cache_ttl: str = "5m",
    native_anthropic: bool = False,
) -> List[Dict[str, Any]]:
    """Apply system_and_3 caching strategy to messages for Anthropic models.

    Places up to 4 cache_control breakpoints: system prompt + last 3 non-system
    messages, all at the same TTL.

    Returns:
        Deep copy of messages with cache_control breakpoints injected.
    """
    messages = copy.deepcopy(api_messages)
    if not messages:
        return messages

    marker = _build_marker(cache_ttl)

    breakpoints_used = 0

    if messages[0].get("role") == "system":
        _apply_cache_marker(messages[0], marker, native_anthropic=native_anthropic)
        breakpoints_used += 1

    remaining = 4 - breakpoints_used
    non_sys = [i for i in range(len(messages)) if messages[i].get("role") != "system"]
    for idx in non_sys[-remaining:]:
        _apply_cache_marker(messages[idx], marker, native_anthropic=native_anthropic)

    return messages


def caching_aktif_mi(provider: Optional[str] = None) -> bool:
    """Check if prompt caching is active/supported for the given provider.

    Args:
        provider: Provider name string (e.g. 'anthropic', 'openai', 'deepseek').

    Returns:
        True if the provider supports prompt caching.
    """
    if provider is None:
        return True  # varsayilan: aktif
    provider = provider.lower()
    # Anthropic, OpenAI, DeepSeek, OpenRouter destekliyor
    caching_providers = {"anthropic", "claude", "sonnet", "openai", "gpt4",
                         "gpt4o", "deepseek", "openrouter", "gemini", "codex"}
    return provider in caching_providers or any(p in provider for p in caching_providers)


def _prompt_caching_ekle(loop_instance: Any, mesajlar: List[dict]) -> List[dict]:
    """Apply prompt caching strategy based on provider.

    This is called by conversation_loop's _prompt_caching_ekle method.
    Delegates to apply_anthropic_cache_control for Anthropic-compatible providers.

    Args:
        loop_instance: The ConversationLoop instance (for provider context).
        mesajlar: List of message dicts to add caching markers to.

    Returns:
        Messages with caching markers applied.
    """
    # Try to detect provider from the loop instance
    provider = getattr(loop_instance, "_provider", None)
    if provider:
        provider = str(provider).lower()

    # Default: apply Anthropic-style caching
    return apply_anthropic_cache_control(mesajlar, cache_ttl="5m", native_anthropic=False)


# Global cache instance
_ONBELLEK = PromptCache()


def cache_ile_uret(prompt: str, mesajlar: list, uret_fonksiyonu) -> str:
    """Onbellek kontrolu ile LLM cagrisi yap.

    Args:
        prompt: Sistem prompt'u
        mesajlar: Konusma mesajlari
        uret_fonksiyonu: Onbellekte yoksa cagrilacak fonksiyon

    Returns:
        Yanit metni
    """
    yanit = _ONBELLEK.al(prompt, mesajlar)
    if yanit is not None:
        return yanit

    yanit = uret_fonksiyonu(prompt, mesajlar)
    _ONBELLEK.ekle(prompt, mesajlar, yanit)
    return yanit


if __name__ == "__main__":
    c = PromptCache(max_boyut=5, ttl_saniye=10)
    c.ekle("test", [{"role": "user", "content": "merhaba"}], "merhaba")
    print("Hit:", c.al("test", [{"role": "user", "content": "merhaba"}]))
    print("Miss:", c.al("test", [{"role": "user", "content": "nasilsin"}]))
    print("Istatistik:", c.istatistik())
