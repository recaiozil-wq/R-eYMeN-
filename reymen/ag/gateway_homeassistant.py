#!/usr/bin/env python3
"""
ReYMeN Home Assistant Gateway Connector

Home Assistant REST API ile notify servisi üzerinden mesaj gönderir.

API:
  POST https://HA_URL/api/services/notify/NOTIFIER
  Header: Authorization: Bearer TOKEN
  Body: {"message": "...", "title": "ReYMeN"}

Config:
    platforms:
      homeassistant:
        enabled: false
        url: "${HOME_ASSISTANT_URL}"
        token: "${HOME_ASSISTANT_TOKEN}"
        notifier: "notify.notify"  # opsiyonel

Env:
    HOME_ASSISTANT_URL      — Home Assistant sunucu URL'si (örn: http://192.168.1.100:8123)
    HOME_ASSISTANT_TOKEN    — Uzun ömürlü access token
    HOME_ASSISTANT_NOTIFIER — Notify servis adı (opsiyonel, varsayılan: notify.notify)
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


class HomeAssistantGateway(BasePlatformGateway):
    """Home Assistant REST API ile mesaj gönderir."""

    def __init__(self, config: dict):
        super().__init__(config)
        raw_url = config.get("url", "") or ""
        raw_token = config.get("token", "") or ""
        raw_notifier = config.get("notifier", "") or ""
        self.ha_url = self._resolve_env_var(raw_url).rstrip("/")
        self.ha_token = self._resolve_env_var(raw_token)
        self.notifier = self._resolve_env_var(raw_notifier) or "notify.notify"

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
        Home Assistant notify servisi ile mesaj gönder.

        POST https://HA_URL/api/services/notify/NOTIFIER
        Header: Authorization: Bearer TOKEN
        Body: {"message": "...", "title": "ReYMeN"}

        Args:
            channel: Kullanılmaz (HA notify tek kanallıdır), notifier adı
                     burada da verilebilir veya config'deki varsayılan kullanılır.
            message: Gönderilecek mesaj metni.

        Returns:
            dict: {"ok": True} veya {"error": "..."}
        """
        if not self.ha_url:
            return {"error": "HOME_ASSISTANT_URL tanımlı değil"}
        if not self.ha_token:
            return {"error": "HOME_ASSISTANT_TOKEN tanımlı değil"}

        # channel parametresi notifier override olarak kullanılabilir
        notifier = channel.strip() if channel else self.notifier

        payload = {
            "message": message,
            "title": "ReYMeN",
        }

        url = f"{self.ha_url}/api/services/notify/{notifier.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.ha_token}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    body = await resp.text()
                    # HA notify başarılı: HTTP 200/201 boş body veya JSON döner
                    if resp.status in (200, 201):
                        logger.info(
                            "✅ HA mesaj gönderildi -> %s (status=%d)",
                            notifier, resp.status,
                        )
                        return {"ok": True, "status": resp.status}
                    else:
                        logger.error(
                            "❌ HA hata: HTTP %d - %s",
                            resp.status, body,
                        )
                        return {"error": f"HTTP {resp.status}: {body}"}
        except asyncio.TimeoutError:
            logger.error("❌ HA timeout: %s", url)
            return {"error": "Home Assistant timeout"}
        except aiohttp.ClientError as e:
            logger.error("❌ HA bağlantı hatası: %s", e)
            return {"error": str(e)}
        except Exception as e:
            logger.exception("❌ HA beklenmeyen hata")
            return {"error": str(e)}

    async def health_check(self) -> bool:
        """
        Bağlantı kontrolü.

        GET /api/ ile HA API'nin erişilebilir olduğunu doğrular.
        - URL boş değil mi?
        - Token boş değil mi?
        - Geçerli URL formatı var mı?
        - GET /api/ yanıt veriyor mu?

        Returns:
            True: sağlıklı
            False: sorun var
        """
        if not self.ha_url:
            logger.warning("⚠️ HA health_check: ha_url boş")
            return False

        if not self.ha_token:
            logger.warning("⚠️ HA health_check: ha_token boş")
            return False

        # URL formatı kontrolü
        parsed = urlparse(self.ha_url)
        if not parsed.scheme or not parsed.netloc:
            logger.warning("⚠️ HA health_check: geçersiz URL formatı")
            return False

        if not parsed.scheme.startswith("http"):
            logger.warning("⚠️ HA health_check: scheme http/https değil")
            return False

        # GET /api/ — HA API root endpoint'i
        api_url = f"{self.ha_url}/api/"
        headers = {
            "Authorization": f"Bearer {self.ha_token}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    api_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        # HA /api/ başarılı yanıtı genellikle
                        # {"message": "API running."} veya bir liste döner
                        body = await resp.json()
                        logger.info(
                            "✅ HA sunucu yanıt veriyor (HTTP %d): %s",
                            resp.status, body,
                        )
                        return True
                    else:
                        body = await resp.text()
                        logger.warning(
                            "⚠️ HA health_check: HTTP %d - %s",
                            resp.status, body,
                        )
                        return False
        except asyncio.TimeoutError:
            logger.warning("⚠️ HA health_check: sunucu timeout")
            return False
        except aiohttp.ClientError as e:
            logger.warning("⚠️ HA health_check: bağlantı hatası - %s", e)
            return False
        except json.JSONDecodeError:
            # Yanıt JSON değilse de başarısız say
            logger.warning("⚠️ HA health_check: geçersiz JSON yanıtı")
            return False
        except Exception as e:
            logger.warning("⚠️ HA health_check: beklenmeyen hata - %s", e)
            return False

    @staticmethod
    def required_env_vars() -> list[str]:
        """Gerekli çevre değişkenleri."""
        return ["HOME_ASSISTANT_URL", "HOME_ASSISTANT_TOKEN"]


# ── Doğrudan test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test():
        notifier = os.environ.get("HOME_ASSISTANT_NOTIFIER", "notify.notify")
        gw = HomeAssistantGateway({
            "enabled": True,
            "url": os.environ.get("HOME_ASSISTANT_URL", ""),
            "token": os.environ.get("HOME_ASSISTANT_TOKEN", ""),
            "notifier": notifier,
        })

        print(f"Name:         {gw.name}")
        print(f"Enabled:      {gw.enabled}")
        print(f"HA URL:       {gw.ha_url or '(boş)'}")
        print(f"Notifier:     {gw.notifier}")
        print(f"Token set:    {'✅' if gw.ha_token else '❌'}")
        print(f"Env vars:     {HomeAssistantGateway.required_env_vars()}")

        # Sağlık kontrolü
        health = await gw.health_check()
        print(f"\nHealth Check: {'✅' if health else '❌'}")

        if health:
            # Test mesajı gönder
            result = await gw.send_message(
                "",
                "🧪 *ReYMeN* Home Assistant gateway test mesajı\n\n"
                "Eğer bunu görüyorsan bağlantı çalışıyor! ✅",
            )
            print(f"Send: {result}")

    asyncio.run(test())
