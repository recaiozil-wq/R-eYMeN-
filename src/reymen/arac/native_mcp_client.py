# -*- coding: utf-8 -*-
"""
native_mcp_client.py — LEGACY Native MCP Client (Korunuyor).

⚠️  LEGACY / ESKI — Sadece geriye uyumluluk icin korunuyor.
    Yeni gelistirmeler icin reymen/mcp/* paketini kullanin:
      - reymen.mcp.mcp_manager      (async MCP yoneticisi)
      - reymen.mcp.mcp_reconnect    (heartbeat + yeniden baglanma)
      - reymen.mcp.mcp_discovery    (konfig + .env kesfi)
      - reymen.mcp.mcp_tool         (motor arac kaydi)
      - reymen.mcp.mcp_catalog      (onceden tanimli sunucu katalogu)

    Bu modul silinmemeli, cunku dis bagimliliklar (plugin'ler, skill'ler,
    dogrudan import eden kodlar) olabilir. Ancak yeni ozellik eklenmez.

ReYMeN Native MCP Client ozellikleri (legacy):
  - Baslangicta otomatik kesif (discover_mcp_tools)
  - Her sunucu ayri arkaplan thread'de calisir
  - Otomatik yeniden baglanma (exponential backoff, max 5, 60s)
  - mcp_{sunucu}_{arac} isimlendirme
  - Motor'a otomatik kayit
  - YAPI konfig (config.yaml) + JSON geriye uyumluluk

Konfig
  ~/.hermes/config.yaml veya .ReYMeN/config.yaml icinde:
    mcp_servers:
      filesystem:
        command: "npx"
        args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        timeout: 30
      github:
        url: "https://api.github.com/mcp"
        headers:
          Authorization: "Bearer ghp_xxx"
"""

import asyncio
import json
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ── Varsayilan konfig yollari ──────────────────────────────────────────────
REYMEN_KOK = Path(__file__).parent.parent  # reymen/
CONFIG_YOLLARI = [
    REYMEN_KOK / ".ReYMeN" / "config.yaml",
    REYMEN_KOK / ".ReYMeN" / "mcp_client.json",
    REYMEN_KOK.parent / "config.yaml",
    Path.home() / ".ReYMeN" / "config.yaml",
]

# aiohttp opsiyonel
try:
    import aiohttp
    AIOHTTP_OK = True
except ImportError:
    AIOHTTP_OK = False

# pyyaml opsiyonel
try:
    import yaml
    YAML_OK = True
except ImportError:
    YAML_OK = False


@dataclass
class MCPSunucuConfig:
    """Tek bir MCP sunucusu konfigurasyonu."""
    ad: str
    komut: Optional[str] = None        # stdio: calistirilacak program
    args: list[str] = field(default_factory=list)      # stdio: argumanlar
    env: dict[str, str] = field(default_factory=dict)  # stdio: ek ortam degiskenleri
    url: Optional[str] = None          # HTTP: sunucu URL
    headers: dict[str, str] = field(default_factory=dict)  # HTTP: basliklar
    timeout: int = 120                 # arac timeout
    connect_timeout: int = 60          # baglanti timeout

    @property
    def transport(self) -> str:
        if self.url:
            return "http"
        return "stdio"


class MCPBaglanti:
    """Tek bir MCP sunucusu baglantisi (async + thread ile)."""

    def __init__(self, config: MCPSunucuConfig):
        self.config = config
        self._proses: Optional[subprocess.Popen] = None
        self._session: Any = None
        self._istek_id = 0
        self._kilit = threading.Lock()
        self._araclar: list[dict] = []
        self._bagli = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._durduruldu = False

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def bagli(self) -> bool:
        return self._bagli

    @property
    def araclar(self) -> list[dict]:
        return self._araclar

    def baslat(self) -> bool:
        """Baglantiyi baslat (sync wrapper)."""
        if self.config.transport == "http":
            if not AIOHTTP_OK:
                logger.error("[MCP] aiohttp gerekli: pip install aiohttp")
                return False
            # HTTP icin async loop baslat
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(
                target=self._http_thread_loop,
                daemon=True,
                name=f"mcp-{self.config.ad}",
            )
            self._thread.start()
            # Baglanti olusana kadar bekle
            for _ in range(30):
                if self._bagli:
                    return True
                time.sleep(0.1)
            return self._bagli
        else:
            # Stdio: senkron baglan
            return self._stdio_baglan()

    def arac_cagir(self, arac_adi: str, parametreler: dict) -> str:
        """Bir tool'u cagir."""
        if self.config.transport == "http":
            return self._http_arac_cagir(arac_adi, parametreler)
        return self._stdio_arac_cagir(arac_adi, parametreler)

    def kapat(self):
        """Baglantiyi kapat."""
        self._durduruldu = True
        if self.config.transport == "http":
            if self._loop and not self._loop.is_closed():
                try:
                    self._loop.call_soon_threadsafe(self._loop.stop)
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )
            if self._proses and self._proses.poll() is None:
                self._proses.terminate()
        else:
            if self._proses and self._proses.poll() is None:
                self._proses.terminate()
                try:
                    self._proses.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proses.kill()
        self._bagli = False

    # ── HTTP Transport ────────────────────────────────────────────────────

    def _http_thread_loop(self):
        """HTTP baglantisi icin ayri event loop thread'i."""
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._http_baglan_ve_koru())
        except Exception as e:
            logger.error("[MCP] %s event loop hatasi: %s", self.config.ad, e)

    async def _http_baglan_ve_koru(self):
        """Baglan, araclari kesfet, sonra canli tut (yeniden baglanma ile)."""
        deneme = 0
        while not self._durduruldu:
            try:
                # Yeniden baglanma araligi (exponential backoff)
                if deneme > 0:
                    bekle = min(2 ** deneme, 60)  # max 60s
                    logger.info("[MCP] %s yeniden baglaniyor (deneme %d, bekle %ds)...",
                                self.config.ad, deneme + 1, bekle)
                    await asyncio.sleep(bekle)

                async with aiohttp.ClientSession(
                    headers=self.config.headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.connect_timeout),
                ) as session:
                    self._session = session
                    # Initialize
                    init_yanit = await self._json_rpc_http("initialize", {
                        "protocolVersion": "0.1.0",
                        "capabilities": {},
                        "clientInfo": {"name": "ReYMeN", "version": "1.0"},
                    })
                    if "result" not in init_yanit:
                        raise ConnectionError("Initialize basarisiz")

                    # Tools/list
                    yanit = await self._json_rpc_http("tools/list", {})
                    self._araclar = yanit.get("result", {}).get("tools", [])
                    self._bagli = True
                    deneme = 0
                    logger.info("[MCP] %s (HTTP): %d tool kesfedildi",
                                self.config.ad, len(self._araclar))

                    # Baglantiyi canli tut — sunucu kapatana kadar bekle
                    while not self._durduruldu:
                        await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._bagli = False
                deneme += 1
                if deneme > 5:
                    logger.error("[MCP] %s 5 kez denendi, vazgeciliyor: %s",
                                 self.config.ad, e)
                    break
                logger.warning("[MCP] %s baglanti koptu (deneme %d/5): %s",
                               self.config.ad, deneme, e)

    async def _json_rpc_http(self, method: str, params: dict) -> dict:
        """HTTP JSON-RPC istegi."""
        if not self._session or self._session.closed:
            return {}
        istek = {
            "jsonrpc": "2.0",
            "id": self._istek_id + 1,
            "method": method,
            "params": params,
        }
        self._istek_id += 1
        try:
            async with self._session.post(
                self.config.url,
                json=istek,
                headers={"Content-Type": "application/json"},
            ) as resp:
                return await resp.json()
        except Exception as e:
            logger.error("[MCP] HTTP JSON-RPC hatasi (%s): %s", self.config.ad, e)
            return {}

    def _http_arac_cagir(self, arac_adi: str, parametreler: dict) -> str:
        """HTTP tool cagrisi (sync wrapper)."""
        if not self._loop or self._loop.is_closed():
            return "[MCP] Baglanti aktif degil"
        gelecek = asyncio.run_coroutine_threadsafe(
            self._http_arac_cagir_async(arac_adi, parametreler),
            self._loop,
        )
        try:
            return gelecek.result(timeout=self.config.timeout)
        except asyncio.TimeoutError:
            return f"[MCP] {arac_adi} zamani asimi ({self.config.timeout}s)"
        except Exception as e:
            return f"[MCP] {arac_adi} hatasi: {e}"

    async def _http_arac_cagir_async(self, arac_adi: str, parametreler: dict) -> str:
        """HTTP tool cagrisi (async)."""
        yanit = await self._json_rpc_http("tools/call", {
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

    # ── Stdio Transport ────────────────────────────────────────────────────

    def _stdio_baglan(self) -> bool:
        """Stdio baglantisi baslat."""
        try:
            komut = [self.config.komut] + self.config.args if self.config.komut else []
            if not komut:
                return False
            # Windows: npx gibi script'ler CreateProcess ile bulunamaz.
            # shutil.which ile .cmd/.exe yolunu coz.
            if os.name == "nt":
                import shutil
                ilk = komut[0]
                tam_yol = shutil.which(ilk)
                if tam_yol and tam_yol != ilk:
                    komut[0] = tam_yol
            env = {**os.environ, **self.config.env}
            self._proses = subprocess.Popen(
                komut,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            # Initialize
            self._stdio_json_rpc("initialize", {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {"name": "ReYMeN", "version": "1.0"},
            })
            # Tools/list
            yanit = self._stdio_json_rpc("tools/list", {})
            self._araclar = yanit.get("result", {}).get("tools", [])
            self._bagli = True
            # Periyodik canli-kontrol icin thread baslat
            self._thread = threading.Thread(
                target=self._stdio_canli_koru,
                daemon=True,
                name=f"mcp-{self.config.ad}-watchdog",
            )
            self._thread.start()
            logger.info("[MCP] %s (stdio): %d tool kesfedildi",
                        self.config.ad, len(self._araclar))
            return True
        except Exception as e:
            logger.error("[MCP] %s (stdio) baglanti hatasi: %s", self.config.ad, e)
            self._stdio_kapat()
            return False

    def _stdio_canli_koru(self):
        """Stdio baglantisini canli tut, koparsa yeniden baglan."""
        deneme = 0
        while not self._durduruldu:
            time.sleep(5)
            if self._proses and self._proses.poll() is not None:
                # Baglanti koptu
                self._bagli = False
                deneme += 1
                if deneme > 5:
                    logger.error("[MCP] %s stdio 5 kez denendi, vazgeciliyor",
                                 self.config.ad)
                    break
                bekle = min(2 ** deneme, 60)
                logger.info("[MCP] %s stdio yeniden basliyor (deneme %d, bekle %ds)...",
                            self.config.ad, deneme, bekle)
                time.sleep(bekle)
                if self._stdio_baglan():
                    deneme = 0

    def _stdio_json_rpc(self, method: str, params: dict) -> dict:
        """Stdio JSON-RPC istegi."""
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
                logger.error("[MCP] Stdio JSON-RPC hatasi (%s): %s",
                             self.config.ad, e)
                return {}

    def _stdio_arac_cagir(self, arac_adi: str, parametreler: dict) -> str:
        """Stdio tool cagrisi."""
        if not self._bagli:
            return "[MCP] Baglanti aktif degil"
        yanit = self._stdio_json_rpc("tools/call", {
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

    def _stdio_kapat(self):
        """Stdio baglantisini kapat."""
        if self._proses and self._proses.poll() is None:
            self._proses.terminate()
            try:
                self._proses.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proses.kill()
        self._proses = None
        self._bagli = False


class NativeMCPClient:
    """ReYMeN-tarzi Native MCP Client yoneticisi.

    Baslangicta config'deki tum sunuculara otomatik baglanir,
    araclari kesfeder ve motor'a kaydeder.
    """

    def __init__(self):
        self._baglantilar: dict[str, MCPBaglanti] = {}
        self._motor_ref: Any = None
        self._kesfedildi = False

    # ── Config Yukleme ────────────────────────────────────────────────────

    def konfig_yukle(self) -> list[MCPSunucuConfig]:
        """Config dosyasindan MCP sunucu ayarlarini yukle.

        Oncelik sirasi:
          1. .ReYMeN/config.yaml (mcp_servers:)
          2. .ReYMeN/mcp_client.json (servers:)
          3. ~/.hermes/config.yaml (mcp_servers:)
        """
        for yol in CONFIG_YOLLARI:
            if not yol.exists():
                continue
            try:
                if yol.suffix in (".yaml", ".yml"):
                    sunucular = self._yaml_oku(yol)
                else:
                    sunucular = self._json_oku(yol)
                if sunucular:
                    logger.info("[MCP] %d sunucu %s'den yuklendi",
                                len(sunucular), yol)
                    return sunucular
            except Exception as e:
                logger.warning("[MCP] %s okuma hatasi: %s", yol, e)
        return []

    def _yaml_oku(self, yol: Path) -> list[MCPSunucuConfig]:
        """YAML config dosyasindan MCP sunuculari oku.

        Format:
          mcp_servers:
            sunucu_adi:
              command: "npx"
              args: ["-y", "paket"]
              env: {KEY: val}
              url: "https://..."
              headers: {Auth: "Bearer ..."}
              timeout: 120
        """
        if not YAML_OK:
            logger.warning("[MCP] pyyaml kurulu degil, JSON config kullaniliyor")
            return []
        icerik = yol.read_text(encoding="utf-8")
        data = yaml.safe_load(icerik)
        if not data:
            return []
        servers = data.get("mcp_servers", {})
        if not servers:
            # Alternatif: duz yaml icinde servers: anahtari
            servers = data.get("servers", data)
        sonuc = []
        for ad, ayar in servers.items():
            if not isinstance(ayar, dict):
                continue
            sonuc.append(MCPSunucuConfig(
                ad=ad,
                komut=ayar.get("command"),
                args=ayar.get("args", []),
                env=ayar.get("env", {}),
                url=ayar.get("url"),
                headers=ayar.get("headers", {}),
                timeout=ayar.get("timeout", 120),
                connect_timeout=ayar.get("connect_timeout", 60),
            ))
        return sonuc

    def _json_oku(self, yol: Path) -> list[MCPSunucuConfig]:
        """JSON config dosyasindan MCP sunuculari oku (geriye uyumluluk).

        Format:
          {"servers": {
            "sunucu_adi": {
              "transport": "stdio",
              "command": "npx",
              "args": [...],
              "env": {...}
            }
          }}
        """
        icerik = yol.read_text(encoding="utf-8")
        data = json.loads(icerik)
        servers = data.get("servers", data)
        sonuc = []
        for ad, ayar in servers.items():
            if not isinstance(ayar, dict):
                continue
            transport = ayar.get("transport", "stdio")
            if transport == "http":
                sonuc.append(MCPSunucuConfig(
                    ad=ad,
                    url=ayar.get("url"),
                    headers=ayar.get("headers", {}),
                    timeout=ayar.get("timeout", 120),
                    connect_timeout=ayar.get("connect_timeout", 60),
                ))
            else:
                komut = ayar.get("command", "")
                if isinstance(komut, str):
                    komut_list = komut.split() if " " in komut else [komut]
                else:
                    komut_list = komut
                args = ayar.get("args", [])
                sonuc.append(MCPSunucuConfig(
                    ad=ad,
                    komut=komut_list[0] if komut_list else None,
                    args=komut_list[1:] + args if len(komut_list) > 1 else args,
                    env=ayar.get("env", {}),
                    timeout=ayar.get("timeout", 120),
                    connect_timeout=ayar.get("connect_timeout", 60),
                ))
        return sonuc

    # ── Baglanti Yonetimi ─────────────────────────────────────────────────

    def baglan(self, config: MCPSunucuConfig) -> bool:
        """Bir MCP sunucusuna baglan."""
        if config.ad in self._baglantilar:
            logger.info("[MCP] %s zaten bagli, atlaniyor", config.ad)
            return True
        baglanti = MCPBaglanti(config)
        if baglanti.baslat():
            self._baglantilar[config.ad] = baglanti
            logger.info("[MCP] %s baglandi (%d tool)", config.ad, len(baglanti.araclar))
            return True
        logger.warning("[MCP] %s baglanamadi", config.ad)
        return False

    def baglanti_kaldir(self, ad: str) -> bool:
        """Bir sunucu baglantisini kaldir."""
        if ad not in self._baglantilar:
            return False
        self._baglantilar[ad].kapat()
        del self._baglantilar[ad]
        return True

    def baglanti_kontrol(self, ad: str) -> bool:
        """Belirli bir sunucunun bagli olup olmadigini kontrol et."""
        baglanti = self._baglantilar.get(ad)
        return baglanti is not None and baglanti.bagli

    def tum_baglantilari_kapat(self):
        """Tum baglantilari kapat."""
        for ad in list(self._baglantilar.keys()):
            self.baglanti_kaldir(ad)

    # ── Araclari Kesfetme ve Kaydetme ─────────────────────────────────────

    def discover_mcp_tools(self, motor_ref: Any = None):
        """ReYMeN-tarzi otomatik MCP arac kesfi.

        Cagri sirasi:
          1. Config'deki tum sunuculari yukle
          2. Henuz bagli olmayanlara baglan
          3. Araclari motor'a kaydet
        """
        if motor_ref:
            self._motor_ref = motor_ref

        # 1. Config yukle
        sunucular = self.konfig_yukle()
        if not sunucular:
            logger.info("[MCP] Config'de MCP sunucu bulunamadi")
            return

        # 2. Baglan (sadece bagli olmayanlar)
        yeni_sayisi = 0
        for cfg in sunucular:
            if cfg.ad not in self._baglantilar:
                if self.baglan(cfg):
                    yeni_sayisi += 1

        # 3. Motor'a kaydet
        if self._motor_ref and yeni_sayisi > 0:
            self.motor_kaydet()

        self._kesfedildi = True
        logger.info("[MCP] discover_mcp_tools: %d yeni sunucu, toplam %d",
                    yeni_sayisi, len(self._baglantilar))

    def motor_kaydet(self):
        """Tum MCP tool'larini motora kaydet.

        ReYMeN uyumlu isimlendirme: mcp_{sunucu}_{arac}
        """
        if not self._motor_ref:
            return
        motor = self._motor_ref
        if not hasattr(motor, "_plugin_arac_kaydet"):
            return

        for sunucu_ad, baglanti in self._baglantilar.items():
            for arac in baglanti.araclar:
                # mcp_{sunucu}_{arac} — ReYMeN standardi
                arac_adi = f"mcp_{sunucu_ad}_{arac['name']}"
                # Karakter temizligi (tire/nokta -> altcizgi)
                arac_adi = arac_adi.replace("-", "_").replace(".", "_").upper()

                # Closure ile dogru referans yakala
                def _fn(sun=sunucu_ad, ar=arac["name"], **kw):
                    return self.arac_cagir(sun, ar, kw)

                try:
                    motor._plugin_arac_kaydet(
                        arac_adi,
                        _fn,
                        arac.get("description", f"MCP: {sunucu_ad}/{arac['name']}"),
                    )
                except Exception as e:
                    logger.error("[MCP] Motor kayit hatasi (%s): %s", arac_adi, e)

    def arac_cagir(self, sunucu: str, arac: str, parametreler: dict) -> str:
        """Bir MCP sunucusundaki araci cagir."""
        baglanti = self._baglantilar.get(sunucu)
        if not baglanti:
            return f"[MCP] '{sunucu}' sunucusu bagli degil"
        if not baglanti.bagli:
            return f"[MCP] '{sunucu}' baglantisi koptu"
        sonuc = baglanti.arac_cagir(arac, parametreler)
        if sonuc is None:
            return ""
        return str(sonuc)

    # ── Durum Raporu ──────────────────────────────────────────────────────

    def durum(self) -> dict[str, Any]:
        """Tum MCP sunucu durumlari."""
        return {
            ad: {
                "bagli": b.bagli,
                "tool_sayisi": len(b.araclar),
                "transport": b.config.transport,
                "tools": [a.get("name") for a in b.araclar],
            }
            for ad, b in self._baglantilar.items()
        }

    def durum_text(self) -> str:
        """Insan-okunabilir durum raporu."""
        durum = self.durum()
        if not durum:
            return "[MCP] Bagli sunucu yok"

        satirlar = ["[MCP Native Client] Bagli Sunucular:", "=" * 50]
        for ad, bilgi in durum.items():
            satirlar.append(
                f"  {ad} ({bilgi['transport']}): "
                f"{'🟢' if bilgi['bagli'] else '🔴'} "
                f"{bilgi['tool_sayisi']} tool"
            )
            for tool in bilgi["tools"]:
                satirlar.append(f"    - mcp_{ad}_{tool}")
        return "\n".join(satirlar)


# ── Singleton ──────────────────────────────────────────────────────────────

_NATIVE_MCP: Optional[NativeMCPClient] = None


def native_mcp() -> NativeMCPClient:
    """Singleton Native MCP Client erisimi."""
    global _NATIVE_MCP
    if _NATIVE_MCP is None:
        _NATIVE_MCP = NativeMCPClient()
    return _NATIVE_MCP


def discover_mcp_tools(motor_ref: Any = None):
    """ReYMeN-tarzi: baslangicta MCP araclarini otomatik kesfet.

    motor.py _plugin_moduller_yukle icinde cagrilmasi icin.
    """
    istemci = native_mcp()
    istemci.discover_mcp_tools(motor_ref)
    return istemci


def motor_kaydet(motor):
    """MCP tool'larini motora kaydet (plugin API uyumlulugu)."""
    native_mcp().motor_kaydet()


# ── CLI Test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    istemci = native_mcp()
    istemci.discover_mcp_tools()

    print(istemci.durum_text())

    if len(sys.argv) > 2:
        # kullanim: python native_mcp_client.py sunucu_adi arac_adi '{"param": "deger"}'
        sunucu = sys.argv[1]
        arac = sys.argv[2]
        params = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        sonuc = istemci.arac_cagir(sunucu, arac, params)
        print(f"\nSonuc: {sonuc}")
