"""ReYMeN tools.mcp_tool shim — Hermes MCP tool fonksiyonlarını yönlendirir."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_servers: Dict[str, Any] = {}
_lock = None


def discover_mcp_tools(*args, **kwargs) -> List[Dict[str, Any]]:
    """Hermes discover_mcp_tools — ReYMeN stub."""
    return []


def shutdown_mcp_servers() -> None:
    """Hermes shutdown_mcp_servers — ReYMeN stub."""
    pass


def _kill_orphaned_mcp_children() -> None:
    """Hermes _kill_orphaned_mcp_children — ReYMeN stub."""
    pass
