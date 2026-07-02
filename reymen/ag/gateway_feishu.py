#!/usr/bin/env python3
"""
ReYMeN Feishu/Lark Gateway Connector

Feishu bot webhook ile mesaj gönderir.
Opsiyonel olarak JWT kimlik doğrulamalı custom bot desteği (app_id + app_secret).

Feishu Bot Webhook:
  POST https://open.feishu.cn/open-apis/bot/v2/hook/{TOKEN}
  Body: {"msg_type": "text", "content": {"text": "mesaj"}}

Config:
    platforms:
      feishu:
        enabled: false
        webhook_url: "${FEISHU_WEBHOOK_URL}"
        app_id: "${FEISHU_APP_ID}"
        app_secret: "${FEISHU_APP_SECRET}"

Env:
    FEISHU_WEBHOOK_URL — Bot webhook URL (örn: https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx)
    FEISHU_APP_ID     — (Opsiyonel) Custom bot JWT App ID
    FEISHU_APP_SECRET — (Opsiyonel) Custom bot JWT App Secret
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

# Feishu API sabitleri
FEISHU_BASE_URL = "https://open.feishu.cn"
FEISHU_AUTH_PATH = "/open-apis/auth/v3/tenant_access_token/internal"
FEISHU_WEBHOOK_PATH = "/open-apis/bot/v2/hook"


class FeishuGateway(BasePlatformGateway):
    """Feishu/Lark Bot Webhook ile mesaj gönderir."""

    def __init__(self, config: dict):
        super().__init__(config)
        raw_url = config.get("webhook_url", "") or ""
        # ${ENV_VAR} desenini çöz
        self.webhook_url = self._resolve_env_var(raw_url)
        self.app_id = self._resolve_env_var(config.get("app_id", "") or "")
        self.app_secret = self._resolve_env_var(config.get("app_secret", "") or "")
        self._tenant_token = None

    # ── env var çözümleme ──────────────────────────────────────────────

    @staticmethod
    def _resolve_env_var(value: str) -> str:
        """${ENV_VAR} veya $ENV_VAR desenlerini ortam değişkeninden çözümle."""
        if not value:
            return ""
        # ${FEISHU_WEBHOOK_URL} -> os.environ
        match = re.match(r"^\$\{(\w+)\}$", value.strip())
        if match:
            return os.environ.get(match.group(1), "")
        match = re.match(r"^\$(\w+)$", value.strip())
        if match:
            return os.environ.get(match.group(1), "")
        return value

    # ── JWT token yönetimi (opsiyonel custom bot) ─────────────────────

    async def _get_tenant_token(self) -> str | None:
        """
        Feishu custom bot Tenant Access Token al.
        app_id + app_secret gerektirir.
        """
        if not self.app_id or not self.app_secret:
            return None

        if self._tenant_token:
            return self._tenant_token

        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }

        try:
            async with aiohttp.ClientSession() as session:
                auth_url = f"{FEISHU_BASE_URL}{FEISHU_AUTH_PATH}"
                async with session.post(
                    auth_url,
                    data=json.dumps(payload),
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    body = await resp.json()
                    if resp.status == 200 and body.get("code") == 0:
                        self._tenant_token = body.get("tenant_access_token")
                        logger.info("✅ Feishu tenant token alındı")
                        return self._tenant_token
                    else:
                        logger.error(
                            "❌ Feishu token hatası: HTTP %d - %s",
                            resp.status, body,
                        )
                        return None
        except (asyncio.TimeoutError, aiohttp.ClientError, json.JSONDecodeError) as e:
            logger.error("❌ Feishu token isteği başarısız: %s", e)
            return None

    # ── BasePlatformGateway arayüzü ────────────────────────────────────

    async def send_message(self, channel: str, message: str) -> dict:
        """
        Feishu Bot Webhook'a mesaj gönder.

        POST https://open.feishu.cn/open-apis/bot/v2/hook/{TOKEN}
        Body: {"msg_type": "text", "content": {"text": "..."}}

        Not: Feishu bot webhookları channel parametresini desteklemez.
        Mesaj bot'un eklendiği tüm gruplara gönderilmez; sadece webhook
        URL'ine bağlı olan gruba gider. `channel` argümanı log amaçlıdır.

        Args:
            channel: Hedef kanal (sadece log için, Feishu webhook channel override desteklemez)
            message: Gönderilecek mesaj (düz metin)

        Returns:
            dict: {"ok": True} veya {"error": "..."}
        """
        if not self.webhook_url:
            return {"error": "FEISHU_WEBHOOK_URL tanımlı değil"}

        # Feishu bot webhook body formatı
        payload = {
            "msg_type": "text",
            "content": {
                "text": message,
            },
        }

        headers = {"Content-Type": "application/json; charset=utf-8"}

        # Opsiyonel: JWT token varsa Authorization header ekle
        token = await self._get_tenant_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    data=json.dumps(payload, ensure_ascii=False),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    body = await resp.text()
                    if resp.status == 200:
                        logger.info(
                            "✅ Feishu mesaj gönderildi -> %s (status=%d)",
                            channel or "default", resp.status,
                        )
                        return {"ok": True, "status": resp.status}
                    else:
                        logger.error(
                            "❌ Feishu hata: HTTP %d - %s",
                            resp.status, body,
                        )
                        # 410 = bot disabled/removed
                        if resp.status == 410:
                            return {"error": "Bot devre dışı veya kaldırılmış (HTTP 410)"}
                        return {"error": f"HTTP {resp.status}: {body}"}
        except asyncio.TimeoutError:
            logger.error("❌ Feishu timeout: %s", self.webhook_url[:60])
            return {"error": "Feishu webhook timeout"}
        except aiohttp.ClientError as e:
            logger.error("❌ Feishu bağlantı hatası: %s", e)
            return {"error": str(e)}
        except Exception as e:
            logger.exception("❌ Feishu beklenmeyen hata")
            return {"error": str(e)}

    async def health_check(self) -> bool:
        """
        Bağlantı kontrolü.

        Webhook URL'sinin formatını kontrol eder:
          - URL boş değil mi?
          - Geçerli bir URL formatı var mı?
          - open.feishu.cn/open-apis/bot/v2/hook/ yolu içeriyor mu?
          - HTTP HEAD ile endpoint canlı mı?

        Returns:
            True: sağlıklı
            False: sorun var
        """
        if not self.webhook_url:
            logger.warning("⚠️ Feishu health_check: webhook_url boş")
            return False

        # URL formatı kontrolü
        parsed = urlparse(self.webhook_url)
        if not parsed.scheme or not parsed.netloc:
            logger.warning("⚠️ Feishu health_check: geçersiz URL formatı")
            return False

        if not parsed.scheme.startswith("http"):
            logger.warning("⚠️ Feishu health_check: scheme http değil")
            return False

        # Webhook yolu kontrolü (Feishu webhook'ları /open-apis/bot/v2/hook/ ile başlar)
        if FEISHU_WEBHOOK_PATH not in parsed.path:
            logger.warning(
                "⚠️ Feishu health_check: URL %s içermiyor (geçersiz webhook URL'si olabilir)",
                FEISHU_WEBHOOK_PATH,
            )
            return False

        # HTTP bağlantı testi — HEAD ile endpoint canlı mı?
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    f"{parsed.scheme}://{parsed.netloc}",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    logger.info("✅ Feishu sunucu yanıt veriyor (HTTP %d)", resp.status)
                    return True
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.warning("⚠️ Feishu health_check: sunucuya erişilemiyor - %s", e)
            return False
        except Exception as e:
            logger.warning("⚠️ Feishu health_check: beklenmeyen hata - %s", e)
            return False

    @staticmethod
    def required_env_vars() -> list[str]:
        """Gerekli çevre değişkenleri."""
        return ["FEISHU_WEBHOOK_URL"]


# ── Doğrudan test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test():
        gw = FeishuGateway({
            "enabled": True,
            "webhook_url": os.environ.get("FEISHU_WEBHOOK_URL", ""),
            "app_id": os.environ.get("FEISHU_APP_ID", ""),
            "app_secret": os.environ.get("FEISHU_APP_SECRET", ""),
        })

        print(f"Name:        {gw.name}")
        print(f"Enabled:     {gw.enabled}")
        print(f"Webhook URL: {gw.webhook_url[:60] if gw.webhook_url else '(boş)'}...")
        print(f"App ID:      {'✅' if gw.app_id else '❌ (opsiyonel)'}")
        print(f"App Secret:  {'✅' if gw.app_secret else '❌ (opsiyonel)'}")
        print(f"Env vars:    {FeishuGateway.required_env_vars()}")

        # Sağlık kontrolü
        health = await gw.health_check()
        print(f"\nHealth Check: {'✅' if health else '❌'}")

        if health:
            # Test mesajı gönder
            result = await gw.send_message(
                "test-grubu",
                "🧪 *ReYMeN* Feishu gateway test mesajı\n\n"
                "Eğer bunu görüyorsan bağlantı çalışıyor! ✅\n\n"
                "`kod bloğu` ve **bold** testi.",
            )
            print(f"Send: {result}")

    asyncio.run(test())
