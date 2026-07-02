"""ReYMeN Web Search Provider Registry
======================================

Central map of registered web providers. Basitleştirilmiş ReYMeN sürümü —
Hermes config.yaml bağımlılığı yoktur, sadece env var + kayıtlı provider'lar.

Active selection:
1. REYMEN_SEARCH_BACKEND / REYMEN_EXTRACT_BACKEND env var
2. REYMEN_WEB_BACKEND env var (shared fallback)
3. Legacy preference: firecrawl → parallel → tavily → exa → searxng → brave-free → ddgs
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Dict, List, Optional

from reymen.web_search_provider import WebSearchProvider

logger = logging.getLogger(__name__)

_providers: Dict[str, WebSearchProvider] = {}
_lock = threading.Lock()


def register_provider(provider: WebSearchProvider) -> None:
    if not isinstance(provider, WebSearchProvider):
        raise TypeError(
            f"register_provider() expects a WebSearchProvider instance, "
            f"got {type(provider).__name__}"
        )
    name = provider.name
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Web provider .name must be a non-empty string")
    with _lock:
        existing = _providers.get(name)
        _providers[name] = provider
    if existing is not None:
        logger.debug("Web provider '%s' re-registered", name)
    else:
        logger.debug("Registered web provider '%s' (%s)", name, type(provider).__name__)


def list_providers() -> List[WebSearchProvider]:
    with _lock:
        items = list(_providers.values())
    return sorted(items, key=lambda p: p.name)


def get_provider(name: str) -> Optional[WebSearchProvider]:
    if not isinstance(name, str):
        return None
    with _lock:
        return _providers.get(name.strip())


_LEGACY_PREFERENCE = (
    "firecrawl", "parallel", "tavily", "exa", "searxng", "brave-free", "ddgs",
)


def _get_env_backend(capability: str) -> Optional[str]:
    """Read backend from REYMEN_{capability}_BACKEND or REYMEN_WEB_BACKEND."""
    key = f"REYMEN_{capability.upper()}_BACKEND"
    val = os.getenv(key, "").strip().lower()
    if val:
        return val
    val = os.getenv("REYMEN_WEB_BACKEND", "").strip().lower()
    if val:
        return val
    return None


def _resolve(configured: Optional[str], *, capability: str) -> Optional[WebSearchProvider]:
    with _lock:
        snapshot = dict(_providers)

    def _capable(p: WebSearchProvider) -> bool:
        if capability == "search":
            return bool(p.supports_search())
        if capability == "extract":
            return bool(p.supports_extract())
        return False

    def _available(p: WebSearchProvider) -> bool:
        try:
            return bool(p.is_available())
        except Exception:
            return False

    if configured:
        provider = snapshot.get(configured)
        if provider is not None and _capable(provider):
            return provider

    eligible = [p for p in snapshot.values() if _capable(p) and _available(p)]
    if len(eligible) == 1:
        return eligible[0]

    for legacy in _LEGACY_PREFERENCE:
        provider = snapshot.get(legacy)
        if provider is not None and _capable(provider) and _available(provider):
            return provider

    return None


def get_active_search_provider() -> Optional[WebSearchProvider]:
    configured = _get_env_backend("search")
    return _resolve(configured, capability="search")


def get_active_extract_provider() -> Optional[WebSearchProvider]:
    configured = _get_env_backend("extract")
    return _resolve(configured, capability="extract")


def _reset_for_tests() -> None:
    with _lock:
        _providers.clear()
