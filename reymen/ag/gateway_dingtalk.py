#!/usr/bin/env python3
"""
ReYMeN DingTalk Gateway Connector

DingTalk (钉钉) Group Robot Webhook ile mesaj gönderir.

API Referansı:
  POST https://oapi.dingtalk.com/robot/send?access_token=TOKEN
  Body: {"msgtype": "text", "text": {"content": "..."}}

Config:
    platforms:
      dingtalk:
        enabled: false
        access_token: "${DINGTALK_ACCESS_TOKEN}"

Env:
    DINGTALK_ACCESS_TOKEN — DingTalk Robot access token
"""

import os
import re
import json
import asyncio
import logging
from urllib.parse import urlencode, urlparse

import aiohttp

from reymen.ag.gateway_manager import BasePlatformGateway

logger = logging.getLogger(__name__)

DINGTALK_API_BASE = "https://oapi.dingtalk.com/robot/send"


class DingTalkGateway(BasePlatformGateway):
    """DingTalk Group Robot Webhook ile mesaj gönderir."""

    def __init__(self, config: dict):
        super().__init__(config)
        raw_token = config.get("access_token", "") or ""
        # ${ENV_VAR} desenini çöz
        self.access_token = self._resolve_env_var(raw_token)

    # ── env var çözümleme ──────────────────────────────────────────────

    @staticmethod
    def _resolve_env_var(value: str) -> str:
        """${ENV_VAR} veya $ENV_VAR desenlerini ortam değişkeninden çözümle."""
        if not value:
            return ""
        # ${DINGTALK_ACCESS_TOKEN} -> os.environ
        match = re.match(r"^\$\{(\w+)\}$", value.strip())
        if match:
            return os.environ.get(match.group(1), "")
        match = re.match(r"^\$(\w+)$", value.strip())
        if match:
            return os.environ.get(match.group(1), "")
        return value

    # ── webhook URL oluşturma ──────────────────────────────────────────

    def _build_webhook_url(self) -> str:
        """Access token ile tam webhook URL'sini oluştur."""
        if not self.access_token:
            return ""
        return f"{DINGTALK_API_BASE}?access_token={self.access_token}"

    # ── BasePlatformGateway arayüzü ────────────────────────────────────

    async def send_message(self, channel: str, message: str) -> dict:
        """
        DingTalk Robot Webhook'a mesaj gönder.

        POST https://oapi.dingtalk.com/robot/send?access_token=TOKEN
        Body: {"msgtype": "text", "text": {"content": "..."}}

        Args:
            channel: Kullanılmıyor (DingTalk robot kanal seçmez),
                     sadece BasePlatformGateway arayüzü uyumu için.
            message: Gönderilecek mesaj (düz metin)

        Returns:
            dict: {"ok": True} veya {"error": "..."}
        """
        webhook_url = self._build_webhook_url()
        if not webhook_url:
            return {"error": "DINGTALK_ACCESS_TOKEN tanımlı değil"}

        payload = {
            "msgtype": "text",
            "text": {
                "content": message,
            },
        }

        headers = {"Content-Type": "application/json"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    body = await resp.text()
                    try:
                        data = json.loads(body)
                    except json.JSONDecodeError:
                        data = {}

                    errcode = data.get("errcode", -1)
                    errmsg = data.get("errmsg", body)

                    if resp.status == 200 and errcode == 0:
                        logger.info(
                            "✅ DingTalk mesaj gönderildi (errcode=%d)",
                            errcode,
                        )
                        return {"ok": True, "status": resp.status}
                    else:
                        logger.error(
                            "❌ DingTalk hata: HTTP %d - errcode=%d errmsg=%s",
                            resp.status, errcode, errmsg,
                        )
                        return {
                            "error": f"DingTalk API hatası (HTTP {resp.status}): {errmsg}",
                        }
        except asyncio.TimeoutError:
            logger.error("❌ DingTalk timeout")
            return {"error": "DingTalk webhook timeout"}
        except aiohttp.ClientError as e:
            logger.error("❌ DingTalk bağlantı hatası: %s", e)
            return {"error": str(e)}
        except Exception as e:
            logger.exception("❌ DingTalk beklenmeyen hata")
            return {"error": str(e)}

    async def health_check(self) -> bool:
        """
        Bağlantı kontrolü.

        Access token'ın varlığını ve formatını kontrol eder,
        ardından oapi.dingtalk.com sunucusuna HEAD isteği atar.

        Returns:
            True: sağlıklı
            False: sorun var
        """
        webhook_url = self._build_webhook_url()
        if not webhook_url:
            logger.warning("⚠️ DingTalk health_check: access_token boş")
            return False

        # URL formatı kontrolü
        parsed = urlparse(webhook_url)
        if not parsed.scheme or not parsed.netloc:
            logger.warning("⚠️ DingTalk health_check: geçersiz URL formatı")
            return False

        if not parsed.scheme.startswith("http"):
            logger.warning("⚠️ DingTalk health_check: scheme http değil")
            return False

        # Token varlığı kontrolü
        if "access_token=" not in parsed.query:
            logger.warning("⚠️ DingTalk health_check: URL'de access_token yok")
            return False

        # HTTP bağlantı testi — HEAD ile endpoint canlı mı?
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    f"{parsed.scheme}://{parsed.netloc}",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    logger.info("✅ DingTalk sunucu yanıt veriyor (HTTP %d)", resp.status)
                    return True
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.warning("⚠️ DingTalk health_check: sunucuya erişilemiyor - %s", e)
            return False
        except Exception as e:
            logger.warning("⚠️ DingTalk health_check: beklenmeyen hata - %s", e)
            return False

    @staticmethod
    def required_env_vars() -> list[str]:
        """Gerekli çevre değişkenleri."""
        return ["DINGTALK_ACCESS_TOKEN"]


# ── Doğrudan test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test():
        gw = DingTalkGateway({
            "enabled": True,
            "access_token": os.environ.get("DINGTALK_ACCESS_TOKEN", ""),
        })

        print(f"Name:        {gw.name}")
        print(f"Enabled:     {gw.enabled}")
        print(f"Token:       {'[set]' if gw.access_token else '(boş)'}")
        print(f"Webhook URL: {gw._build_webhook_url()[:80] if gw.access_token else '(boş)'}...")
        print(f"Env vars:    {DingTalkGateway.required_env_vars()}")

        # Sağlık kontrolü
        health = await gw.health_check()
        print(f"\nHealth Check: {'✅' if health else '❌'}")

        if health and gw.access_token:
            # Test mesajı gönder
            result = await gw.send_message(
                "",  # DingTalk channel kullanmaz
                "🧪 ReYMeN DingTalk gateway test mesajı\n\n"
                "Eğer bunu görüyorsan bağlantı çalışıyor! ✅\n\n"
                "`kod bloğu` ve **bold** testi.",
            )
            print(f"Send: {result}")

    asyncio.run(test())
