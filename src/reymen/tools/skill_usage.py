"""ReYMeN tools.skill_usage shim — Hermes skill kullanım takibini yönlendirir."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def bump_use(skill_name: str, by: int = 1) -> None:
    """Hermes bump_use — ReYMeN'de skill kullanım sayacı."""
    logger.debug("Skill '%s' usage bumped by %d (ReYMeN stub)", skill_name, by)
