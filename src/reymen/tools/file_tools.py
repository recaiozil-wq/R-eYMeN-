"""ReYMeN tools.file_tools shim — Hermes file tools fonksiyonlarını yönlendirir."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def notify_other_tool_call(function_name: str) -> None:
    """Hermes notify_other_tool_call — ReYMeN'de no-op."""
    pass
