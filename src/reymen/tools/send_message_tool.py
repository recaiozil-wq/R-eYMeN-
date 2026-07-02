"""ReYMeN tools.send_message_tool shim — Hermes mesajlaşma fonksiyonlarını yönlendirir."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _parse_target_ref(target: str) -> Dict[str, Any]:
    """Hermes _parse_target_ref — hedef referansını çözümler."""
    return {"platform": "telegram", "chat_id": target}


def _send_to_platform(
    platform: str,
    chat_id: str,
    message: str,
    **kwargs,
) -> bool:
    """Hermes _send_to_platform — mesajı platforma gönderir."""
    try:
        if platform == "telegram":
            token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            if not token:
                logger.warning("TELEGRAM_BOT_TOKEN not set")
                return False

            import urllib.request
            import urllib.parse

            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": message[:4096],
                "parse_mode": "Markdown",
            }).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        else:
            logger.warning("Unsupported platform: %s", platform)
            return False
    except Exception as e:
        logger.warning("_send_to_platform failed: %s", e)
        return False


def telegram_gonder(chat_id: str, mesaj: str) -> str:
    """Hermes telegram_gonder — ReYMeN Telegram API'sine yönlendirir."""
    success = _send_to_platform("telegram", chat_id, mesaj)
    return json.dumps({"success": success, "chat_id": chat_id})


def telegram_resim_gonder(chat_id: str, resim_yolu: str, altyazi: str = "") -> str:
    """Hermes telegram_resim_gonder — ReYMeN Telegram API'sine yönlendirir."""
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not token:
            return json.dumps({"success": False, "error": "TELEGRAM_BOT_TOKEN not set"})

        import urllib.request

        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        import json as _json
        data = _json.dumps({
            "chat_id": chat_id,
            "photo": resim_yolu,
            "caption": altyazi,
        }).encode()
        req = urllib.request.Request(url, data=data,
                                      headers={"Content-Type": "application/json"},
                                      method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            success = resp.status == 200
            return json.dumps({"success": success, "chat_id": chat_id})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
