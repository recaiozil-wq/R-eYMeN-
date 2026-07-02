"""ReYMeN tools.macro shim — Hermes macro fonksiyonlarını yönlendirir."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def oynat(makro_adi: str, **kwargs) -> str:
    """Hermes macro.oynat — ReYMeN'de makro çalıştırma."""
    logger.info("Macro '%s' called with %d args (ReYMeN stub)", makro_adi, len(kwargs))
    return f"[MAKRO] {makro_adi} çalıştırıldı (stub)"
