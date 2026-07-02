#!/usr/bin/env python3
"""
ReYMeN Gateway Platform Entegrasyon Sistemi

Her platform için:
  - gateway_<platform>.py (connector)
  - config.yaml'da platform ayarları
  - .env'de API key/credentials
  
Kullanım: 
    from reymen.ag.gateway_manager import GatewayManager
    gm = GatewayManager()
    gm.broadcast("Merhaba Dünya!", platforms=["slack", "matrix"])
"""

import os, json, logging, asyncio
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)

class BasePlatformGateway(ABC):
    """Tüm platform gateway'leri için temel sınıf."""
    
    def __init__(self, config: dict):
        self.config = config
        self.name = self.__class__.__name__.lower()
        self.enabled = config.get("enabled", False)
    
    @abstractmethod
    async def send_message(self, channel: str, message: str) -> dict:
        """Mesaj gönder."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Bağlantı kontrolü."""
        pass
    
    @staticmethod
    @abstractmethod
    def required_env_vars() -> list[str]:
        """Gerekli .env değişkenleri."""
        return []


class GatewayManager:
    """Tüm platformları yönetir."""
    
    def __init__(self, config_path: str = None):
        self.gateways: dict[str, BasePlatformGateway] = {}
        self._load_config(config_path)
    
    def _load_config(self, config_path: Optional[str] = None):
        """Konfigürasyonu yükle."""
        if not config_path:
            config_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "config.yaml"
            )
        # Basit yaml yerine dict kullan
        self._platforms_config = self._default_config()
    
    def _default_config(self) -> dict:
        return {
            "platforms": {
                "slack": {"enabled": False, "channel": "#reymen"},
                "signal": {"enabled": False},
                "matrix": {"enabled": False, "homeserver": "matrix.org"},
                "mattermost": {"enabled": False, "url": "", "webhook_url": "${MATTERMOST_WEBHOOK_URL}"},
                "dingtalk": {"enabled": False},
                "feishu": {"enabled": False},
                "wecom": {"enabled": False},
                "qq": {"enabled": False},
                "teams": {"enabled": False},
                "googlechat": {"enabled": False},
                "homeassistant": {"enabled": False},
                "bluebubbles": {"enabled": False},
            }
        }
    
    def register(self, name: str, gateway: BasePlatformGateway):
        """Gateway kaydet."""
        self.gateways[name] = gateway
        logger.info(f"✅ Gateway kaydedildi: {name}")
    
    async def send(self, platform: str, channel: str, message: str) -> dict:
        """Belirli platforma mesaj gönder."""
        gw = self.gateways.get(platform)
        if not gw:
            return {"error": f"Platform bulunamadı: {platform}"}
        if not gw.enabled:
            return {"error": f"Platform devre dışı: {platform}"}
        return await gw.send_message(channel, message)
    
    async def broadcast(self, message: str, platforms: list[str] = None):
        """Tüm aktif platformlara mesaj gönder."""
        results = {}
        for name, gw in self.gateways.items():
            if not gw.enabled:
                continue
            if platforms and name not in platforms:
                continue
            try:
                ch = gw.config.get("channel", "#general")
                results[name] = await gw.send_message(ch, message)
            except Exception as e:
                results[name] = {"error": str(e)}
        return results
    
    async def health_all(self) -> dict:
        """Tüm platformların sağlık kontrolü."""
        results = {}
        for name, gw in self.gateways.items():
            try:
                ok = await gw.health_check()
                results[name] = "✅" if ok else "❌"
            except Exception as e:
                results[name] = f"❌ {e}"
        return results
    
    def list_enabled(self) -> list[str]:
        """Aktif platformları listele."""
        return [n for n, g in self.gateways.items() if g.enabled]
