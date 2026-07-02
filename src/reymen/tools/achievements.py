"""ReYMeN tools.achievements shim — Hermes başarımlarını yönlendirir."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _listeye_ekle(*args, **kwargs) -> None:
    """Hermes _listeye_ekle — ReYMeN'de no-op."""
    pass


def check_achievements(*args, **kwargs) -> Any:
    """Hermes check_achievements — ReYMeN'de no-op."""
    return []


def rozet_listele(*args, **kwargs) -> str:
    """Hermes rozet_listele — ReYMeN'de no-op."""
    return "Rozetler (ReYMeN stub)"
