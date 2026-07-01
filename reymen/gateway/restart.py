"""Shared gateway restart constants and parsing helpers."""
from __future__ import annotations

# Varsayilan config degerleri (DEFAULT_CONFIG yerine)
_DEFAULT_RESTART_DRAIN_TIMEOUT = 30.0

# EX_TEMPFAIL from sysexits.h — used to ask the service manager to restart
# the gateway after a graceful drain/reload path completes.
GATEWAY_SERVICE_RESTART_EXIT_CODE = 75

DEFAULT_GATEWAY_RESTART_DRAIN_TIMEOUT = _DEFAULT_RESTART_DRAIN_TIMEOUT


def parse_restart_drain_timeout(raw: object) -> float:
    """Parse a configured drain timeout, falling back to the shared default."""
    try:
        value = float(raw) if str(raw or "").strip() else DEFAULT_GATEWAY_RESTART_DRAIN_TIMEOUT
    except (TypeError, ValueError):
        return DEFAULT_GATEWAY_RESTART_DRAIN_TIMEOUT
    return max(0.0, value)
