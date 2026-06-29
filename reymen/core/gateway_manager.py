# -*- coding: utf-8 -*-
"""
gateway_manager.py — Gateway Sistemi (multi-platform).

Platform adapter ABC + somut implementasyonlar:
  - GatewayAdapter (ABC): ad, baslat(), durdur(), mesaj_gonder(), durum()
  - TelegramAdapter: Mevcut bot.py'yi sarmalar
  - DiscordAdapter: Mevcut discord_bot.py'yi sarmalar
  - CLIAdapter: stdin/stdout

Hepsi ayni anda calisabilir (multi-platform).
Mevcut GatewayManager (reymen.ag.gateway_yonetici) ile uyumludur.

Motor tools:
  - GATEWAY_LISTE:   Kayitli gateway'leri listele
  - GATEWAY_BASLAT:  Bir gateway'i baslat
  - GATEWAY_DURDUR:  Bir gateway'i durdur
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Sabitler ─────────────────────────────────────────────────────────
PROJE_KOKU = Path(__file__).resolve().parent.parent.parent


# ═══════════════════════════════════════════════════════════════════════
#  Platform Adapter (ABC)
# ═══════════════════════════════════════════════════════════════════════

class GatewayAdapter(ABC):
    """Tum platform gateway'leri icin soyut temel sinif.

    Her platform (Telegram, Discord, CLI) bu sinifi extend ederek
    kendi iletisim mantigini uygular.
    """

    def __init__(self, ad: str, config: Optional[dict[str, Any]] = None):
        self._ad = ad
        self._config = config or {}
        self._calisiyor = False
        self._bagli = False
        self._son_hata: Optional[str] = None
        self._baslangic_zamani: float = 0.0
        self._mesaj_sayisi: int = 0

    # ── Zorunlu Metodlar ────────────────────────────────────────────

    @abstractmethod
    async def baslat(self) -> bool:
        """Gateway'i baslat (baglanti kur + dinlemeye basla)."""
        ...

    @abstractmethod
    async def durdur(self) -> bool:
        """Gateway'i durdur (baglantiyi kes + kaynaklari temizle)."""
        ...

    @abstractmethod
    async def mesaj_gonder(self, mesaj: str, hedef: Optional[str] = None,
                            meta: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Platforma mesaj gonder.

        Args:
            mesaj: Gonderilecek mesaj
            hedef: Platforma ozel hedef (chat_id, kanal_id vb.)
            meta: Ek metadata

        Returns:
            {"basarili": True/False, ...}
        """
        ...

    @abstractmethod
    async def durum(self) -> dict[str, Any]:
        """Platform durum raporu.

        Returns:
            {"ad": ..., "calisiyor": ..., "bagli": ..., "mesaj_sayisi": ...}
        """
        ...

    # ── Ortak Metodlar ──────────────────────────────────────────────

    @property
    def ad(self) -> str:
        return self._ad

    @property
    def calisiyor(self) -> bool:
        return self._calisiyor

    @property
    def bagli(self) -> bool:
        return self._bagli

    @property
    def son_hata(self) -> Optional[str]:
        return self._son_hata

    @property
    def mesaj_sayisi(self) -> int:
        return self._mesaj_sayisi

    @property
    def calisma_suresi(self) -> float:
        if self._baslangic_zamani:
            return time.time() - self._baslangic_zamani
        return 0.0

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}[{self._ad}] calisiyor={self._calisiyor}>"


# ═══════════════════════════════════════════════════════════════════════
#  TelegramAdapter (mevcut bot.py'yi sarmalar)
# ═══════════════════════════════════════════════════════════════════════

class TelegramAdapter(GatewayAdapter):
    """Telegram platform adapteri — mevcut telegram_bot/bot.py'yi sarmalar.

    Bot.py'yi ayri bir subprocess olarak baslatir ve durumunu takip eder.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None, bot_yolu: Optional[str] = None):
        super().__init__("telegram", config)
        self._bot_yolu = bot_yolu or str(PROJE_KOKU / "telegram_bot" / "bot.py")
        self._process: Optional[subprocess.Popen] = None
        self._durum_dosyasi = PROJE_KOKU / ".ReYMeN" / "ai_bot_ReYMeN_ReYMeNbot.json"

    async def baslat(self) -> bool:
        """Telegram bot'unu subprocess olarak baslat."""
        try:
            if not os.path.exists(self._bot_yolu):
                self._son_hata = f"bot.py bulunamadi: {self._bot_yolu}"
                logger.error("[TelegramAdapter] %s", self._son_hata)
                return False

            self._process = subprocess.Popen(
                [sys.executable, self._bot_yolu],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(PROJE_KOKU),
            )

            self._calisiyor = True
            self._bagli = True
            self._baslangic_zamani = time.time()
            self._son_hata = None

            logger.info("[TelegramAdapter] Bot baslatildi (pid=%d)", self._process.pid)
            return True

        except Exception as e:
            self._son_hata = str(e)
            logger.error("[TelegramAdapter] Baslatma hatasi: %s", e)
            return False

    async def durdur(self) -> bool:
        """Telegram bot'unu durdur."""
        try:
            if self._process:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=3)

                self._process = None

            self._calisiyor = False
            self._bagli = False
            logger.info("[TelegramAdapter] Bot durduruldu.")
            return True

        except Exception as e:
            self._son_hata = str(e)
            logger.error("[TelegramAdapter] Durdurma hatasi: %s", e)
            return False

    async def mesaj_gonder(self, mesaj: str, hedef: Optional[str] = None,
                            meta: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Telegram'a mesaj gonder — durum dosyasina yazarak.

        Not: Bot.py telegram API'sine bagli oldugu icin dogrudan gonderim
        yerine durum dosyasi uzerinden iletisim saglanir.
        """
        try:
            if not self._calisiyor:
                return {"basarili": False, "hata": "Telegram bot calismiyor"}

            # Durum dosyasina mesaj yaz (bot.py tarafindan okunur)
            chat_id = hedef or self._config.get("varsayilan_chat_id", "")

            payload = {
                "komut": "mesaj_gonder",
                "mesaj": mesaj,
                "chat_id": chat_id,
                "meta": meta or {},
                "zaman": datetime.now().isoformat(),
            }

            self._durum_dosyasi.parent.mkdir(parents=True, exist_ok=True)
            mevcut = {}
            if self._durum_dosyasi.exists():
                try:
                    mevcut = json.loads(self._durum_dosyasi.read_text(encoding="utf-8"))
                except Exception:
                    pass

            mevcut["_sira_bekleyen_mesaj"] = payload
            self._durum_dosyasi.write_text(
                json.dumps(mevcut, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            self._mesaj_sayisi += 1
            return {"basarili": True, "platform": "telegram", "hedef": chat_id}

        except Exception as e:
            return {"basarili": False, "hata": str(e)}

    async def durum(self) -> dict[str, Any]:
        """Telegram bot durumu."""
        pid = self._process.pid if self._process else None
        process_aktif = pid and self._process and self._process.poll() is None

        # Durum dosyasindan bilgi al
        bot_durum = {}
        if self._durum_dosyasi.exists():
            try:
                bot_durum = json.loads(self._durum_dosyasi.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "ad": self._ad,
            "calisiyor": self._calisiyor and process_aktif,
            "bagli": self._bagli and process_aktif,
            "pid": pid,
            "process_aktif": process_aktif,
            "mesaj_sayisi": self._mesaj_sayisi,
            "calisma_suresi": round(self.calisma_suresi, 2),
            "bot_durum": bot_durum,
            "son_hata": self._son_hata,
            "bot_yolu": self._bot_yolu,
        }


# ═══════════════════════════════════════════════════════════════════════
#  DiscordAdapter (mevcut discord_bot.py'yi sarmalar)
# ═══════════════════════════════════════════════════════════════════════

class DiscordAdapter(GatewayAdapter):
    """Discord platform adapteri — mevcut discord_bot.py'yi sarmalar.

    Discord bot'unu ayri bir subprocess olarak baslatir.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None, bot_yolu: Optional[str] = None):
        super().__init__("discord", config)
        self._bot_yolu = bot_yolu or str(PROJE_KOKU / "reymen" / "ag" / "discord_bot.py")
        self._process: Optional[subprocess.Popen] = None
        self._durum_dosyasi = PROJE_KOKU / ".ReYMeN" / "discord_status.json"

    async def baslat(self) -> bool:
        """Discord bot'unu subprocess olarak baslat."""
        try:
            if not os.path.exists(self._bot_yolu):
                self._son_hata = f"discord_bot.py bulunamadi: {self._bot_yolu}"
                logger.error("[DiscordAdapter] %s", self._son_hata)
                return False

            self._process = subprocess.Popen(
                [sys.executable, self._bot_yolu],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(PROJE_KOKU),
            )

            self._calisiyor = True
            self._bagli = True
            self._baslangic_zamani = time.time()
            self._son_hata = None

            logger.info("[DiscordAdapter] Bot baslatildi (pid=%d)", self._process.pid)
            return True

        except Exception as e:
            self._son_hata = str(e)
            logger.error("[DiscordAdapter] Baslatma hatasi: %s", e)
            return False

    async def durdur(self) -> bool:
        """Discord bot'unu durdur."""
        try:
            if self._process:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=3)
                self._process = None

            self._calisiyor = False
            self._bagli = False
            logger.info("[DiscordAdapter] Bot durduruldu.")
            return True

        except Exception as e:
            self._son_hata = str(e)
            logger.error("[DiscordAdapter] Durdurma hatasi: %s", e)
            return False

    async def mesaj_gonder(self, mesaj: str, hedef: Optional[str] = None,
                            meta: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Discord'a mesaj gonder — durum dosyasina yazarak."""
        try:
            if not self._calisiyor:
                return {"basarili": False, "hata": "Discord bot calismiyor"}

            kanal_id = hedef or self._config.get("varsayilan_kanal_id", "")

            payload = {
                "komut": "mesaj_gonder",
                "mesaj": mesaj,
                "kanal_id": kanal_id,
                "meta": meta or {},
                "zaman": datetime.now().isoformat(),
            }

            self._durum_dosyasi.parent.mkdir(parents=True, exist_ok=True)
            mevcut = {}
            if self._durum_dosyasi.exists():
                try:
                    mevcut = json.loads(self._durum_dosyasi.read_text(encoding="utf-8"))
                except Exception:
                    pass

            mevcut["_sira_bekleyen_mesaj"] = payload
            self._durum_dosyasi.write_text(
                json.dumps(mevcut, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            self._mesaj_sayisi += 1
            return {"basarili": True, "platform": "discord", "hedef": kanal_id}

        except Exception as e:
            return {"basarili": False, "hata": str(e)}

    async def durum(self) -> dict[str, Any]:
        """Discord bot durumu."""
        pid = self._process.pid if self._process else None
        process_aktif = pid and self._process and self._process.poll() is None

        bot_durum = {}
        if self._durum_dosyasi.exists():
            try:
                bot_durum = json.loads(self._durum_dosyasi.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "ad": self._ad,
            "calisiyor": self._calisiyor and process_aktif,
            "bagli": self._bagli and process_aktif,
            "pid": pid,
            "process_aktif": process_aktif,
            "mesaj_sayisi": self._mesaj_sayisi,
            "calisma_suresi": round(self.calisma_suresi, 2),
            "bot_durum": bot_durum,
            "son_hata": self._son_hata,
            "bot_yolu": self._bot_yolu,
        }


# ═══════════════════════════════════════════════════════════════════════
#  CLIAdapter (stdin/stdout)
# ═══════════════════════════════════════════════════════════════════════

class CLIAdapter(GatewayAdapter):
    """CLI platform adapteri — stdin/stdout uzerinden iletisim.

    Mevcut CLIGateway (reymen.ag.platform_gateways) ile uyumludur.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__("cli", config)
        self._girdi_kuyrugu: asyncio.Queue = asyncio.Queue()
        self._okuyucu_gorev: Optional[asyncio.Task] = None

    async def baslat(self) -> bool:
        """CLI kanalini baslat — stdin okuyucuyu baslat."""
        try:
            self._okuyucu_gorev = asyncio.create_task(self._stdin_okuyucu())
            self._calisiyor = True
            self._bagli = True
            self._baslangic_zamani = time.time()
            self._son_hata = None
            logger.info("[CLIAdapter] CLI kanali baslatildi.")
            return True
        except Exception as e:
            self._son_hata = str(e)
            logger.error("[CLIAdapter] Baslatma hatasi: %s", e)
            return False

    async def durdur(self) -> bool:
        """CLI kanalini durdur."""
        try:
            if self._okuyucu_gorev:
                self._okuyucu_gorev.cancel()
                try:
                    await self._okuyucu_gorev
                except asyncio.CancelledError:
                    pass
                self._okuyucu_gorev = None
            self._calisiyor = False
            self._bagli = False
            logger.info("[CLIAdapter] CLI kanali durduruldu.")
            return True
        except Exception as e:
            self._son_hata = str(e)
            return False

    async def mesaj_gonder(self, mesaj: str, hedef: Optional[str] = None,
                            meta: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """CLI'ya mesaj bas (stdout)."""
        try:
            timestamp = time.strftime("%H:%M:%S")
            if meta and meta.get("raw"):
                print(mesaj, end="", flush=True)
            else:
                print(f"\r\033[2K\033[36m[CLI {timestamp}]\033[0m {mesaj}", flush=True)

            self._mesaj_sayisi += 1
            return {"basarili": True, "platform": "cli", "mesaj": mesaj}
        except Exception as e:
            return {"basarili": False, "hata": str(e)}

    async def durum(self) -> dict[str, Any]:
        """CLI kanal durumu."""
        return {
            "ad": self._ad,
            "calisiyor": self._calisiyor,
            "bagli": self._bagli,
            "mesaj_sayisi": self._mesaj_sayisi,
            "calisma_suresi": round(self.calisma_suresi, 2),
            "okuyucu_aktif": self._okuyucu_gorev is not None,
            "son_hata": self._son_hata,
        }

    async def _stdin_okuyucu(self) -> None:
        """Arkaplanda stdin satirlarini kuyruga ekle."""
        try:
            loop = asyncio.get_running_loop()
            while self._calisiyor:
                satir = await loop.run_in_executor(None, sys.stdin.readline)
                if not satir:
                    await asyncio.sleep(0.1)
                    continue
                satir = satir.strip()
                if satir:
                    await self._girdi_kuyrugu.put(satir)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("[CLIAdapter] stdin okuyucu hatasi: %s", e)
            self._son_hata = str(e)

    def girdi_ekle(self, satir: str) -> None:
        """Programatik girdi ekle (test / otomasyon)."""
        try:
            self._girdi_kuyrugu.put_nowait(satir)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════
#  Gateway Yoneticisi (multi-platform)
# ═══════════════════════════════════════════════════════════════════════

class GatewayYoneticisi:
    """Coklu platform gateway yoneticisi — tum adapter'lari ayni anda yonetir.

    Kullanim:
        yonetici = GatewayYoneticisi()
        await yonetici.kaydet(TelegramAdapter())
        await yonetici.kaydet(CLIAdapter())
        await yonetici.kaydet(DiscordAdapter())
        await yonetici.hepsini_baslat()
        await yonetici.mesaj_gonder("telegram", "Merhaba!")
        await yonetici.liste()
    """

    def __init__(self):
        self._adapters: dict[str, GatewayAdapter] = {}

    # ── Kayit / Kaldirma ────────────────────────────────────────────

    def kaydet(self, adapter: GatewayAdapter) -> bool:
        """Bir gateway adapter'ini kaydet.

        Args:
            adapter: GatewayAdapter implementasyonu

        Returns:
            Basarili mi?
        """
        if not isinstance(adapter, GatewayAdapter):
            logger.error("[Gateway] Gecersiz adapter tipi: %s", type(adapter).__name__)
            return False

        if adapter.ad in self._adapters:
            logger.warning("[Gateway] '%s' zaten kayitli, degistiriliyor.", adapter.ad)
            # Eskisini durdur
            eski = self._adapters[adapter.ad]
            if eski.calisiyor:
                # Senkron durdur — arkaplan thread'de
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(eski.durdur())
                except Exception:
                    pass

        self._adapters[adapter.ad] = adapter
        logger.info("[Gateway] '%s' kaydedildi (%s).", adapter.ad, type(adapter).__name__)
        return True

    def kaldir(self, ad: str) -> Optional[GatewayAdapter]:
        """Bir gateway adapter'ini kaldir ve durdur.

        Args:
            ad: Kaldirilacak adapter adi

        Returns:
            Kaldirilan adapter veya None
        """
        adapter = self._adapters.pop(ad, None)
        if adapter and adapter.calisiyor:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(adapter.durdur())
            except Exception:
                pass
            logger.info("[Gateway] '%s' kaldirildi.", ad)
        return adapter

    def get(self, ad: str) -> Optional[GatewayAdapter]:
        """Adapter'i ada gore getir."""
        return self._adapters.get(ad)

    # ── Yasam Dongusu ───────────────────────────────────────────────

    async def baslat(self, ad: str) -> bool:
        """Belirli bir gateway adapter'ini baslat.

        Args:
            ad: Baslatilacak adapter adi

        Returns:
            Basarili mi?
        """
        adapter = self._adapters.get(ad)
        if not adapter:
            logger.error("[Gateway] '%s' bulunamadi.", ad)
            return False

        sonuc = await adapter.baslat()
        if sonuc:
            logger.info("[Gateway] '%s' baslatildi.", ad)
        else:
            hata = adapter.son_hata or "bilinmeyen hata"
            logger.error("[Gateway] '%s' baslatilamadi: %s", ad, hata)

        return sonuc

    async def durdur(self, ad: str) -> bool:
        """Belirli bir gateway adapter'ini durdur.

        Args:
            ad: Durdurulacak adapter adi

        Returns:
            Basarili mi?
        """
        adapter = self._adapters.get(ad)
        if not adapter:
            return False

        sonuc = await adapter.durdur()
        if sonuc:
            logger.info("[Gateway] '%s' durduruldu.", ad)

        return sonuc

    async def hepsini_baslat(self) -> dict[str, bool]:
        """Kayitli tum adapter'lari baslat."""
        sonuclar = {}
        for ad in list(self._adapters.keys()):
            sonuclar[ad] = await self.baslat(ad)
        return sonuclar

    async def hepsini_durdur(self) -> dict[str, bool]:
        """Tum adapter'lari durdur."""
        sonuclar = {}
        for ad in list(self._adapters.keys()):
            sonuclar[ad] = await self.durdur(ad)
        return sonuclar

    # ── Mesaj Gonderimi ─────────────────────────────────────────────

    async def mesaj_gonder(self, platform: str, mesaj: str,
                            hedef: Optional[str] = None,
                            meta: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Belirli bir platforma mesaj gonder.

        Args:
            platform: Hedef platform adi
            mesaj: Gonderilecek mesaj
            hedef: Platforma ozel hedef
            meta: Ek metadata

        Returns:
            Gonderim sonucu
        """
        adapter = self._adapters.get(platform)
        if not adapter:
            return {"basarili": False, "hata": f"'{platform}' platformu bulunamadi"}
        if not adapter.calisiyor:
            return {"basarili": False, "hata": f"'{platform}' calismiyor"}

        return await adapter.mesaj_gonder(mesaj, hedef=hedef, meta=meta)

    async def broadcast(self, mesaj: str,
                         hedef: Optional[str] = None,
                         meta: Optional[dict[str, Any]] = None,
                         platformlar: Optional[list[str]] = None) -> dict[str, Any]:
        """Belirtilen (veya tum) platformlara mesaj gonder.

        Args:
            mesaj: Gonderilecek mesaj
            hedef: Platforma ozel hedef
            meta: Ek metadata
            platformlar: Hedef platform listesi (None = tumu)

        Returns:
            Platform -> gonderim sonucu
        """
        hedefler = platformlar or list(self._adapters.keys())
        sonuclar = {}
        for platform in hedefler:
            sonuc = await self.mesaj_gonder(mesaj, platform, hedef=hedef, meta=meta)
            sonuclar[platform] = sonuc
        return sonuclar

    # ── Listeleme ───────────────────────────────────────────────────

    def liste(self) -> list[dict[str, Any]]:
        """Kayitli tum gateway'lerin durum ozetini listele.

        Returns:
            [{ad, tip, calisiyor, bagli, ...}]
        """
        return [
            {
                "ad": ad,
                "tip": type(adapter).__name__,
                "calisiyor": adapter.calisiyor,
                "bagli": adapter.bagli,
                "mesaj_sayisi": adapter.mesaj_sayisi,
                "son_hata": adapter.son_hata,
            }
            for ad, adapter in self._adapters.items()
        ]

    async def durum_raporu(self) -> dict[str, Any]:
        """Tum platformlarin detayli durum raporu."""
        raporlar = {}
        for ad, adapter in self._adapters.items():
            try:
                raporlar[ad] = await adapter.durum()
            except Exception as e:
                raporlar[ad] = {"hata": str(e)}

        return {
            "platform_sayisi": len(self._adapters),
            "platformlar": raporlar,
            "zaman": time.time(),
        }

    # ── Yardimci ────────────────────────────────────────────────────

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.hepsini_durdur()

    def __repr__(self) -> str:
        return f"<GatewayYoneticisi platform={len(self._adapters)}>"


# ═══════════════════════════════════════════════════════════════════════
#  Tekil Ornek
# ═══════════════════════════════════════════════════════════════════════

_gateway_yonetici: Optional[GatewayYoneticisi] = None


def get_gateway_yoneticisi() -> GatewayYoneticisi:
    """Tekil GatewayYoneticisi ornegini doner."""
    global _gateway_yonetici
    if _gateway_yonetici is None:
        _gateway_yonetici = GatewayYoneticisi()
    return _gateway_yonetici


# ═══════════════════════════════════════════════════════════════════════
#  Motor Tool'lari
# ═══════════════════════════════════════════════════════════════════════

def _gateway_liste() -> str:
    """Motor tool: Kayitli gateway'leri listele.

    Kullanim:
        GATEWAY_LISTE()

    Returns:
        JSON formatinda gateway listesi
    """
    yonetici = get_gateway_yoneticisi()
    liste = yonetici.liste()
    if not liste:
        return "[] — hic gateway kayitli degil"
    return json.dumps(liste, indent=2, ensure_ascii=False, default=str)


def _gateway_baslat(platform: str = "") -> str:
    """Motor tool: Bir gateway'i baslat.

    Kullanim:
        GATEWAY_BASLAT(platform="telegram")
        GATEWAY_BASLAT(platform="discord")
        GATEWAY_BASLAT(platform="cli")

    Args:
        platform: Baslatilacak platform adi

    Returns:
        JSON formatinda sonuc
    """
    if not platform:
        sonuclar = {"hata": "platform parametresi zorunlu. Secenekler: telegram, discord, cli"}
        return json.dumps(sonuclar, ensure_ascii=False)

    yonetici = get_gateway_yoneticisi()

    # Adapter yoksa olustur
    if not yonetici.get(platform):
        if platform == "telegram":
            yonetici.kaydet(TelegramAdapter())
        elif platform == "discord":
            yonetici.kaydet(DiscordAdapter())
        elif platform == "cli":
            yonetici.kaydet(CLIAdapter())
        else:
            return json.dumps({"hata": f"Bilinmeyen platform: {platform}"}, ensure_ascii=False)

    # Baslat
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Zaten calisan loop var — task olarak baslat
            future = asyncio.run_coroutine_threadsafe(yonetici.baslat(platform), loop)
            sonuc = future.result(timeout=10)
        else:
            sonuc = loop.run_until_complete(yonetici.baslat(platform))
    except RuntimeError:
        # Loop yok — yeni loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        sonuc = loop.run_until_complete(yonetici.baslat(platform))
        loop.close()
    except Exception as e:
        sonuc = False
        logger.error("[Gateway] Baslatma hatasi: %s", e)

    return json.dumps({"basarili": sonuc, "platform": platform}, indent=2, ensure_ascii=False)


def _gateway_durdur(platform: str = "") -> str:
    """Motor tool: Bir gateway'i durdur.

    Kullanim:
        GATEWAY_DURDUR(platform="telegram")

    Args:
        platform: Durdurulacak platform adi

    Returns:
        JSON formatinda sonuc
    """
    if not platform:
        return json.dumps({"hata": "platform parametresi zorunlu"}, ensure_ascii=False)

    yonetici = get_gateway_yoneticisi()
    adapter = yonetici.get(platform)
    if not adapter:
        return json.dumps({"hata": f"'{platform}' bulunamadi"}, ensure_ascii=False)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(yonetici.durdur(platform), loop)
            sonuc = future.result(timeout=10)
        else:
            sonuc = loop.run_until_complete(yonetici.durdur(platform))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        sonuc = loop.run_until_complete(yonetici.durdur(platform))
        loop.close()
    except Exception as e:
        sonuc = False
        logger.error("[Gateway] Durdurma hatasi: %s", e)

    return json.dumps({"basarili": sonuc, "platform": platform}, indent=2, ensure_ascii=False)


# ── Motor Kayit ─────────────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    """Motor'a gateway araçlarını kaydeder."""
    motor._plugin_arac_kaydet(
        "GATEWAY_LISTE",
        _gateway_liste,
        "Kayitli gateway'leri listele. "
        "Parametre yok. Donus: JSON formatinda gateway listesi (ad, tip, calisiyor, bagli).",
    )
    motor._plugin_arac_kaydet(
        "GATEWAY_BASLAT",
        _gateway_baslat,
        "Bir gateway'i baslat. "
        "Parametre: platform (str, zorunlu) — 'telegram', 'discord', 'cli'. "
        "Adapter yoksa otomatik olusturulur.",
    )
    motor._plugin_arac_kaydet(
        "GATEWAY_DURDUR",
        _gateway_durdur,
        "Bir gateway'i durdur. "
        "Parametre: platform (str, zorunlu) — 'telegram', 'discord', 'cli'.",
    )
    logger.info("[Gateway] Motor araclari kaydedildi: GATEWAY_LISTE, GATEWAY_BASLAT, GATEWAY_DURDUR")
