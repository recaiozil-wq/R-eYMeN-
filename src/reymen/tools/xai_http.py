"""ReYMeN tools.xai_http stub — sadece env var ile çalışır."""

import json
import os
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def has_xai_credentials() -> bool:
    """XAI_API_KEY env var'ı kontrol eder."""
    key = os.getenv("XAI_API_KEY", "").strip()
    if key:
        return True
    # REYMEN_HOME/auth.json da kontrol et
    reymen_home = Path(os.environ.get("REYMEN_HOME", str(Path.home() / ".reymen")))
    auth_path = reymen_home / "auth.json"
    if auth_path.exists():
        try:
            store = json.loads(auth_path.read_text())
            providers = store.get("providers", {}) if isinstance(store, dict) else {}
            xai_state = providers.get("xai-oauth", {}) if isinstance(providers, dict) else {}
            tokens = xai_state.get("tokens", {}) if isinstance(xai_state, dict) else {}
            access = tokens.get("access_token", "") if isinstance(tokens, dict) else ""
            return bool(str(access or "").strip())
        except Exception as _e:
            logger.warning("[XaiHttp] except Exception (L25): %s", Exception)
            pass
    return False


def get_env_value(name: str, default=None):
    """Önce REYMEN_HOME/.env, sonra os.environ."""
    reymen_home = Path(os.environ.get("REYMEN_HOME", str(Path.home() / ".reymen")))
    dotenv_path = reymen_home / ".env"
    if dotenv_path.exists():
        try:
            for line in dotenv_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip().strip("'\"")
                if k == name:
                    return v.strip().strip("'\"")
        except Exception as _e:
            logger.warning("[XaiHttp] except Exception (L44): %s", Exception)
            pass
    return os.environ.get(name, default)


def hermes_xai_user_agent() -> str:
    """ReYMeN User-Agent for xAI HTTP calls."""
    return "ReYMeN-Agent/1.0"


def resolve_xai_http_credentials(*, force_refresh: bool = False) -> Dict[str, str]:
    """XAI_API_KEY'den bearer token oluşturur."""
    key = get_env_value("XAI_API_KEY", "")
    if key:
        return {"Authorization": f"Bearer {key}"}
    return {}
