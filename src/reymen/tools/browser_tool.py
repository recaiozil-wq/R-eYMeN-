"""ReYMeN tools.browser_tool shim — Hermes browser fonksiyonlarını ReYMeN browser_engine'e yönlendirir.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _emergency_cleanup_all_sessions() -> None:
    """Hermes browser acil kapatma — ReYMeN browser_engine'e yönlendirir."""
    try:
        from reymen.arac.browser_engine import BrowserEngine

        be = BrowserEngine()
        be.kapat()
        logger.info("Browser sessions cleaned up via ReYMeN browser_engine")
    except Exception as e:
        logger.warning("Browser cleanup failed: %s", e)


def cleanup_all_browsers() -> None:
    """Tüm browser session'larını temizler."""
    _emergency_cleanup_all_sessions()


def cleanup_browser() -> None:
    """Aktif browser session'ını temizler."""
    _emergency_cleanup_all_sessions()


def _stop_cdp_supervisor() -> None:
    """CDP supervisor'ı durdurur. ReYMeN'de kullanılmaz."""
    pass


def _ensure_cdp_supervisor(*args, **kwargs) -> None:
    """CDP supervisor'ı garanti eder. ReYMeN'de direkt Playwright kullanılır."""
    pass


def _get_browser_engine() -> Any:
    """Hermes browser engine referansı — ReYMeN BrowserEngine döndürür."""
    try:
        from reymen.arac.browser_engine import BrowserEngine

        return BrowserEngine()
    except Exception as e:
        logger.warning("BrowserEngine not available: %s", e)
        return None


def _get_cloud_provider() -> Optional[str]:
    """Hermes cloud browser provider — ReYMeN'de local browser kullanılır."""
    return None


# ---------------------------------------------------------------------------
# Ana browser tool fonksiyonları
# ---------------------------------------------------------------------------

def browser_navigate(url: str) -> str:
    """Hermes browser_navigate — ReYMeN browser_engine'e yönlendirir."""
    import json

    try:
        from reymen.arac.browser_engine import BrowserEngine

        be = BrowserEngine()
        be.sayfa_ac(url)
        title = be.sayfa_basligi()
        return json.dumps({"success": True, "title": title, "url": url})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
