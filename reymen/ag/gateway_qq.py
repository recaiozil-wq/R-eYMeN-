#!/usr/bin/env python3
"""
ReYMeN QQ Gateway Connector — reymen/ag/gateway_qq.py

OneBot (NapCat) protokolü üzerinden QQ grup mesajı gönderir.

OneBot HTTP API:
    POST {api_url}/send_group_msg
    Body: {"group_id": GROUP_ID, "message": "mesaj"}

Opsiyonel erişim token'ı Authorization header'ı olarak iletilir:
    Authorization: Bearer {QQ_ACCESS_TOKEN}

Config:
    platforms:
      qq:
        enabled: false
        group_id: "${QQ_GROUP_ID}"
        api_url: "${QQ_API_URL}"

Env:
    QQ_GROUP_ID      — Zorunlu. Hedef QQ grup ID'si
    QQ_API_URL       — Opsiyonel. OneBot HTTP API base URL (varsayılan: http://localhost:3000)
    QQ_ACCESS_TOKEN  — Opsiyonel. OneBot access token
"""

import os
import re
import json
import asyncio
import logging
from typing import Optional

import aiohttp

from reymen.ag.gateway_manager import BasePlatformGateway

logger = logging.getLogger(__name__)


class QQGateway(BasePlatformGateway):
    """QQ platformu için gateway — OneBot (NapCat) HTTP API."""

    def __init__(self, config: dict):
        super().__init__(config)

        # Grup ID'si (zorunlu)
        raw_group_id = config.get("group_id", "") or ""
        self.group_id = self._resolve_env_var(raw_group_id)

        # API URL (opsiyonel, varsayılan: http://localhost:3000)
        raw_api_url = config.get("api_url", "") or ""
        self.api_url = self._resolve_env_var(raw_api_url)
        if not self.api_url:
            self.api_url = os.environ.get("QQ_API_URL", "http://localhost:3000")
        self.api_url = self.api_url.rstrip("/")

        # Access token (opsiyonel)
        self.access_token = os.environ.get("QQ_ACCESS_TOKEN", "") or ""

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

    # ── OneBot HTTP API ile mesaj gönderme ──────────────────────────────

    async def _send_to_group(self, group_id: str, message: str) -> dict:
        """
        OneBot HTTP API'ye POST isteği gönder.

        Endpoint: POST {api_url}/send_group_msg
        Body:
            {
                "group_id": "...",
                "message": "..."
            }

        Eğer QQ_ACCESS_TOKEN tanımlıysa Authorization header'ı eklenir:
            Authorization: Bearer {token}

        Args:
            group_id: Hedef QQ grup ID'si
            message:  Gönderilecek mesaj metni

        Returns:
            dict: {"ok": True} veya {"error": "..."}
        """
        if not group_id:
            return {"error": "QQ: grup ID'si belirtilmedi"}

        url = f"{self.api_url}/send_group_msg"
        payload = {
            "group_id": int(group_id) if group_id.isdigit() else group_id,
            "message": message,
        }
        headers = {"Content-Type": "application/json"}

        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    body = await resp.text()
                    if resp.status in (200, 201):
                        logger.info(
                            "✅ QQ mesaj gönderildi -> grup %s (status=%d)",
                            group_id, resp.status,
                        )
                        return {"ok": True, "status": resp.status}
                    else:
                        logger.error(
                            "❌ QQ API hata: HTTP %d - %s",
                            resp.status, body,
                        )
                        return {"error": f"HTTP {resp.status}: {body}"}
        except asyncio.TimeoutError:
            logger.error("❌ QQ API timeout: %s", self.api_url)
            return {"error": "QQ API timeout"}
        except aiohttp.ClientError as e:
            logger.error("❌ QQ API bağlantı hatası: %s", e)
            return {"error": str(e)}
        except Exception as e:
            logger.exception("❌ QQ API beklenmeyen hata")
            return {"error": str(e)}

    # ── BasePlatformGateway arayüzü ────────────────────────────────────

    async def send_message(self, channel: str = "", message: str = "") -> dict:
        """
        QQ grubuna mesaj gönder.

        channel parametresi grup ID'si olarak kullanılır.
        channel boşsa config'deki group_id (veya env'deki QQ_GROUP_ID) kullanılır.

        Args:
            channel: Hedef QQ grup ID'si (opsiyonel, boşsa config/fallback)
            message: Gönderilecek mesaj metni

        Returns:
            dict: {"ok": True, ...} veya {"error": "..."}
        """
        group_id = channel or self.group_id

        if not group_id:
            return {"error": "QQ: grup ID'si belirtilmedi (channel veya QQ_GROUP_ID)"}

        return await self._send_to_group(group_id, message)

    async def health_check(self) -> bool:
        """
        Bağlantı kontrolü — OneBot API endpoint canlı mı?

        - API URL boş değil mi?
        - Geçerli URL formatı var mı?
        - GET isteği ile endpoint yanıt veriyor mu?

        Returns:
            True: sağlıklı
            False: sorun var
        """
        if not self.api_url:
            logger.warning("⚠️ QQ health_check: api_url boş")
            return False

        # URL formatı kontrolü
        from urllib.parse import urlparse
        parsed = urlparse(self.api_url)
        if not parsed.scheme or not parsed.netloc:
            logger.warning("⚠️ QQ health_check: geçersiz API URL formatı")
            return False

        # HTTP bağlantı testi (ana endpoint'e GET)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    logger.info(
                        "✅ QQ sunucu yanıt veriyor (HTTP %d)",
                        resp.status,
                    )
                    return True
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.warning(
                "⚠️ QQ health_check: sunucuya erişilemiyor - %s", e
            )
            return False
        except Exception as e:
            logger.warning(
                "⚠️ QQ health_check: beklenmeyen hata - %s", e
            )
            return False

    @staticmethod
    def required_env_vars() -> list[str]:
        """Gerekli çevre değişkenleri."""
        return ["QQ_GROUP_ID"]

    def __repr__(self) -> str:
        return (
            f"QQGateway(enabled={self.enabled}, "
            f"group_id={self.group_id}, "
            f"api_url={self.api_url})"
        )


# ── Doğrudan test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test():
        gw = QQGateway({
            "enabled": True,
            "group_id": "${QQ_GROUP_ID}",
            "api_url": "${QQ_API_URL}",
        })

        print("═══════ QQ Gateway Test ═══════")
        print(f"Name:        {gw.name}")
        print(f"Enabled:     {gw.enabled}")
        print(f"Group ID:    {gw.group_id or '(boş)'}")
        print(f"API URL:     {gw.api_url or '(boş)'}")
        print(f"Access Token:{'<set>' if gw.access_token else '(yok)'}")
        print(f"Env vars:    {QQGateway.required_env_vars()}")
        print()

        health = await gw.health_check()
        print(f"Health Check: {'✅' if health else '❌'}")
        print()
        print("repr:", repr(gw))

        # Test mesajı gönderme (sadece env varsa)
        group_id = os.environ.get("QQ_GROUP_ID", "")
        if group_id:
            print()
            print(f"📤 Test mesajı gönderiliyor -> grup {group_id}...")
            result = await gw.send_message(channel="", message="🧪 ReYMeN QQ Gateway test mesajı")
            print(f"Sonuç: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print("ℹ️ QQ_GROUP_ID tanımlı değil, test mesajı atlandı.")

    asyncio.run(test())
