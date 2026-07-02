"""ReYMeN shared debug session — Bağımsız ReYMeN sürümü."""

import datetime
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DebugSession:
    """Per-tool debug session that records tool calls to a JSON log file."""

    def __init__(self, tool_name: str, *, env_var: str) -> None:
        self.tool_name = tool_name
        self.enabled = os.getenv(env_var, "false").lower() == "true"
        self.session_id = str(uuid.uuid4()) if self.enabled else ""
        # ReYMeN log dir = ~/.reymen/logs/ veya REYMEN_HOME/logs/
        reymen_home = Path(os.environ.get("REYMEN_HOME", str(Path.home() / ".reymen")))
        self.log_dir = reymen_home / "logs"
        self._calls: list[Dict[str, Any]] = []
        self._start_time = datetime.datetime.now().isoformat() if self.enabled else ""
        if self.enabled:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            logger.debug("%s debug mode enabled - Session ID: %s", tool_name, self.session_id)

    @property
    def active(self) -> bool:
        return self.enabled

    def log_call(self, call_name: str, call_data: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        self._calls.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "tool_name": call_name,
            **call_data,
        })

    def save(self) -> None:
        if not self.enabled:
            return
        try:
            filename = f"{self.tool_name}_debug_{self.session_id}.json"
            filepath = self.log_dir / filename
            payload = {
                "session_id": self.session_id,
                "start_time": self._start_time,
                "end_time": datetime.datetime.now().isoformat(),
                "calls": list(self._calls),
            }
            filepath.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.debug("Debug log saved: %s", filepath)
        except Exception as exc:
            logger.warning("Failed to save debug log: %s", exc)

    def get_session_info(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"enabled": False}
        return {
            "enabled": True,
            "tool_name": self.tool_name,
            "session_id": self.session_id,
            "start_time": self._start_time,
            "call_count": len(self._calls),
            "log_dir": str(self.log_dir),
        }
