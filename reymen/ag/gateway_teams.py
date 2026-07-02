#!/usr/bin/env python3
"""
ReYMeN Microsoft Teams Gateway Connector

Teams Incoming Webhook (Office 365 Connector) ile mesaj gönderir.
MessageCard formatını kullanır.

Config:
    platforms:
      teams:
        enabled: false
        webhook_url: "${TEAMS_WEBHOOK_URL}"

Env:
    TEAMS_WEBHOOK_URL — Teams Incoming Webhook URL (office.com/webhook/...)
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


class TeamsGateway(BasePlatformGateway):
    """Microsoft Teams Incoming Webhook (MessageCard) ile mesaj gönderir."""

    def __init__(self, config: dict):
        super().__init__(config)
        raw_url = config.get("webhook_url", "") or ""
        # ${ENV_VAR} desenini çöz
        self.webhook_url = self._resolve_env_var(raw_url)

    # ── env var çözümleme ──────────────────────────────────────────────

    @staticmethod
    def _resolve_env_var(value: str) -> str:
        """${ENV_VAR} veya $ENV_VAR desenlerini ortam değişkeninden çözümle."""
        if not value:
            return ""
        # ${TEAMS_WEBHOOK_URL} -> os.environ
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
        Teams Incoming Webhook'a MessageCard olarak mesaj gönder.

        POST to webhook URL
        Body: MessageCard (Office 365 Connector) JSON

        Args:
            channel: Kullanılmaz (Teams webhook tek kanala bağlıdır),
                     uyumluluk için korunur.
            message: Gönderilecek mesaj metni.

        Returns:
            dict: {"ok": True} veya {"error": "..."}
        """
        if not self.webhook_url:
            return {"error": "TEAMS_WEBHOOK_URL tanımlı değil"}

        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": "ReYMeN Mesajı",
            "themeColor": "0072C6",
            "title": "ReYMeN",
            "text": message,
        }

        headers = {"Content-Type": "application/json"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    body = await resp.text()
                    if resp.status == 200:
                        logger.info(
                            "✅ Teams mesaj gönderildi (status=%d)",
                            resp.status,
                        )
                        return {"ok": True, "status": resp.status}
                    else:
                        logger.error(
                            "❌ Teams hata: HTTP %d - %s",
                            resp.status, body,
                        )
                        return {"error": f"HTTP {resp.status}: {body}"}
        except asyncio.TimeoutError:
            logger.error("❌ Teams timeout: %s", self.webhook_url[:50])
            return {"error": "Teams webhook timeout"}
        except aiohttp.ClientError as e:
            logger.error("❌ Teams bağlantı hatası: %s", e)
            return {"error": str(e)}
        except Exception as e:
            logger.exception("❌ Teams beklenmeyen hata")
            return {"error": str(e)}

    async def health_check(self) -> bool:
        """
        Bağlantı kontrolü.

        Webhook URL'sinin formatını ve erişilebilirliğini kontrol eder:
          - URL boş değil mi?
          - Geçerli bir URL formatı var mı?
          - URL office.com/webhook yolu içeriyor mu? (Teams pattern)
          - HTTPS kullanıyor mu?

        Returns:
            True: sağlıklı
            False: sorun var
        """
        if not self.webhook_url:
            logger.warning("⚠️ Teams health_check: webhook_url boş")
            return False

        # URL formatı kontrolü
        parsed = urlparse(self.webhook_url)
        if not parsed.scheme or not parsed.netloc:
            logger.warning("⚠️ Teams health_check: geçersiz URL formatı")
            return False

        # Teams webhook'ları HTTPS olmalı
        if parsed.scheme != "https":
            logger.warning("⚠️ Teams health_check: HTTPS gerekli, mevcut: %s", parsed.scheme)
            return False

        # Webhook yolu kontrolü — Teams webhook'ları office.com/webhook/... içerir
        if "office.com/webhook" not in parsed.netloc + parsed.path:
            logger.warning("⚠️ Teams health_check: URL 'office.com/webhook' içermiyor (geçersiz webhook URL'si olabilir)")
            return False

        # HTTP bağlantı testi — HEAD ile endpoint canlı mı?
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    f"{parsed.scheme}://{parsed.netloc}",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    logger.info("✅ Teams sunucu yanıt veriyor (HTTP %d)", resp.status)
                    return True
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.warning("⚠️ Teams health_check: sunucuya erişilemiyor - %s", e)
            return False
        except Exception as e:
            logger.warning("⚠️ Teams health_check: beklenmeyen hata - %s", e)
            return False

    @staticmethod
    def required_env_vars() -> list[str]:
        """Gerekli çevre değişkenleri."""
        return ["TEAMS_WEBHOOK_URL"]


# ── Doğrudan test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test():
        gw = TeamsGateway({
            "enabled": True,
            "webhook_url": os.environ.get("TEAMS_WEBHOOK_URL", ""),
        })

        print(f"Name:        {gw.name}")
        print(f"Enabled:     {gw.enabled}")
        print(f"Webhook URL: {gw.webhook_url[:60] if gw.webhook_url else '(boş)'}...")
        print(f"Env vars:    {TeamsGateway.required_env_vars()}")

        # Sağlık kontrolü
        health = await gw.health_check()
        print(f"\nHealth Check: {'✅' if health else '❌'}")

        if health:
            # Test mesajı gönder
            result = await gw.send_message(
                "#general",
                "🧪 **ReYMeN** Teams gateway test mesajı\n\n"
                "Eğer bunu görüyorsan bağlantı çalışıyor! ✅\n\n"
                "`kod bloğu` ve **bold** testi.",
            )
            print(f"Send: {result}")

    asyncio.run(test())
