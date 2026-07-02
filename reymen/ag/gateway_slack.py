#!/usr/bin/env python3
"""
ReYMeN Slack Gateway Connector

Slack Incoming Webhook ile mesaj gönderir.
Slack mrkdwn formatı kullanır.

Config:
    platforms:
      slack:
        enabled: false
        channel: "#reymen"
        webhook_url: "${SLACK_WEBHOOK_URL}"

Env:
    SLACK_WEBHOOK_URL — Incoming Webhook URL
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


class SlackGateway(BasePlatformGateway):
    """Slack Incoming Webhook ile mesaj gönderir."""

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
        # ${SLACK_WEBHOOK_URL} -> os.environ
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
        Slack Incoming Webhook'a mesaj gönder.

        POST https://hooks.slack.com/services/T.../B.../x...
        Body: {"text": "...", "channel": "..."}

        Args:
            channel: Hedef kanal adı (#kanal)
            message: Gönderilecek mesaj (mrkdwn formatı)

        Returns:
            dict: {"ok": True} veya {"error": "..."}
        """
        if not self.webhook_url:
            return {"error": "SLACK_WEBHOOK_URL tanımlı değil"}

        payload = {
            "text": message,
        }

        # Slack webhook channel override — sadece config'de belirtilmişse ekle
        if channel:
            payload["channel"] = channel if channel.startswith("#") else f"#{channel}"
            payload["channel"] = payload["channel"].strip()

        # Slack Incoming Webhook text alanı varsayılan olarak mrkdwn destekler
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
                    # Slack webhook başarılı yanıtı: HTTP 200 body "ok"
                    if resp.status == 200 and body.strip().lower() == "ok":
                        logger.info(
                            "✅ Slack mesaj gönderildi -> %s (status=%d)",
                            payload.get("channel", "default"), resp.status,
                        )
                        return {"ok": True, "status": resp.status}
                    else:
                        logger.error(
                            "❌ Slack hata: HTTP %d - %s",
                            resp.status, body,
                        )
                        return {"error": f"HTTP {resp.status}: {body}"}
        except asyncio.TimeoutError:
            logger.error("❌ Slack timeout: %s", self.webhook_url[:50])
            return {"error": "Slack webhook timeout"}
        except aiohttp.ClientError as e:
            logger.error("❌ Slack bağlantı hatası: %s", e)
            return {"error": str(e)}
        except Exception as e:
            logger.exception("❌ Slack beklenmeyen hata")
            return {"error": str(e)}

    async def health_check(self) -> bool:
        """
        Bağlantı kontrolü.

        Webhook URL'sinin formatını kontrol eder:
          - URL boş değil mi?
          - Geçerli bir URL formatı var mı?
          - hooks.slack.com/services/ yolu içeriyor mu? (Slack webhook pattern)
          - HTTP HEAD ile endpoint canlı mı?

        Returns:
            True: sağlıklı
            False: sorun var
        """
        if not self.webhook_url:
            logger.warning("⚠️ Slack health_check: webhook_url boş")
            return False

        # URL formatı kontrolü
        parsed = urlparse(self.webhook_url)
        if not parsed.scheme or not parsed.netloc:
            logger.warning("⚠️ Slack health_check: geçersiz URL formatı")
            return False

        if not parsed.scheme.startswith("http"):
            logger.warning("⚠️ Slack health_check: scheme http değil")
            return False

        # Webhook yolu kontrolü (Slack webhook'ları /services/ ile başlar)
        if "/services/" not in parsed.path:
            logger.warning("⚠️ Slack health_check: URL /services/ içermiyor (geçersiz webhook URL'si olabilir)")
            return False

        # HTTP bağlantı testi — HEAD ile endpoint canlı mı?
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    f"{parsed.scheme}://{parsed.netloc}",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    logger.info("✅ Slack sunucu yanıt veriyor (HTTP %d)", resp.status)
                    return True
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.warning("⚠️ Slack health_check: sunucuya erişilemiyor - %s", e)
            return False
        except Exception as e:
            logger.warning("⚠️ Slack health_check: beklenmeyen hata - %s", e)
            return False

    @staticmethod
    def required_env_vars() -> list[str]:
        """Gerekli çevre değişkenleri."""
        return ["SLACK_WEBHOOK_URL"]


# ── Doğrudan test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test():
        gw = SlackGateway({
            "enabled": True,
            "channel": "#reymen",
            "webhook_url": os.environ.get("SLACK_WEBHOOK_URL", ""),
        })

        print(f"Name:        {gw.name}")
        print(f"Enabled:     {gw.enabled}")
        print(f"Webhook URL: {gw.webhook_url[:60] if gw.webhook_url else '(boş)'}...")
        print(f"Env vars:    {SlackGateway.required_env_vars()}")

        # Sağlık kontrolü
        health = await gw.health_check()
        print(f"\nHealth Check: {'✅' if health else '❌'}")

        if health:
            # Test mesajı gönder
            result = await gw.send_message(
                "#reymen-test",
                "🧪 *ReYMeN* Slack gateway test mesajı\n\n"
                "Eğer bunu görüyorsan bağlantı çalışıyor! ✅\n\n"
                "`kod bloğu` ve *bold* testi.",
            )
            print(f"Send: {result}")

    asyncio.run(test())
