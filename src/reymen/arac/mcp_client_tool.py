# -*- coding: utf-8 -*-
"""mcp_client_tool.py — MCP Client (stdio + HTTP) with async support.

Mevcut mcp_tool.py'ye ek olarak:
  - HTTP tabanlı MCP sunucu desteği (aiohttp)
  - Async/await ile non-blocking bağlantı
  - Otomatik tool keşfi ve motor.py'ye kayıt
  - JSON config'den çoklu sunucu yükleme

Kullanım:
    from reymen.arac.mcp_client_tool import mcp_client_baglan, mcp_client_listele

    # Tek sunucu bağla
    mcp_client_baglan("sunucu_adi")

    # Tüm sunucuları listele
    mcp_client_listele()

Config formatı (.ReYMeN/mcp_client.json):
    {
      "servers": {
        "ornek_http": {
          "transport": "http",
          "url": "http://localhost:8080/mcp"
        },
        "ornek_stdio": {
          "transport": "stdio",
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-github"],
          "env": {"GITHUB_TOKEN": "..."}
        }
      }
    }
"""

import asyncio
import json
import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CONFIG_YOLU = Path(__file__).parent.parent / ".ReYMeN" / "mcp_client.json"

# aiohttp opsiyonel
try:
    import aiohttp
    AIOHTTP_OK = True
except ImportError:
    AIOHTTP_OK = False


class MCPClientHTTP:
    """HTTP tabanlı MCP sunucu istemcisi (async)."""

    def __init__(self, ad: str, url: str, headers: Optional[dict] = None):
        self.ad = ad
        self.url = url.rstrip("/")
        self.headers = headers or {}
        self._istek_id = 0
        self._araclar: list[dict] = []
        self._session: Optional[aiohttp.ClientSession] = None
        self._kilit = asyncio.Lock()

    async def baglan(self) -> bool:
        """Sunucuya bağlan, initialize et, tool'ları keşfet."""
        if not AIOHTTP_OK:
            logger.error("[MCPClient] aiohttp kurulu değil: pip install aiohttp")
            return False
        try:
            self._session = aiohttp.ClientSession(
                headers=self.headers, timeout=aiohttp.ClientTimeout(total=30)
            )
            # Initialize
            await self._json_rpc("initialize", {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {"name": "ReYMeN", "version": "1.0"},
            })
            # Tools/list
            yanit = await self._json_rpc("tools/list", {})
            self._araclar = yanit.get("result", {}).get("tools", [])
            logger.info("[MCPClient] %s: %d tool keşfedildi", self.ad, len(self._araclar))
            return True
        except Exception as e:
            logger.error("[MCPClient] %s bağlantı hatası: %s", self.ad, e)
            await self.kapat()
            return False

    async def _json_rpc(self, method: str, params: dict) -> dict:
        if not self._session:
            return {}
        async with self._kilit:
            self._istek_id += 1
            istek = {
                "jsonrpc": "2.0",
                "id": self._istek_id,
                "method": method,
                "params": params,
            }
            try:
                async with self._session.post(
                    self.url, json=istek, headers={"Content-Type": "application/json"}
                ) as resp:
                    return await resp.json()
            except Exception as e:
                logger.error("[MCPClient] JSON-RPC hatası: %s", e)
                return {}

    async def arac_cagir(self, arac_adi: str, parametreler: dict) -> Any:
        """Bir MCP tool'u çağır."""
        yanit = await self._json_rpc("tools/call", {
            "name": arac_adi,
            "arguments": parametreler,
        })
        sonuc = yanit.get("result", {})
        icerik = sonuc.get("content", [])
        if icerik and isinstance(icerik, list):
            return " ".join(
                c.get("text", "") for c in icerik if c.get("type") == "text"
            )
        return str(sonuc)

    def araclar(self) -> list[dict]:
        return self._araclar

    async def kapat(self):
        if self._session and not self._session.closed:
            await self._session.close()


class MCPClientStdio:
    """Stdio tabanlı MCP sunucu istemcisi (sync, subprocess)."""

    def __init__(self, ad: str, komut: list, env: Optional[dict] = None, cwd: str = ""):
        self.ad = ad
        self.komut = komut
        self.env = {**os.environ, **(env or {})}
        self.cwd = cwd or None
        self._proses: Optional[subprocess.Popen] = None
        self._istek_id = 0
        self._kilit = threading.Lock()
        self._araclar: list[dict] = []

    def baglan(self) -> bool:
        try:
            # Windows: npx gibi script'ler CreateProcess ile bulunamaz.
            # shutil.which ile .cmd/.exe yolunu coz.
            komut = self.komut[:]
            if os.name == "nt":
                import shutil
                ilk = komut[0]
                tam_yol = shutil.which(ilk)
                if tam_yol and tam_yol != ilk:
                    komut[0] = tam_yol
            self._proses = subprocess.Popen(
                komut,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.env,
                cwd=self.cwd,
            )
            self._json_rpc("initialize", {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {"name": "ReYMeN", "version": "1.0"},
            })
            yanit = self._json_rpc("tools/list", {})
            self._araclar = yanit.get("result", {}).get("tools", [])
            logger.info("[MCPClient] %s (stdio): %d tool keşfedildi", self.ad, len(self._araclar))
            return True
        except Exception as e:
            logger.error("[MCPClient] %s (stdio) bağlantı hatası: %s", self.ad, e)
            self.kapat()
            return False

    def _json_rpc(self, method: str, params: dict) -> dict:
        with self._kilit:
            self._istek_id += 1
            istek = json.dumps({
                "jsonrpc": "2.0",
                "id": self._istek_id,
                "method": method,
                "params": params,
            }) + "\n"
            try:
                self._proses.stdin.write(istek)
                self._proses.stdin.flush()
                satir = self._proses.stdout.readline()
                return json.loads(satir) if satir else {}
            except Exception as e:
                logger.error("[MCPClient] JSON-RPC (stdio) hatası: %s", e)
                return {}

    def arac_cagir(self, arac_adi: str, parametreler: dict) -> Any:
        yanit = self._json_rpc("tools/call", {
            "name": arac_adi,
            "arguments": parametreler,
        })
        sonuc = yanit.get("result", {})
        icerik = sonuc.get("content", [])
        if icerik and isinstance(icerik, list):
            return " ".join(
                c.get("text", "") for c in icerik if c.get("type") == "text"
            )
        return str(sonuc)

    def araclar(self) -> list[dict]:
        return self._araclar

    def kapat(self):
        if self._proses and self._proses.poll() is None:
            self._proses.terminate()
            try:
                self._proses.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proses.kill()


class MCPClientYoneticisi:
    """Çoklu MCP sunucu yöneticisi (HTTP + stdio)."""

    def __init__(self):
        self._sunucular: dict[str, Any] = {}  # ad -> MCPClientHTTP | MCPClientStdio
        self._konfig: dict = {}               # ad -> ayar (ham config)
        self._konfig_yukle()

    def _konfig_yukle(self):
        """JSON config'den sunucu ayarlarını yükle (sadece ayar, bağlanma)."""
        if not _CONFIG_YOLU.exists():
            return
        try:
            konfig = json.loads(_CONFIG_YOLU.read_text(encoding="utf-8"))
            self._konfig = konfig.get("servers", {})
            logger.info("[MCPClient] %d sunucu config'den yüklendi", len(self._konfig))
        except Exception as e:
            logger.error("[MCPClient] Config yükleme hatası: %s", e)

    def _sunucu_al(self, ad: str) -> Any:
        """Sunucu objesini döndür, gerekirse bağlan."""
        # Zaten bağlıysa döndür
        if ad in self._sunucular:
            s = self._sunucular[ad]
            if isinstance(s, MCPClientStdio) and len(s.araclar()) == 0:
                # Config'den yüklenmiş ama bağlanmamış, bağlan
                if s.baglan():
                    return s
                return None
            return s
        # Config'de var mı kontrol et
        ayar = self._konfig.get(ad)
        if not ayar:
            return None
        transport = ayar.get("transport", "stdio")
        if transport == "http":
            url = ayar.get("url", "")
            headers = ayar.get("headers", {})
            if not url:
                return None
            sunucu = MCPClientHTTP(ad, url, headers)
            loop = asyncio.new_event_loop()
            try:
                basarili = loop.run_until_complete(sunucu.baglan())
            finally:
                loop.close()
            if basarili:
                self._sunucular[ad] = sunucu
                return sunucu
            return None
        else:
            komut = ayar.get("command", "")
            if isinstance(komut, str):
                komut = komut.split()
            args = ayar.get("args", [])
            env = ayar.get("env", {})
            cwd = ayar.get("cwd", "")
            if not komut:
                return None
            sunucu = MCPClientStdio(ad, komut + args, env, cwd)
            if sunucu.baglan():
                self._sunucular[ad] = sunucu
                return sunucu
            return None

    def sunucu_ekle_http(self, ad: str, url: str, headers: Optional[dict] = None) -> bool:
        """HTTP tabanlı MCP sunucusu ekle ve bağlan."""
        if ad in self._sunucular:
            return False
        sunucu = MCPClientHTTP(ad, url, headers)
        # Async bağlantıyı sync context'te çalıştır
        loop = asyncio.new_event_loop()
        try:
            basarili = loop.run_until_complete(sunucu.baglan())
        finally:
            # Session'ı kapatma, sonra kullanılacak
            loop.close()
        if basarili:
            self._sunucular[ad] = sunucu
            return True
        return False

    def sunucu_ekle_stdio(
        self, ad: str, komut: list, env: Optional[dict] = None, cwd: str = ""
    ) -> bool:
        """Stdio tabanlı MCP sunucusu ekle ve bağlan."""
        if ad in self._sunucular:
            return False
        sunucu = MCPClientStdio(ad, komut, env, cwd)
        if sunucu.baglan():
            self._sunucular[ad] = sunucu
            return True
        return False

    def sunucu_kaldir(self, ad: str) -> bool:
        """Sunucuyu kapat ve kaldır."""
        if ad not in self._sunucular:
            return False
        sunucu = self._sunucular[ad]
        if isinstance(sunucu, MCPClientHTTP):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(sunucu.kapat())
            finally:
                loop.close()
        else:
            sunucu.kapat()
        del self._sunucular[ad]
        return True

    def arac_cagir(self, sunucu: str, arac: str, params: dict) -> str:
        """Bir sunucudaki bir aracı çağır."""
        s = self._sunucu_al(sunucu)
        if s is None:
            return f"[MCPClient] '{sunucu}' sunucusu bulunamadı veya bağlanamadı."
        if isinstance(s, MCPClientHTTP):
            loop = asyncio.new_event_loop()
            try:
                sonuc = loop.run_until_complete(s.arac_cagir(arac, params))
            finally:
                loop.close()
            return str(sonuc)
        return str(s.arac_cagir(arac, params))

    def tum_araclar(self) -> dict[str, list[dict]]:
        """Tüm sunucuların tool'larını döndür."""
        # Önce config'deki tüm sunucuları dene (bağlı/bağlananlar)
        sonuc = {}
        for ad in list(self._sunucular.keys()):
            sonuc[ad] = self._sunucular[ad].araclar()
        for ad in self._konfig:
            if ad not in sonuc:
                s = self._sunucu_al(ad)
                if s:
                    sonuc[ad] = s.araclar()
        return sonuc

    def durum(self) -> dict:
        """Sunucu durum raporu."""
        sonuc = {}
        for ad in list(self._sunucular.keys()):
            s = self._sunucular[ad]
            sonuc[ad] = {
                "arac_sayisi": len(s.araclar()),
                "transport": "http" if isinstance(s, MCPClientHTTP) else "stdio",
            }
        return sonuc

    def motor_kaydet(self, motor):
        """Tüm MCP tool'larını motora kaydet."""
        if not hasattr(motor, "_plugin_arac_kaydet"):
            return
        for sunucu_ad, araclar in self.tum_araclar().items():
            for arac in araclar:
                arac_adi = f"MCPCLIENT_{sunucu_ad.upper()}_{arac['name'].upper()}"

                def _fn(sun=sunucu_ad, ar=arac["name"], **kw):
                    return self.arac_cagir(sun, ar, kw)

                try:
                    motor._plugin_arac_kaydet(
                        arac_adi,
                        _fn,
                        arac.get("description", f"MCP Client: {sunucu_ad}/{arac['name']}"),
                    )
                except Exception as e:
                    logger.error("[MCPClient] Motor kayıt hatası (%s): %s", arac_adi, e)

    def kapat_tum(self):
        """Tüm sunucuları kapat."""
        for ad in list(self._sunucular.keys()):
            self.sunucu_kaldir(ad)


# ── Singleton ─────────────────────────────────────────────────────────────

_YONETICI: Optional[MCPClientYoneticisi] = None


def mcp_client() -> MCPClientYoneticisi:
    """Singleton MCP client yöneticisi."""
    global _YONETICI
    if _YONETICI is None:
        _YONETICI = MCPClientYoneticisi()
    return _YONETICI


# ── Public API ────────────────────────────────────────────────────────────

def mcp_client_baglan(sunucu_adi: str) -> str:
    """Belirli bir sunucuya bağlan (config'den veya manuel).

    Args:
        sunucu_adi: Config'de tanımlı sunucu adı

    Returns:
        str: Bağlantı sonucu mesajı
    """
    yonetici = mcp_client()
    # _sunucu_al otomatik bağlanır, zaten bağlıysa direkt döndürür
    s = yonetici._sunucu_al(sunucu_adi)
    if s is None:
        return f"[MCPClient] '{sunucu_adi}' bağlantı başarısız. Config ve ağ bağlantınızı kontrol edin."
    transport = "HTTP" if isinstance(s, MCPClientHTTP) else "STDIO"
    return f"[MCPClient] '{sunucu_adi}' ({transport}) bağlandı. {len(s.araclar())} tool keşfedildi."


def mcp_client_listele() -> str:
    """Tüm bağlı MCP sunucularını ve tool'larını listele."""
    yonetici = mcp_client()
    durum = yonetici.durum()
    if not durum:
        return "[MCPClient] Hiç sunucu bağlı değil. mcp_client_baglan('sunucu_adi') kullanın."

    satirlar = ["[MCPClient] Bağlı Sunucular:", "=" * 50]
    for ad, bilgi in durum.items():
        satirlar.append(f"  {ad} ({bilgi['transport']}): {bilgi['arac_sayisi']} tool")
        for arac in yonetici._sunucular[ad].araclar():
            satirlar.append(f"    - {arac.get('name', '?')}: {arac.get('description', '')[:60]}")
    return "\n".join(satirlar)


def mcp_client_arac_cagir(sunucu: str, arac: str, **parametreler) -> str:
    """Bir MCP sunucusundaki bir aracı çağır.

    Args:
        sunucu: Sunucu adı
        arac: Araç adı
        **parametreler: Araç parametreleri

    Returns:
        str: Araç sonucu
    """
    return mcp_client().arac_cagir(sunucu, arac, parametreler)


def motor_kaydet(motor):
    """MCP Client tool'larını motora kaydet."""
    mcp_client().motor_kaydet(motor)


if __name__ == "__main__":
    print(mcp_client_listele())
    print(f"\nConfig yolu: {_CONFIG_YOLU}")
    print(f"aiohttp: {'OK' if AIOHTTP_OK else 'YOK (pip install aiohttp)'}")