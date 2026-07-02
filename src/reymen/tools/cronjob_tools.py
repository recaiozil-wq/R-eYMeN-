"""ReYMeN tools.cronjob_tools shim — Hermes cronjob araçlarını yönlendirir."""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _scan_cron_prompt(prompt: str) -> dict:
    """Hermes _scan_cron_prompt — cron prompt'unu tarar."""
    return {"prompt": prompt, "schedule": None}


def _scan_cron_skill_assembled(skills: list) -> list:
    """Hermes _scan_cron_skill_assembled — skill listesini tarar."""
    return skills


def cronjob(*args, **kwargs) -> str:
    """Hermes cronjob — cronjob tool'una yönlendirir."""
    import json
    try:
        from reymen.cron.cronjob_tool import cronjob as _cronjob
        return _cronjob(*args, **kwargs)
    except Exception as e:
        return json.dumps({"success": False, "error": f"Cronjob unavailable: {e}"})
