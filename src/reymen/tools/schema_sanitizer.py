"""ReYMeN tools.schema_sanitizer shim — Hermes schema sanitizer'ını yönlendirir."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def sanitize_tool_schemas(schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Hermes sanitize_tool_schemas — ReYMeN'de olduğu gibi geçir."""
    return schemas
