# -*- coding: utf-8 -*-
"""
platform_gateways.py — Çoklu platform gateway'leri.

TelegramGateway (salted_gateway modulunden extend edilmistir),
CLIGateway, WebGateway ve DiscordGateway siniflarini icerir.
Her biri GatewayBase soyut sinifini implemente eder.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from reymen.ag.gateway_temel import GatewayBase

# TelegramGateway: salted_gateway modulunden extend et
from reymen.ag.salted_gateway import TelegramGateway as _TelegramGatewayBase

logger = logging.getLogger(__name__)

# ── Sabitler ─────────────────────────────────────────────────────────
PROJE_KOK = Path(__file__).parent.parent  # reymen/


# ═══════════════════════════════════════════════════════════════════════
#  Telegram Gateway (salted_gateway'den extend)
# ═══════════════════════════════════════════════════════════════════════

class TelegramGateway(_TelegramGatewayBase):
    """
    Telegram platform gateway'i — salted_gateway modulunden extend edilmistir.

    salted_gateway.py'deki TelegramGateway sinifini genisletir.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Platforma ozel ek ozellikler buraya eklenebilir


# ═══════════════════════════════════════════════════════════════════════
#  CLI Gateway
# ═══════════════════════════════════════════════════════════════════════

class CLIGateway(GatewayBase):
    """
    Komut satiri (stdin/stdout) gateway'i.

    Dogrudan terminal uzerinden girdi alir, cikti basilir.
    Bot2 / arkaplan CLI senaryolari icin uygundur.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None,
                 girdi_okuyucu: Optional[asyncio.Queue] = None):
        super().__init__("cli", config)
        self._girdi_kuyrugu = girdi_okuyucu or asyncio.Queue()
        self._okuyucu_gorev: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        """CLI kanalini baslat — stdin okuyucuyu baslat."""
        try:
            self._okuyucu_gorev = asyncio.create_task(self._stdin_okuyucu())
            self._bagli = True
            self._son_hata = None
            logger.info("[CLIGateway] CLI kanali baslatildi.")
            return True
        except Exception as e:
            self._son_hata = str(e)
            logger.error(f"[CLIGateway] Baslatma hatasi: {e}")
            return False

    async def disconnect(self) -> bool:
        """CLI kanalini durdur."""
        try:
            if self._okuyucu_gorev:
                self._okuyucu_gorev.cancel()
                self._okuyucu_gorev = None
            self._bagli = False
            logger.info("[CLIGateway] CLI kanali durduruldu.")
            return True
        except Exception as e:
            self._son_hata = str(e)
            return False

    async def send(self, mesaj: str, hedef: Optional[str] = None,
                   meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """CLI'ya mesaj bas (stdout)."""
        try:
            if meta and meta.get("raw"):
                print(mesaj, end="", flush=True)
            else:
                timestamp = time.strftime("%H:%M:%S")
                print(f"\r\033[2K\033[36m[CLI {timestamp}]\033[0m {mesaj}", flush=True)

            self._mesaj_sayaci += 1
            return {"basarili": True, "platform": "cli", "mesaj": mesaj}
        except Exception as e:
            return {"basarili": False, "hata": str(e)}

    async def receive(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """CLI girdisini kuyruktan al."""
        try:
            satir = await asyncio.wait_for(self._girdi_kuyrugu.get(), timeout=timeout)
            return {"platform": "cli", "mesaj": satir, "zaman": time.time()}
        except asyncio.TimeoutError:
            return None

    async def health_check(self) -> Dict[str, Any]:
        """CLI kanali her zaman saglikli (okuyucu kontrolu)."""
        return {
            "durum": "saglikli" if self._okuyucu_gorev else "kopuk",
            "platform": "cli",
            "okuyucu_aktif": self._okuyucu_gorev is not None,
        }

    async def _stdin_okuyucu(self) -> None:
        """Arkaplanda stdin satirlarini kuyruga ekle."""
        try:
            loop = asyncio.get_running_loop()
            while self._bagli:
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
            logger.error(f"[CLIGateway] stdin okuyucu hatasi: {e}")
            self._son_hata = str(e)

    def girdi_ekle(self, satir: str) -> None:
        """Programatik girdi ekle (test / otomasyon)."""
        self._girdi_kuyrugu.put_nowait(satir)


# ═══════════════════════════════════════════════════════════════════════
#  Web Gateway (FastAPI WS/SSE)
# ═══════════════════════════════════════════════════════════════════════

class WebGateway(GatewayBase):
    """
    Web platform gateway'i — FastAPI WebSocket ve SSE destegi.

    Web arayuzune bagli istemcilere gercek zamanli mesaj
    gonderimi saglar. WebSocket ve Server-Sent Events
    protokollerini destekler.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("web", config)
        self._ws_baglantilari: List[Any] = []
        self._sse_kanallari: List[Any] = []
        self._gelen_kuyruk: asyncio.Queue = asyncio.Queue()
        self._sse_gonderim_fonk: Optional[callable] = None

    async def connect(self) -> bool:
        """Web gateway'i baslat."""
        try:
            self._bagli = True
            self._son_hata = None
            logger.info("[WebGateway] Web kanali baslatildi.")
            return True
        except Exception as e:
            self._son_hata = str(e)
            return False

    async def disconnect(self) -> bool:
        """Tum baglantilari kes."""
        try:
            self._ws_baglantilari.clear()
            self._sse_kanallari.clear()
            self._bagli = False
            logger.info("[WebGateway] Web kanali durduruldu.")
            return True
        except Exception as e:
            self._son_hata = str(e)
            return False

    async def send(self, mesaj: str, hedef: Optional[str] = None,
                   meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Tum WebSocket ve SSE istemcilerine mesaj gonder."""
        try:
            if not self._bagli:
                return {"basarili": False, "hata": "Baglanti yok"}

            payload = {
                "tip": meta.get("tip", "mesaj") if meta else "mesaj",
                "icerik": mesaj,
                "zaman": time.time(),
                "kaynak": meta.get("kaynak", "system") if meta else "system",
            }

            # WebSocket istemcilerine gonder
            for ws in list(self._ws_baglantilari):
                try:
                    await ws.send_json(payload)
                except Exception as ws_err:
                    logger.warning(f"[WebGateway] WS gonderim hatasi: {ws_err}")
                    self._ws_baglantilari.remove(ws)

            # SSE kanallarina gonder
            payload_str = json.dumps(payload, ensure_ascii=False)
            if self._sse_gonderim_fonk:
                try:
                    await self._sse_gonderim_fonk(payload_str)
                except Exception as sse_err:
                    logger.warning(f"[WebGateway] SSE gonderim hatasi: {sse_err}")

            self._mesaj_sayaci += 1
            return {"basarili": True, "platform": "web", "hedef_sayisi": len(self._ws_baglantilari)}

        except Exception as e:
            return {"basarili": False, "hata": str(e)}

    async def receive(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Web'den gelen mesaji kuyruktan al."""
        try:
            mesaj = await asyncio.wait_for(self._gelen_kuyruk.get(), timeout=timeout)
            return mesaj
        except asyncio.TimeoutError:
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Web baglanti durumu."""
        return {
            "durum": "saglikli" if self._bagli else "kopuk",
            "platform": "web",
            "ws_baglanti_sayisi": len(self._ws_baglantilari),
            "sse_kanal_sayisi": len(self._sse_kanallari),
        }

    def ws_ekle(self, ws_baglantisi: Any) -> None:
        """WebSocket istemcisi ekle."""
        self._ws_baglantilari.append(ws_baglantisi)
        logger.debug(f"[WebGateway] WS istemci eklendi (toplam: {len(self._ws_baglantilari)})")

    def ws_cikar(self, ws_baglantisi: Any) -> None:
        """WebSocket istemcisi cikar."""
        if ws_baglantisi in self._ws_baglantilari:
            self._ws_baglantilari.remove(ws_baglantisi)

    def sse_kanal_ekle(self, gonderim_fonk: callable) -> None:
        """SSE gonderim kanali ekle."""
        self._sse_gonderim_fonk = gonderim_fonk

    def mesaj_ekle(self, mesaj: Dict[str, Any]) -> None:
        """Web'den gelen mesaji kuyruga ekle."""
        self._gelen_kuyruk.put_nowait(mesaj)


# ═══════════════════════════════════════════════════════════════════════
#  Discord Gateway (Hazirlik — Stub)
# ═══════════════════════════════════════════════════════════════════════

class DiscordGateway(GatewayBase):
    """
    Discord platform gateway'i (hazirlik asamasinda).

    Su an stub durumda. discord.py entegrasyonu icin
    hazir bir cerceve saglar.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("discord", config)
        self._client = None
        self._token: Optional[str] = None
        self._gelen_kuyruk: asyncio.Queue = asyncio.Queue()

    async def connect(self) -> bool:
        """Discord API'sine baglan."""
        try:
            token = self._config.get("token") or os.getenv("DISCORD_BOT_TOKEN", "")
            if not token:
                self._son_hata = "DISCORD_BOT_TOKEN bulunamadi"
                logger.warning(f"[DiscordGateway] {self._son_hata}")
                # Stub mod: token olmadan da bagli say
                self._bagli = True
                return True

            self._token = token

            try:
                import discord
                intents = discord.Intents.default()
                intents.message_content = True
                self._client = discord.Client(intents=intents)
                self._bagli = True
                logger.info("[DiscordGateway] Discord baglantisi hazir.")
            except ImportError:
                logger.warning("[DiscordGateway] discord.py yuklu degil, stub modda.")
                self._bagli = True

            return True

        except Exception as e:
            self._son_hata = str(e)
            logger.error(f"[DiscordGateway] Baglanti hatasi: {e}")
            return False

    async def disconnect(self) -> bool:
        """Discord baglantisini kes."""
        try:
            if self._client:
                await self._client.close()
                self._client = None
            self._bagli = False
            logger.info("[DiscordGateway] Discord baglantisi kesildi.")
            return True
        except Exception as e:
            self._son_hata = str(e)
            return False

    async def send(self, mesaj: str, hedef: Optional[str] = None,
                   meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Discord kanalina mesaj gonder (stub)."""
        try:
            if not self._bagli:
                return {"basarili": False, "hata": "Baglanti yok"}

            kanal_id = hedef or self._config.get("varsayilan_kanal_id")

            if self._client and kanal_id:
                try:
                    kanal = self._client.get_channel(int(kanal_id))
                    if kanal:
                        await kanal.send(mesaj)
                except Exception as send_err:
                    logger.warning(f"[DiscordGateway] Gonderim: {send_err}")

            self._mesaj_sayaci += 1
            return {"basarili": True, "platform": "discord", "hedef": kanal_id}

        except Exception as e:
            return {"basarili": False, "hata": str(e)}

    async def receive(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Discord'dan gelen mesaji al (stub)."""
        try:
            mesaj = await asyncio.wait_for(self._gelen_kuyruk.get(), timeout=timeout)
            return mesaj
        except asyncio.TimeoutError:
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Discord baglanti sagligi (stub)."""
        return {
            "durum": "saglikli" if self._bagli else "kopuk",
            "platform": "discord",
            "stub": True,
        }


# ── Motor Kayit ─────────────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    """Motor'a platform gateway araçlarını kaydeder."""
    motor._plugin_arac_kaydet(
        "GATEWAY_PLATFORM_LISTELE",
        lambda: str([p for p in ["telegram", "cli", "web", "discord"]]),
        "Mevcut platform gateway'lerini listeler",
    )
    motor._plugin_arac_kaydet(
        "GATEWAY_TELEGRAM_OLUSTUR",
        lambda config="{}": f"TelegramGateway(config={config}) — Telegram gateway ornegi olusturur",
        "TelegramGateway olusturma yardimcisi",
    )
    motor._plugin_arac_kaydet(
        "GATEWAY_CLI_OLUSTUR",
        lambda config="{}": f"CLIGateway(config={config}) — CLI gateway ornegi olusturur",
        "CLIGateway olusturma yardimcisi",
    )
    motor._plugin_arac_kaydet(
        "GATEWAY_WEB_OLUSTUR",
        lambda config="{}": f"WebGateway(config={config}) — Web gateway ornegi olusturur",
        "WebGateway olusturma yardimcisi",
    )
    motor._plugin_arac_kaydet(
        "GATEWAY_DISCORD_OLUSTUR",
        lambda config="{}": f"DiscordGateway(config={config}) — Discord gateway (stub) ornegi olusturur",
        "DiscordGateway olusturma yardimcisi",
    )
