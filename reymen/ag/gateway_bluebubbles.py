#!/usr/bin/env python3
"""
ReYMeN BlueBubbles Gateway Connector

BlueBubbles (iMessage bridge) API ile mesaj gönderir.
Private API kullanır: POST /api/v1/chat/send

Config:
    platforms:
      bluebubbles:
        enabled: false
        url: "${BLUEBUBBLES_URL}"
        token: "${BLUEBUBBLES_TOKEN}"
        chat_guid: "${BLUEBUBBLES_CHAT_GUID}"

Env:
    BLUEBUBBLES_URL       — BlueBubbles sunucu adresi ve port (http://host:port)
    BLUEBUBBLES_TOKEN     — API Bearer token
    BLUEBUBBLES_CHAT_GUID — Varsayılan chat GUID (opsiyonel, send_message'a da verilebilir)
"""

import os
import re
import json
import asyncio
import logging
from urllib.parse import urlparse

import aiohttp

from reymen.ag.gateway_manager import BasePlatformGateway

logger = logging.getLogger(__name__)


class BlueBubblesGateway(BasePlatformGateway):
    """BlueBubbles Private API ile iMessage gönderir."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.url = self._resolve_env_var(config.get("url", "") or "")
        self.token = self._resolve_env_var(config.get("token", "") or "")
        self.chat_guid = self._resolve_env_var(config.get("chat_guid", "") or "")

    # ── env var çözümleme ──────────────────────────────────────────────

    @staticmethod
    def _resolve_env_var(value: str) -> str:
        """${ENV_VAR} veya $ENV_VAR desenlerini ortam değişkeninden çözümle."""
        if not value:
            return ""
        match = re.match(r"^\$\{(\w+)\}$", value.strip())
        if match:
            return os.environ.get(match.group(1), "")
        match = re.match(r"^\$(\w+)$", value.strip())
        if match:
            return os.environ.get(match.group(1), "")
        return value

    # ── BasePlatformGateway arayüzü ────────────────────────────────────

    async def send_message(self, channel: str, message: str) -> dict:
        """
        BlueBubbles Private API ile mesaj gönder.

        POST http://BB_URL:PORT/api/v1/chat/send
        Authorization: Bearer TOKEN
        Body: {"chatGuid": "...", "text": "..."}

        Args:
            channel: Hedef chat GUID. Boş bırakılırsa config'deki chat_guid kullanılır.
            message: Gönderilecek mesaj metni.

        Returns:
            dict: {"ok": True} veya {"error": "..."}
        """
        if not self.url:
            return {"error": "BLUEBUBBLES_URL tanımlı değil"}
        if not self.token:
            return {"error": "BLUEBUBBLES_TOKEN tanımlı değil"}

        # chat GUID: önce channel arg, yoksa config'deki varsayılan
        chat_guid = channel or self.chat_guid
        if not chat_guid:
            return {
                "error": "chat_guid belirtilmedi — channel argümanı veya config'deki "
                         "BLUEBUBBLES_CHAT_GUID kullanılabilir"
            }

        # URL'yi normalize et (trailing / temizle)
        base_url = self.url.rstrip("/")
        endpoint = f"{base_url}/api/v1/chat/send"

        payload = {
            "chatGuid": chat_guid,
            "text": message,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    body = await resp.text()
                    if resp.status in (200, 201, 204):
                        logger.info(
                            "✅ BlueBubbles mesaj gönderildi -> %s (status=%d)",
                            chat_guid[:40], resp.status,
                        )
                        return {"ok": True, "status": resp.status}
                    else:
                        logger.error(
                            "❌ BlueBubbles hata: HTTP %d - %s",
                            resp.status, body,
                        )
                        return {"error": f"HTTP {resp.status}: {body}"}
        except asyncio.TimeoutError:
            logger.error("❌ BlueBubbles timeout: %s", base_url)
            return {"error": "BlueBubbles API timeout"}
        except aiohttp.ClientError as e:
            logger.error("❌ BlueBubbles bağlantı hatası: %s", e)
            return {"error": str(e)}
        except Exception as e:
            logger.exception("❌ BlueBubbles beklenmeyen hata")
            return {"error": str(e)}

    async def health_check(self) -> bool:
        """
        BlueBubbles sunucu sağlık kontrolü.

        GET /api/v1/server/ping

        Kontroller:
          - URL boş değil mi?
          - Geçerli URL formatı var mı?
          - Sunucu /api/v1/server/ping endpoint'ine yanıt veriyor mu?

        Returns:
            True: sağlıklı
            False: sorun var
        """
        if not self.url:
            logger.warning("⚠️ BlueBubbles health_check: url boş")
            return False

        base_url = self.url.rstrip("/")
        ping_url = f"{base_url}/api/v1/server/ping"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    ping_url,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    body = await resp.text()
                    if resp.status == 200:
                        logger.info(
                            "✅ BlueBubbles sunucu yanıt veriyor (HTTP %d)",
                            resp.status,
                        )
                        return True
                    else:
                        logger.warning(
                            "⚠️ BlueBubbles health_check: beklenmeyen durum kodu "
                            "HTTP %d - %s", resp.status, body,
                        )
                        return False
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.warning(
                "⚠️ BlueBubbles health_check: sunucuya erişilemiyor - %s", e,
            )
            return False
        except Exception as e:
            logger.warning(
                "⚠️ BlueBubbles health_check: beklenmeyen hata - %s", e,
            )
            return False

    @staticmethod
    def required_env_vars() -> list[str]:
        """Gerekli çevre değişkenleri."""
        return ["BLUEBUBBLES_URL", "BLUEBUBBLES_TOKEN"]


# ── Doğrudan test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test():
        gw = BlueBubblesGateway({
            "enabled": True,
            "url": os.environ.get("BLUEBUBBLES_URL", ""),
            "token": os.environ.get("BLUEBUBBLES_TOKEN", ""),
            "chat_guid": os.environ.get("BLUEBUBBLES_CHAT_GUID", ""),
        })

        print(f"Name:       {gw.name}")
        print(f"Enabled:    {gw.enabled}")
        print(f"URL:        {gw.url or '(boş)'}")
        print(f"Token:      {'***' if gw.token else '(boş)'}")
        print(f"Chat GUID:  {gw.chat_guid[:50] if gw.chat_guid else '(boş)'}")
        print(f"Env vars:   {BlueBubblesGateway.required_env_vars()}")

        # Sağlık kontrolü
        health = await gw.health_check()
        print(f"\nHealth Check: {'✅' if health else '❌'}")

        if health:
            # Test mesajı gönder
            test_guid = gw.chat_guid or ""
            result = await gw.send_message(
                test_guid,
                "🧪 *ReYMeN* BlueBubbles gateway test mesajı\n\n"
                "Eğer bunu görüyorsan bağlantı çalışıyor! ✅\n\n"
                "`kod bloğu` ve **bold** testi.",
            )
            print(f"Send: {result}")

    asyncio.run(test())
