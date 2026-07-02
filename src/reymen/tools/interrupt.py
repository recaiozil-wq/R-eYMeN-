"""ReYMeN tools.interrupt shim (override) — Hermes interrupt yönetimini ReYMeN'e yönlendirir."""
from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)

_thread_local = threading.local()
_DEBUG_INTERRUPT = bool(os.getenv("HERMES_DEBUG_INTERRUPT"))


def is_interrupted() -> bool:
    """ReYMeN'de interrupt mekanizması yok — her zaman False."""
    return False


def set_interrupt(thread_id: int) -> None:
    logger.debug("set_interrupt(%d) — ReYMeN stub", thread_id)


def clear_interrupt() -> None:
    logger.debug("clear_interrupt — ReYMeN stub")
