"""ReYMeN tools.computer_use_tool shim — Hermes computer use fonksiyonlarını yönlendirir."""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_approval_callback: Optional[Callable] = None


def set_approval_callback(callback: Optional[Callable]) -> None:
    global _approval_callback
    _approval_callback = callback
