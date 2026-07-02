#!/usr/bin/env python3
"""
ReYMeN Google Chat Gateway Connector

Google Chat Incoming Webhook ile mesaj gönderir.
İki mesaj formatı desteklenir:
  - Basit metin: {"text": "..."}
  - Kart (Card): {"cards": [{"header": {...}, "sections": [...]}]}

Config:
    platforms:
      googlechat:
        enabled: false
        webhook_url: "${GOOGLE_CHAT_WEBHOOK_URL}"

Env:
    GOOGLE_CHAT_WEBHOOK_URL — Google Chat Incoming Webhook URL
                            (https://chat.googleapis.com/v1/spaces/.../messages)
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


class GoogleChatGateway(BasePlatformGateway):
    """Google Chat Incoming Webhook ile mesaj gönderir."""

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
        # ${GOOGLE_CHAT_WEBHOOK_URL} -> os.environ
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
        Google Chat Incoming Webhook'a mesaj gönder.

        POST https://chat.googleapis.com/v1/spaces/{space}/messages
        Body (basit metin): {"text": "..."}
        Body (kart):        {"cards": [{"header": {...}, "sections": [...]}]}

        Args:
            channel: Kullanılmaz (Google Chat webhook'u tek bir space'e yönlendirilir).
                     Gelecekte thread/space adı için rezerve edildi.
            message: Gönderilecek mesaj metni.
                     Eğer geçerli bir JSON string ise ve "cards" veya "text" içeriyorsa
                     olduğu gibi gönderilir (gelişmiş kullanım).
                     Aksi halde {"text": message} formatında basit metin olarak gönderilir.

        Returns:
            dict: {"ok": True} veya {"error": "..."}
        """
        if not self.webhook_url:
            return {"error": "GOOGLE_CHAT_WEBHOOK_URL tanımlı değil"}

        # Mesajı hazırla
        payload = self._build_payload(message)

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
                    if resp.status in (200, 204):
                        logger.info(
                            "✅ Google Chat mesaj gönderildi (status=%d)",
                            resp.status,
                        )
                        return {"ok": True, "status": resp.status}
                    else:
                        logger.error(
                            "❌ Google Chat hata: HTTP %d - %s",
                            resp.status, body,
                        )
                        return {"error": f"HTTP {resp.status}: {body}"}
        except asyncio.TimeoutError:
            logger.error("❌ Google Chat timeout: %s", self.webhook_url[:60])
            return {"error": "Google Chat webhook timeout"}
        except aiohttp.ClientError as e:
            logger.error("❌ Google Chat bağlantı hatası: %s", e)
            return {"error": str(e)}
        except Exception as e:
            logger.exception("❌ Google Chat beklenmeyen hata")
            return {"error": str(e)}

    async def health_check(self) -> bool:
        """
        Bağlantı kontrolü.

        Webhook URL'sinin formatını kontrol eder:
          - URL boş değil mi?
          - Geçerli bir URL formatı var mı?
          - chat.googleapis.com domain'indeki bir webhook mu?
          - HTTP bağlantı testi

        Returns:
            True: sağlıklı
            False: sorun var
        """
        if not self.webhook_url:
            logger.warning("⚠️ Google Chat health_check: webhook_url boş")
            return False

        # URL formatı kontrolü
        parsed = urlparse(self.webhook_url)
        if not parsed.scheme or not parsed.netloc:
            logger.warning("⚠️ Google Chat health_check: geçersiz URL formatı")
            return False

        if not parsed.scheme.startswith("http"):
            logger.warning("⚠️ Google Chat health_check: scheme http değil")
            return False

        # Domain kontrolü — Google Chat webhook URL'si chat.googleapis.com olmalı
        if "chat.googleapis.com" not in parsed.netloc:
            logger.warning(
                "⚠️ Google Chat health_check: URL 'chat.googleapis.com' "
                "domain'ini içermiyor (geçersiz webhook olabilir)"
            )
            return False

        # HTTP bağlantı testi — HEAD ile endpoint canlı mı?
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    f"{parsed.scheme}://{parsed.netloc}",
                    timeout=aiohttp.ClientTimeout(total=5),
                    allow_redirects=True,
                ) as resp:
                    logger.info(
                        "✅ Google Chat sunucu yanıt veriyor (HTTP %d)",
                        resp.status,
                    )
                    return True
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            logger.warning(
                "⚠️ Google Chat health_check: sunucuya erişilemiyor - %s", e
            )
            return False
        except Exception as e:
            logger.warning(
                "⚠️ Google Chat health_check: beklenmeyen hata - %s", e
            )
            return False

    @staticmethod
    def required_env_vars() -> list[str]:
        """Gerekli çevre değişkenleri."""
        return ["GOOGLE_CHAT_WEBHOOK_URL"]

    # ── Yardımcı metodlar ──────────────────────────────────────────────

    def _build_payload(self, message: str) -> dict:
        """
        Mesaj string'ini Google Chat webhook payload'ına dönüştürür.

        Eğer message geçerli bir JSON ise (gelişmiş kullanım — kart formatı vb.),
        olduğu gibi kullanılır. Aksi halde {"text": message} olarak basit metin
        formatında gönderilir.

        Gelişmiş kullanım örneği (JSON string):
            {
              "cards": [{
                "header": {
                  "title": "ReYMeN Bildirimi",
                  "subtitle": "Google Chat",
                  "imageUrl": "...",
                  "imageStyle": "IMAGE"
                },
                "sections": [{
                  "widgets": [
                    {"textParagraph": {"text": "<b>Kalın</b> metin"}}
                  ]
                }]
              }]
            }
        """
        # JSON mı diye dene
        if message.strip().startswith(("{", "[")):
            try:
                parsed = json.loads(message)
                if isinstance(parsed, dict) and ("text" in parsed or "cards" in parsed):
                    # Geçerli bir Google Chat payload formatı
                    logger.debug("📋 Google Chat: JSON payload kullanılıyor")
                    return parsed
                elif isinstance(parsed, dict):
                    # Başka bir JSON dict — text'e sar
                    return {"text": message}
            except json.JSONDecodeError:
                pass

        # Basit metin
        return {"text": message}


# ── Doğrudan test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def test():
        gw = GoogleChatGateway({
            "enabled": True,
            "webhook_url": os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", ""),
        })

        print(f"Name:        {gw.name}")
        print(f"Enabled:     {gw.enabled}")
        print(f"Webhook URL: {gw.webhook_url[:60] if gw.webhook_url else '(boş)'}...")
        print(f"Env vars:    {GoogleChatGateway.required_env_vars()}")

        # Sağlık kontrolü
        health = await gw.health_check()
        print(f"\nHealth Check: {'✅' if health else '❌'}")

        if health and gw.webhook_url:
            # Test mesajı gönder (basit metin)
            result = await gw.send_message(
                "",
                "🧪 *ReYMeN* Google Chat gateway test mesajı\n\n"
                "Eğer bunu görüyorsan bağlantı çalışıyor! ✅\n\n"
                "`kod bloğu` testi.",
            )
            print(f"Send (text): {result}")

            # Test mesajı gönder (kart formatı - JSON string)
            card_payload = json.dumps({
                "cards": [{
                    "header": {
                        "title": "ReYMeN Test Kartı",
                        "subtitle": "Google Chat Gateway",
                    },
                    "sections": [{
                        "widgets": [
                            {
                                "textParagraph": {
                                    "text": "Bu bir <b>kart</b> formatı testidir."
                                }
                            }
                        ]
                    }]
                }]
            })
            result2 = await gw.send_message("", card_payload)
            print(f"Send (card): {result2}")

    asyncio.run(test())
