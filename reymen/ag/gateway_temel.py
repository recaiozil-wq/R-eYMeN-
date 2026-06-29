# -*- coding: utf-8 -*-
"""
gateway_temel.py — Gateway ABC temel sinifi.

Tüm platform gateway'leri bu siniftan turer.
Zorunlu metodlar: send, receive, connect, disconnect, health_check.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import time
import logging

logger = logging.getLogger(__name__)


class GatewayBase(ABC):
    """
    Tüm platform gateway'leri için soyut temel sinif.

    Her platform (Telegram, CLI, Web, Discord vb.) bu sinifi
    extend ederek kendi iletisim mantigini uygular.
    """

    def __init__(self, platform_adi: str, config: Optional[Dict[str, Any]] = None):
        self._platform = platform_adi
        self._config = config or {}
        self._bagli = False
        self._calisiyor = False
        self._son_hata: Optional[str] = None
        self._baslangic_zamani: float = 0.0
        self._mesaj_sayaci: int = 0

    # ── Zorunlu Metodlar ─────────────────────────────────────────────

    @abstractmethod
    async def send(self, mesaj: str, hedef: Optional[str] = None,
                   meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Platforma mesaj gonderir."""
        ...

    @abstractmethod
    async def receive(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Platformdan mesaj alir."""
        ...

    @abstractmethod
    async def connect(self) -> bool:
        """Platforma baglanir."""
        ...

    @abstractmethod
    async def disconnect(self) -> bool:
        """Platformla baglantiyi keser."""
        ...

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Platform baglanti sagligini kontrol eder."""
        ...

    # ── Ortak Metodlar ──────────────────────────────────────────────

    @property
    def platform(self) -> str:
        return self._platform

    @property
    def bagli(self) -> bool:
        return self._bagli

    @property
    def calisiyor(self) -> bool:
        return self._calisiyor

    @property
    def son_hata(self) -> Optional[str]:
        return self._son_hata

    @property
    def calisma_suresi(self) -> float:
        if self._baslangic_zamani:
            return time.time() - self._baslangic_zamani
        return 0.0

    @property
    def mesaj_sayisi(self) -> int:
        return self._mesaj_sayaci

    async def start(self) -> bool:
        """Gateway'i baslat — baglan ve calistir."""
        try:
            sonuc = await self.connect()
            if sonuc:
                self._calisiyor = True
                self._baslangic_zamani = time.time()
                logger.info(f"[{self._platform}] Gateway baslatildi.")
            return sonuc
        except Exception as e:
            self._son_hata = str(e)
            logger.error(f"[{self._platform}] Baslatma hatasi: {e}")
            return False

    async def stop(self) -> bool:
        """Gateway'i durdur — baglantiyi kes."""
        try:
            sonuc = await self.disconnect()
            self._calisiyor = False
            logger.info(f"[{self._platform}] Gateway durduruldu.")
            return sonuc
        except Exception as e:
            self._son_hata = str(e)
            logger.error(f"[{self._platform}] Durdurma hatasi: {e}")
            return False

    def durum_raporu(self) -> Dict[str, Any]:
        """Platform durum raporu dondurur."""
        return {
            "platform": self._platform,
            "bagli": self._bagli,
            "calisiyor": self._calisiyor,
            "mesaj_sayisi": self._mesaj_sayaci,
            "calisma_suresi": round(self.calisma_suresi, 2),
            "son_hata": self._son_hata,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}[{self._platform}] bagli={self._bagli}>"


# ── Motor Kayit ─────────────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    """Motor'a gateway araçlarını kaydeder."""
    # GatewayBase — referans olarak kaydet
    motor._plugin_arac_kaydet(
        "GATEWAY_TEMEL_SINIF",
        lambda: "GatewayBase (ABC) — tum gateway'lerin temel sinifi",
        "GatewayBase sinif bilgisi",
    )
