"""ReYMeN website access policy — Bağımsız ReYMeN sürümü.

Website blocklist politikasını REYMEN_HOME/config.yaml'dan okur.
"""

import fnmatch
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_DEFAULT_WEBSITE_BLOCKLIST = {
    "enabled": False,
    "domains": [],
    "shared_files": [],
}

_CACHE_TTL_SECONDS = 30.0
_cache_lock = threading.Lock()
_cached_policy: Optional[Dict[str, Any]] = None
_cached_policy_time: float = 0.0


class WebsitePolicyError(Exception):
    pass


def _get_default_config_path() -> Path:
    """REYMEN_HOME/config.yaml — varsayılan config dosyası."""
    reymen_home = Path(os.environ.get("REYMEN_HOME", str(Path.home() / ".reymen")))
    return reymen_home / "config.yaml"


def _normalize_host(host: str) -> str:
    return (host or "").strip().lower().rstrip(".")


def _normalize_rule(rule: Any) -> Optional[str]:
    if not isinstance(rule, str):
        return None
    value = rule.strip().lower()
    if not value or value.startswith("#"):
        return None
    if "://" in value:
        parsed = urlparse(value)
        value = parsed.netloc or parsed.path
    value = value.split("/", 1)[0].strip().rstrip(".")
    if value.startswith("www."):
        value = value[4:]
    return value or None


def _iter_blocklist_file_rules(path: Path) -> List[str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("Shared blocklist file not found: %s", path)
        return []
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("Failed to read shared blocklist %s: %s", path, exc)
        return []
    rules: List[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        normalized = _normalize_rule(stripped)
        if normalized:
            rules.append(normalized)
    return rules


def _load_policy_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    config_path = config_path or _get_default_config_path()
    if not config_path.exists():
        return dict(_DEFAULT_WEBSITE_BLOCKLIST)
    try:
        import yaml
    except ImportError:
        logger.debug("PyYAML not installed — blocklist disabled")
        return dict(_DEFAULT_WEBSITE_BLOCKLIST)
    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except Exception as exc:
        raise WebsitePolicyError(f"Config error at {config_path}: {exc}") from exc
    if not isinstance(config, dict):
        raise WebsitePolicyError("config root must be a mapping")
    security = config.get("security", {}) or {}
    if not isinstance(security, dict):
        raise WebsitePolicyError("security must be a mapping")
    website_blocklist = security.get("website_blocklist", {}) or {}
    if not isinstance(website_blocklist, dict):
        raise WebsitePolicyError("security.website_blocklist must be a mapping")
    policy = dict(_DEFAULT_WEBSITE_BLOCKLIST)
    policy.update(website_blocklist)
    return policy


def load_website_blocklist(config_path: Optional[Path] = None) -> Dict[str, Any]:
    global _cached_policy, _cached_policy_time
    resolved_path = str(config_path) if config_path else "__default__"
    now = time.monotonic()
    if config_path is None:
        with _cache_lock:
            if (_cached_policy is not None
                    and (now - _cached_policy_time) < _CACHE_TTL_SECONDS):
                return _cached_policy
    config_path = config_path or _get_default_config_path()
    policy = _load_policy_config(config_path)
    raw_domains = policy.get("domains", []) or []
    if not isinstance(raw_domains, list):
        raise WebsitePolicyError("domains must be a list")
    raw_shared_files = policy.get("shared_files", []) or []
    if not isinstance(raw_shared_files, list):
        raise WebsitePolicyError("shared_files must be a list")
    enabled = policy.get("enabled", True)
    if not isinstance(enabled, bool):
        raise WebsitePolicyError("enabled must be a boolean")
    rules: List[Dict[str, str]] = []
    seen: set[Tuple[str, str]] = set()
    for raw_rule in raw_domains:
        normalized = _normalize_rule(raw_rule)
        if normalized and ("config", normalized) not in seen:
            rules.append({"pattern": normalized, "source": "config"})
            seen.add(("config", normalized))
    for shared_file in raw_shared_files:
        if not isinstance(shared_file, str) or not shared_file.strip():
            continue
        path = Path(shared_file).expanduser()
        if not path.is_absolute():
            path = (_get_default_config_path().parent / path).resolve()
        for normalized in _iter_blocklist_file_rules(path):
            key = (str(path), normalized)
            if key in seen:
                continue
            rules.append({"pattern": normalized, "source": str(path)})
            seen.add(key)
    result = {"enabled": enabled, "rules": rules}
    if config_path == _get_default_config_path():
        with _cache_lock:
            _cached_policy = result
            _cached_policy_time = now
    return result


def _match_host_against_rule(host: str, pattern: str) -> bool:
    if not host or not pattern:
        return False
    if pattern.startswith("*."):
        return fnmatch.fnmatch(host, pattern)
    return host == pattern or host.endswith(f".{pattern}")


def _extract_host_from_urlish(url: str) -> str:
    parsed = urlparse(url)
    host = _normalize_host(parsed.hostname or parsed.netloc)
    if host:
        return host
    if "://" not in url:
        schemeless = urlparse(f"//{url}")
        host = _normalize_host(schemeless.hostname or schemeless.netloc)
        if host:
            return host
    return ""


def check_website_access(url: str, config_path: Optional[Path] = None) -> Optional[Dict[str, str]]:
    if config_path is None:
        with _cache_lock:
            if _cached_policy is not None and not _cached_policy.get("enabled"):
                return None
    host = _extract_host_from_urlish(url)
    if not host:
        return None
    try:
        policy = load_website_blocklist(config_path)
    except Exception as exc:
        logger.warning("Failed to load website blocklist: %s", exc)
        return None
    if not policy.get("enabled"):
        return None
    for rule in policy.get("rules", []):
        pattern = rule["pattern"]
        if _match_host_against_rule(host, pattern):
            return {
                "host": host,
                "rule": pattern,
                "source": rule["source"],
                "message": f"Access blocked: {host} matches blocklist rule '{pattern}'",
            }
    return None
