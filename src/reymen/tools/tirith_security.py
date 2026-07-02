"""ReYMeN tools.tirith_security shim — Hermes Tirith güvenlik kontrollerini yönlendirir."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def ensure_installed() -> bool:
    """Hermes ensure_installed — ReYMeN'de Tirith kullanılmaz."""
    return True


def is_platform_supported() -> bool:
    """Hermes is_platform_supported — ReYMeN'de her platform desteklenir."""
    return True
