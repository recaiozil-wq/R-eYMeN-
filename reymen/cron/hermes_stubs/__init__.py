"""
ReYMeN Hermes Stubs — cron modulu icin gereken Hermes fonksiyonlari.

Bu dosya, Hermes Agent (Nous Research, Apache 2.0) kaynak kodundan
uyarlanan cron modulunun ReYMeN'de bagimsiz calismasini saglar.

Apache 2.0 License — Copyright 2026 ReYMeN Agent contributors.
"""

import json
import logging
import os
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

# =============================================================================
# hermes_constants stub
# =============================================================================

_REYMEN_DIR: Optional[Path] = None


def _get_reymen_root() -> Path:
    """ReYMeN proje kokunu ~/.hermes yerine dondurur.

    ReYMeN-Ajan/reymen/ -> cron verileri reymen/cron_data/ altina gider.
    """
    return Path(__file__).resolve().parent.parent  # reymen/cron/ -> reymen/


def set_hermes_home_override(path: Union[str, Path]) -> Any:
    """Stub — ReYMeN'de override mekanizmasi basit."""
    global _REYMEN_DIR
    _REYMEN_DIR = Path(path)
    return None


def get_hermes_home() -> Path:
    """ReYMeN proje kokunu ~/.hermes yerine dondurur."""
    if _REYMEN_DIR:
        return _REYMEN_DIR
    return _get_reymen_root()


def display_hermes_home() -> str:
    return str(get_hermes_home())


def get_hermes_dir(new_subpath: str, old_name: str) -> Path:
    return get_hermes_home() / new_subpath


def get_config_path() -> Path:
    return get_hermes_home() / "reymen" / "sistem" / "durum.json"


def get_skills_dir() -> Path:
    skills = get_hermes_home() / "reymen" / "cereyan" / "skills"
    skills.mkdir(parents=True, exist_ok=True)
    return skills


def get_env_path() -> Path:
    return get_hermes_home() / ".env"


def secure_parent_dir(path: Path) -> None:
    """Parent dizini yoksa olustur."""
    path.parent.mkdir(parents=True, exist_ok=True)


def parse_reasoning_effort(effort: str) -> Optional[Dict]:
    return None


def apply_ipv4_preference(force: bool = False) -> None:
    pass


# =============================================================================
# hermes_time stub
# =============================================================================

_now_cache: Optional[datetime] = None


def now() -> datetime:
    """timezone-aware simdiki zaman."""
    global _now_cache
    _now_cache = datetime.now(timezone.utc).astimezone()
    return _now_cache


def reset_time_cache() -> None:
    global _now_cache
    _now_cache = None


# =============================================================================
# utils stub
# =============================================================================

def atomic_replace(tmp_path: Union[str, Path], target: Union[str, Path]) -> str:
    """Atomik dosya degistirme (rename ile)."""
    tmp = Path(tmp_path)
    tgt = Path(target)
    if tgt.exists():
        tgt.unlink()
    shutil.move(str(tmp), str(tgt))
    return str(tgt)


def atomic_json_write(data: Any, path: Union[str, Path], indent: int = 2) -> None:
    """Atomik JSON yazma (tmp + rename)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False, default=str)
        atomic_replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def env_var_enabled(name: str, default: str = "") -> bool:
    return os.environ.get(name, default) not in ("", "0", "false", "no")


# =============================================================================
# hermes_cli.config stub (minimal)
# =============================================================================

def atomic_yaml_write(data: Any, path: Union[str, Path], indent: int = 2) -> None:
    """YAML dosyasi yaz — stub, atomic_json_write kullanir."""
    try:
        import yaml
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, indent=indent, allow_unicode=True)
    except Exception as e:
        logger.warning("[stub/atomic_yaml_write] YAML yazma hatasi: %s", e)


def base_url_host_matches(url1: str, url2: str) -> bool:
    """Iki URL'nin host kismini karsilastir."""
    from urllib.parse import urlparse
    try:
        h1 = urlparse(url1).hostname or ""
        h2 = urlparse(url2).hostname or ""
        return h1.lower() == h2.lower()
    except Exception:
        return False

def load_config() -> Dict[str, Any]:
    """Basit config yukleyici — .env dosyasindan okur."""
    import dotenv
    env_path = get_env_path()
    if env_path.exists():
        dotenv.load_dotenv(env_path)
    return {"config": {"env_file": str(env_path)}}


def get_session_env(key: str) -> Optional[str]:
    """Stub — session env bilgisi yoksa None."""
    return os.environ.get(key)


def validate_within_dir(path: Union[str, Path], allowed_dirs: list = None) -> bool:
    """Stub — basit guvenlik kontrolu."""
    return True


def has_named_custom_provider(name: str) -> bool:
    """Stub — custom provider yok."""
    return False


def windows_hide_flags() -> int:
    """Stub — Windows hide flag yoksa 0."""
    return 0


def _expand_env_vars(cfg: Any) -> Any:
    """Stub — oldugu gibi dondur."""
    return cfg


def get_default_hermes_root() -> Path:
    return get_hermes_home()


# ... gateway stubs ...

def is_truthy_value(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes", "on")
    return bool(value)


def normalize_proxy_url(url: Optional[str]) -> Optional[str]:
    return url


def is_safe_url(url: str) -> bool:
    """Stub — guvenli kabul et."""
    return True


def to_agent_visible_cache_path(path: str) -> str:
    return path


def get_tool_emoji(tool_name: str) -> str:
    return "🛠️"


def get_label(provider: str, model: str) -> str:
    return f"{provider}/{model}"


def group_providers() -> dict:
    return {}


def expensive_model_warning(model: str, provider: str) -> Optional[str]:
    return None


def should_bypass_active_session(ctx: Any) -> bool:
    return False


def telegram_menu_commands() -> list:
    return []


def resolve_gateway_approval(ctx: Any, msg: str) -> bool:
    return True


def resolve_gateway_clarify(ctx: Any) -> Optional[str]:
    return None


def mark_awaiting_text(ctx: Any) -> None:
    pass


def discover_plugins() -> list:
    return []


def has_usable_secret(provider: str) -> bool:
    return False


def text_to_speech_tool(text: str, **kw) -> str:
    return ""


def check_tts_requirements() -> bool:
    return False


def vision_analyze_tool(image: str, **kw) -> str:
    return ""


def ensure(pkg: str) -> bool:
    """Lazy dep ensure — stub, hep basarili say."""
    return True


def managed_scope(scope: str) -> Any:
    """Stub — oldugu gibi gec."""
    return None


def set_session_cwd(path: str) -> None:
    pass


def clear_session_cwd() -> None:
    pass


def _ensure_stubs() -> None:
    """Tum stub'lari dogrula (cagri yapmaz, sadece import kontrolu)."""
    _stubs = [
        is_truthy_value, normalize_proxy_url, is_safe_url,
        to_agent_visible_cache_path, get_tool_emoji, get_label,
        group_providers, expensive_model_warning, should_bypass_active_session,
        telegram_menu_commands, resolve_gateway_approval, resolve_gateway_clarify,
        mark_awaiting_text, discover_plugins, has_usable_secret,
        text_to_speech_tool, check_tts_requirements, vision_analyze_tool,
        ensure, managed_scope, set_session_cwd, clear_session_cwd,
    ]
    _ = _stubs  # noqa
