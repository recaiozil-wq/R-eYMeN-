"""ReYMeN tools.terminal_tool shim — Hermes terminal fonksiyonlarını ReYMeN'e yönlendirir."""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_sudo_password_callback: Optional[Callable] = None
_approval_callback: Optional[Callable] = None


def set_sudo_password_callback(callback: Optional[Callable]) -> None:
    global _sudo_password_callback
    _sudo_password_callback = callback


def set_approval_callback(callback: Optional[Callable]) -> None:
    global _approval_callback
    _approval_callback = callback


def cleanup_all_environments() -> None:
    """Hermes cleanup_all_environments — ReYMeN'de no-op."""
    logger.debug("cleanup_all_environments: ReYMeN stub")


def cleanup_vm() -> None:
    """Hermes cleanup_vm — ReYMeN'de no-op."""
    logger.debug("cleanup_vm: ReYMeN stub")
