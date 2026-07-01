# -*- coding: utf-8 -*-
"""
config.py — ReYMeN config yardimci fonksiyonlari (hermes_stubs.config).
Apache 2.0 — inspired by NousResearch/hermes-agent
"""
from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
logger = logging.getLogger(__name__)


# ReYMeN'in kendi config modulu
try:
    from reymen.sistem.hermes_uyum import load_config as _reymen_load
except ImportError:
    _reymen_load = lambda: {}


def cfg_get(cfg: Optional[Dict[str, Any]], *keys: str, default: Any = None) -> Any:
    """Ic ice dict'ten guvenli deger okuma.
    
    Ornek: cfg_get(config, "agent", "model", default="gpt-4")
    """
    if not cfg or not keys:
        return default
    current: Any = cfg
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    return current if current is not None else default


def load_config() -> Dict[str, Any]:
    """Config yukle — reymen.sistem.hermes_uyum uzerinden."""
    try:
        from reymen.sistem.hermes_uyum import load_config as _load
        return _load() or {}
    except Exception as e:
        logger.debug("[config/stub] load_config: %s", e)
        return {}


def save_config(cfg: Dict[str, Any], path: Optional[Path] = None) -> bool:
    """Config kaydet — stub (henuz yazma destegi yok)."""
    logger.warning("[config/stub] save_config: henuz desteklenmiyor")
    return False


def save_env_value(key: str, value: str) -> bool:
    """Ortam degiskenini .env dosyasina kaydet — stub."""
    logger.warning("[config/stub] save_env_value: henuz desteklenmiyor")
    return False


def is_managed(cfg: Optional[Dict[str, Any]] = None) -> bool:
    """Nous managed mi? — stub, her zaman False."""
    return False


def format_managed_message() -> str:
    """Managed mesaji — stub."""
    return ""


def get_compatible_custom_providers() -> list[Dict[str, Any]]:
    """Custom provider listesi — stub."""
    return []
