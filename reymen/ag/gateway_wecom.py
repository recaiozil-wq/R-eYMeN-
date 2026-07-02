#!/usr/bin/env python3
"""
ReYMeN WeCom/WeChat Work Gateway Connector

WeCom (企业微信) Group Robot Webhook ile mesaj gönderir.
Opsiyonel olarak app mesajlaşma (corp_id + agent_id + secret) desteği.

WeCom Bot Webhook:
  POST https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=KEY
  Body: {"msgtype": "text", "text": {"content": "mesaj"}}

Config:
    platforms:
      wecom:
        enabled: false
        webhook_key: "${WECOM_WEBHOOK_KEY}"

Env:
    WECOM_WEBHOOK_KEY — WeCom Robot webhook key (POST https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=KEY)
    WECOM_CORP_ID    — (Opsiyonel) WeCom Corp ID (app mesajlaşma için)
    WECOM_AGENT_ID   — (Opsiyonel) WeCom Agent ID (app mesajlaşma için)
    WECOM_SECRET     — (Opsiyonel) WeCom agent secret (app mesajlaşma için)
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

WECOM_API_BASE = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"

# WeCom app messaging API (opsiyonel)
WECOM_TOKEN_URL = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
WECOM_APP_MSG_URL = "https://qyapi.weixin.qq.com/cgi-bin/message/send"


class WeComGateway(BasePlatformGateway):
    """WeCom (WeChat Work) Group Robot Webhook ile mesaj gönderir."""

    def __init__(self, config: dict):
        super().__init__(config)
        raw_key = config.get("webhook_key", "") or ""
        # ${ENV_VAR} desenini çöz
        self.webhook_key = self._resolve_env_var(raw_key)

        # Opsiyonel app mesajlaşma ayarları
        self.corp_id = self._resolve_env_var(config.get("corp_id", "") or "")
        self.agent_id = self._resolve_env_var(config.get("agent_id", "") or "")
        self.secret = self._resolve_env_var(config.get("secret", "") or "")
        self._access_token = None

    # ── env var çözümleme ──────────────────────────────────────────────

    @staticmethod
    def _resolve_env_var(value: str) -> str:
        """${ENV_VAR} veya $ENV_VAR desenlerini ortam değişkeninden çözümle."""
        if not value:
            return ""
        # ${WECOM_WEBHOOK_KEY} -> os.environ
        match = re.match(r"^\$\{(\w+)\}$", value.strip())
        if match:
            return os.environ.get(match.group(1), "")
        match = re.match(r"^\$(\w+)$", value.strip())
        if match:
            return os.environ.get(match.group(1), "")
        return value

    # ── webhook URL oluşturma ──────────────────────────────────────────

    def _build_webhook_url(self) -> str:
        """Webhook key ile tam webhook URL'sini oluştur."""
        if not self.webhook_key:
            return ""
        return f"{WECOM_API_BASE}?key={self.webhook_key}"

    # ── Opsiyonel: App access token yönetimi ───────────────────────────

    async def _get_app_access_token(self) -> str | None:
        """
        WeCom app mesajlaşma için access token al.

        POST https://qyapi.weixin.qq.com/cgi-bin/gettoken
        Parameters: corpid, corpsecret

        Returns:
            str: access_token veya None
        """
        if not self.corp_id or not self.secret:
            return None

        if self._access_token:
            return self._access_token

        params = {
            "corpid": self.corp_id,
            "corpsecret": self.secret,
        }

        try:
            async with aiohttp.ClientSession() as session:
                token_url = f"{WECOM_TOKEN_URL}?{urlencode(params)}"
                async with session.get(
                    token_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    body = await resp.json()
                    if resp.status == 200 and body.get("errcode") == 0:
                        self._access_token = body.get("access_token")
                        logger.info("✅ WeCom app access token alındı")
                        return self._access_token
                    else:
                        errmsg = body.get("errmsg", "bilinmeyen hata")
                        logger.error(
                            "❌ WeCom token hatası: HTTP %d - errcode=%d errmsg=%s",
                            resp.status, body.get("errcode", -1), errmsg,
                        )
                        return None
        except (asyncio.TimeoutError, aiohttp.ClientError, json.JSONDecodeError) as e:
            logger.error("❌ WeCom token isteği başarısız: %s", e)
            return None

    async def _send_app_message(self, message: str) -> dict:
        """
        WeCom app üzerinden mesaj gönder (opsiyonel).

        POST https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=TOKEN
        Body: {
            "touser": "@all",
            "msgtype": "text",
            "agentid": AGENT_ID,
            "text": {"content": "..."}
        }

        Args:
            message: Gönderilecek mesaj

        Returns:
            dict: {"ok": True} veya {"error": "..."}
        """
        token = await self._get_app_access_token()
        if not token:
            return {"error": "WeCom app access token alınamadı (corp_id/secret kontrol et)"}

        payload = {
            "touser": "@all",
            "msgtype": "text",
            "agentid": int(self.agent_id) if self.agent_id else 0,
            "text": {
                "content": message,
            },
        }

        headers = {"Content-Type": "application/json"}

        try:
            async with aiohttp.ClientSession() as session:
                app_url = f"{WECOM_APP_MSG_URL}?access_token={token}"
                async with session.post(
                    app_url,
                    data=json.dumps(payload, ensure_ascii=False),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    body = await resp.json()
                    errcode = body.get("errcode", -1)
                    errmsg = body.get("errmsg", await resp.text())

                    if resp.status == 200 and errcode == 0:
                        logger.info("✅ WeCom app mesaj gönderildi (errcode=%d)", errcode)
                        return {"ok": True, "status": resp.status, "channel": "app"}
                    else:
                        logger.error(
                            "❌ WeCom app hata: HTTP %d - errcode=%d errmsg=%s",
                            resp.status, errcode, errmsg,
                        )
                        return {
                            "error": f"WeCom app API hatası (HTTP {resp.status}): {errmsg}",
                        }
        except asyncio.TimeoutError:
            logger.error("❌ WeCom app timeout")
            return {"error": "WeCom app mesajlaşma timeout"}
        except aiohttp.ClientError as e:
            logger.error("❌ WeCom app bağlantı hatası: %s", e)
            return {"error": str(e)}

    # ── BasePlatformGateway arayüzü ────────────────────────────────────

    async def send_message(self, channel: str, message: str) -> dict:
        """
        WeCom Robot Webhook'a mesaj gönder.

        POST https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=KEY
        Body: {"msgtype": "text", "text": {"content": "..."}}

        Eğer webhook key yoksa ve app ayarları (corp_id + agent_id + secret)
        varsa, app mesajlaşma API'ine düşer.

        Args:
            channel: Hedef kanal (sadece log için, WeCom webhook channel
                     override desteklemez; 'app' özel değeri app mesajlaşma
                     API'ini tetikler)
            message: Gönderilecek mesaj (düz metin)

        Returns:
            dict: {"ok": True} veya {"error": "..."}
        """
        # channel == "app" ve app ayarları varsa -> app mesajlaşma
        if channel == "app" and self.corp_id and self.agent_id and self.secret:
            return await self._send_app_message(message)

        # Varsayılan: webhook robot mesajı
        webhook_url = self._build_webhook_url()
        if not webhook_url:
            return {"error": "WECOM_WEBHOOK_KEY tanımlı değil"}

        # WeCom bot webhook body formatı (DingTalk ile aynı)
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
                    data=json.dumps(payload, ensure_ascii=False),
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
                            "✅ WeCom mesaj gönderildi (errcode=%d)",
                            errcode,
                        )
                        return {"ok": True, "status": resp.status}
                    else:
                        logger.error(
                            "❌ WeCom hata: HTTP %d - errcode=%d errmsg=%s",
                            resp.status, errcode, errmsg,
                        )
                        return {
                            "error": f"WeCom API hatası (HTTP {resp.status}): {errmsg}",
                        }
        except asyncio.TimeoutError:
            logger.error("❌ WeCom timeout")
            return {"error": "WeCom webhook timeout"}
        except aiohttp.ClientError as e:
            logger.error("❌ WeCom bağlantı hatası: %s", e)
            return {"error": str(e)}
        except Exception as e:
            logger.exception("❌ WeCom beklenmeyen hata")
            return {"error": str(e)}

    async def health_check(self) -> bool:
        """
        Bağlantı kontrolü.

        Webhook key'in varlığını ve formatını kontrol eder,
        ardından qyapi.weixin.qq.com sunucusuna HEAD isteği atar.

        Returns:
            True: sağlıklı
            False: sorun var
        """
        webhook_url = self._build_webhook_url()
        if not webhook_url:
            logger.warning("⚠️ WeCom health_check: webhook_key boş")
            return False

        # URL formatı kontrolü
        parsed = urlparse(webhook_url)
        if not parsed.scheme or not parsed.netloc:
            logger.warning("⚠️ WeCom health_check: geçersiz URL formatı")
            return False

        if not parsed.scheme.startswith("http"):
            logger.warning("⚠️ WeCom health_check: scheme http değil")
            return False

        # Key varlığı kontrolü
        if "key=" not in parsed.query:
            logger.warning("⚠️ WeCom health_check: URL'de key parametresi yok")
            return False

        # HTTP bağlantı testi — HEAD ile endpoint canlı mı?
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    f"{parsed.scheme}://{parsed.netloc}",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    logger.info("✅ WeCom sunucu yanıt veriyor (HTTP %d)", resp.status)
                    return True
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.warning("⚠️ WeCom health_check: sunucuya erişilemiyor - %s", e)
            return False
        except Exception as e:
            logger.warning("⚠️ WeCom health_check: beklenmeyen hata - %s", e)
            return False

    @staticmethod
    def required_env_vars() -> list[str]:
        """Gerekli çevre değişkenleri."""
        return ["WECOM_WEBHOOK_KEY"]


# ── Doğrudan test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test():
        gw = WeComGateway({
            "enabled": True,
            "webhook_key": os.environ.get("WECOM_WEBHOOK_KEY", ""),
            "corp_id": os.environ.get("WECOM_CORP_ID", ""),
            "agent_id": os.environ.get("WECOM_AGENT_ID", ""),
            "secret": os.environ.get("WECOM_SECRET", ""),
        })

        print(f"Name:        {gw.name}")
        print(f"Enabled:     {gw.enabled}")
        print(f"Webhook Key: {'[set]' if gw.webhook_key else '(boş)'}")
        webhook_url = gw._build_webhook_url()
        print(f"Webhook URL: {webhook_url[:80] if gw.webhook_key else '(boş)'}...")
        print(f"Corp ID:     {'✅' if gw.corp_id else '❌ (opsiyonel)'}")
        print(f"Agent ID:    {'✅' if gw.agent_id else '❌ (opsiyonel)'}")
        print(f"Secret:      {'✅' if gw.secret else '❌ (opsiyonel)'}")
        print(f"Env vars:    {WeComGateway.required_env_vars()}")

        # Sağlık kontrolü
        health = await gw.health_check()
        print(f"\nHealth Check: {'✅' if health else '❌'}")

        if health and gw.webhook_key:
            # Test mesajı gönder (webhook robot)
            result = await gw.send_message(
                "",  # WeCom channel kullanmaz
                "🧪 ReYMeN WeCom gateway test mesajı\n\n"
                "Eğer bunu görüyorsan bağlantı çalışıyor! ✅\n\n"
                "`kod bloğu` ve **bold** testi.",
            )
            print(f"Send (webhook): {result}")
        elif gw.corp_id and gw.agent_id and gw.secret:
            # Test mesajı gönder (app)
            result = await gw.send_message(
                "app",
                "🧪 ReYMeN WeCom gateway app test mesajı\n\n"
                "Eğer bunu görüyorsan bağlantı çalışıyor! ✅",
            )
            print(f"Send (app): {result}")

    asyncio.run(test())
