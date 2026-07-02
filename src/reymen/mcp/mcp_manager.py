# -*- coding: utf-8 -*-
"""
reymen/mcp/mcp_manager.py — MCP (Model Context Protocol) Yöneticisi.

ReYMeN için built-in native MCP istemci.
MCP sunucularına bağlanır, tool'ları keşfeder ve çağırır.
Singleton: mcp_manager() ile erişilir.

Desteklenen transportlar:
  - stdio: alt süreç (subprocess)
  - http:  HTTP POST (JSON-RPC)
  - tcp:   TCP socket (JSON-RPC)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Varsayılan config yolu ────────────────────────────────────────
PROJE_KOK = Path(__file__).parent.parent.parent
CONFIG_YOLLARI = [
    PROJE_KOK / "config.yaml",
    PROJE_KOK / "reymen" / "config.yaml",
    PROJE_KOK / ".ReYMeN" / "config.yaml",
    PROJE_KOK / "reymen" / ".ReYMeN" / "mcp_client.json",
]

# pyyaml opsiyonel
try:
    import yaml
    YAML_OK = True
except ImportError:
    YAML_OK = False


# ═══════════════════════════════════════════════════════════════════
# Transport İstemcileri
# ═══════════════════════════════════════════════════════════════════

class _StdioTransport:
    """Stdio (subprocess) ile JSON-RPC."""

    @staticmethod
    def _coz_komut(komut: list[str]) -> list[str]:
        """Windows: npx gibi script'leri .cmd/.exe yoluna çöz."""
        if os.name == "nt" and komut:
            ilk = komut[0]
            tam = shutil.which(ilk)
            if tam and tam != ilk:
                komut = [tam] + komut[1:]
        return komut

    @staticmethod
    async def cagir(komut: list[str], istek: dict, timeout: int = 30) -> dict:
        komut = _StdioTransport._coz_komut(komut)
        loop = asyncio.get_event_loop()
        try:
            r = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    komut,
                    input=json.dumps(istek),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                ),
            )
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            hata = r.stderr[:300] if r.stderr else "Çıktı yok"
            return {"error": {"message": hata}}
        except subprocess.TimeoutExpired:
            return {"error": {"message": f"Zaman aşımı: {' '.join(komut)}"}}
        except json.JSONDecodeError as e:
            return {"error": {"message": f"JSON hatası: {e}"}}
        except Exception as e:
            return {"error": {"message": str(e)}}


class _HttpTransport:
    """HTTP POST ile JSON-RPC."""

    @staticmethod
    async def cagir(url: str, istek: dict, timeout: int = 15) -> dict:
        loop = asyncio.get_event_loop()
        try:
            data = json.dumps(istek).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            def _request():
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.loads(r.read().decode("utf-8"))

            return await loop.run_in_executor(None, _request)
        except urllib.error.HTTPError as e:
            return {"error": {"message": f"HTTP {e.code}: {e.reason}"}}
        except urllib.error.URLError as e:
            return {"error": {"message": f"URL: {e.reason}"}}
        except Exception as e:
            return {"error": {"message": str(e)}}


class _TcpTransport:
    """TCP socket ile JSON-RPC."""

    @staticmethod
    async def cagir(host: str, port: int, istek: dict, timeout: int = 10) -> dict:
        loop = asyncio.get_event_loop()

        def _tcp():
            try:
                with socket.create_connection((host, port), timeout=timeout) as sock:
                    sock.sendall(json.dumps(istek).encode("utf-8"))
                    data = sock.recv(65536)
                    return json.loads(data.decode("utf-8"))
            except socket.timeout:
                return {"error": {"message": f"TCP zaman aşımı: {host}:{port}"}}
            except Exception as e:
                return {"error": {"message": str(e)}}

        return await loop.run_in_executor(None, _tcp)


# ═══════════════════════════════════════════════════════════════════
# MCP Sunucu Bağlantısı
# ═══════════════════════════════════════════════════════════════════

class MCPServerBaglantisi:
    """Tek bir MCP sunucusuna bağlantı."""

    def __init__(self, ad: str, cfg: dict):
        self.ad = ad
        self.cfg = cfg
        self.transport = cfg.get("transport", "stdio")
        self._tools: list[dict] = []
        self._baglandi = False

    @property
    def baglandi(self) -> bool:
        return self._baglandi

    async def tools_kesfet(self) -> int:
        """tools/list çağır, tool'ları keşfet."""
        istek = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        sonuc = await self._gonder(istek)
        if "error" in sonuc:
            logger.warning("MCP [%s] keşif hatası: %s", self.ad, sonuc["error"])
            return 0
        self._tools = sonuc.get("result", {}).get("tools", [])
        self._baglandi = True
        return len(self._tools)

    async def tool_cagir(self, tool: str, args: Optional[dict] = None) -> dict:
        """tools/call çağır."""
        istek = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": tool, "arguments": args or {}},
        }
        sonuc = await self._gonder(istek)
        if "error" in sonuc:
            return {"durum": "hata", "hata": sonuc["error"].get("message", "?")}

        icerik = sonuc.get("result", {}).get("content", [])
        if isinstance(icerik, list):
            metin = "\n".join(
                c.get("text", "") for c in icerik if isinstance(c, dict) and "text" in c
            )
        else:
            metin = str(icerik)

        return {"durum": "basarili", "icerik": metin}

    def tool_listesi(self) -> list[dict]:
        """Keşfedilen tool'ları döndür."""
        return [
            {
                "sunucu": self.ad,
                "name": t.get("name", "?"),
                "description": t.get("description", ""),
                "inputSchema": t.get("inputSchema", {}),
            }
            for t in self._tools
        ]

    async def _gonder(self, istek: dict) -> dict:
        """Transport'a göre isteği yönlendir."""
        t = self.transport
        if t == "stdio":
            komut = self.cfg.get("command")
            if not komut:
                return {"error": {"message": "stdio için 'command' gerekli"}}
            return await _StdioTransport.cagir(komut, istek)
        elif t == "http":
            url = self.cfg.get("url")
            if not url:
                return {"error": {"message": "http için 'url' gerekli"}}
            return await _HttpTransport.cagir(url, istek)
        else:  # tcp
            host = self.cfg.get("host", "127.0.0.1")
            port = self.cfg.get("port", 9100)
            return await _TcpTransport.cagir(host, port, istek)


# ═══════════════════════════════════════════════════════════════════
# MCP Yöneticisi (Singleton)
# ═══════════════════════════════════════════════════════════════════

class MCPManager:
    """Tüm MCP sunucularını yönetir. Singleton."""

    def __init__(self):
        self._sunucular: dict[str, MCPServerBaglantisi] = {}
        self._basladi = False

    def _config_yukle(self) -> dict:
        """mcp_client.json veya config.yaml'dan mcp_servers anahtarını oku."""
        for yol in CONFIG_YOLLARI:
            if yol.exists():
                try:
                    if yol.suffix == ".json":
                        with open(yol, encoding="utf-8") as f:
                            cfg = json.load(f)
                        # JSON format: {"servers": {"ad": {...}}}
                        return cfg.get("servers", {})
                    else:
                        if not YAML_OK:
                            logger.warning("PyYAML yok, %s yüklenemedi", yol)
                            continue
                        with open(yol) as f:
                            cfg = yaml.safe_load(f) or {}
                        return cfg.get("mcp_servers", {})
                except Exception as e:
                    logger.debug("Config yükleme hatası %s: %s", yol, e)
        logger.info("MCP: config dosyası bulunamadı")
        return {}

    async def baslat(self) -> int:
        """Tüm MCP sunucularını başlat, tool'ları keşfet.

        Returns:
            Toplam keşfedilen tool sayısı.
        """
        servers_config = self._config_yukle()
        if not servers_config:
            logger.info("MCP: config.yaml'da mcp_servers tanımlı değil")
            self._basladi = True
            return 0

        toplam = 0
        for ad, cfg in servers_config.items():
            # Eski format uyumlulugu: command (str) + args (list) → command (list)
            if isinstance(cfg.get("command"), str) and "args" in cfg:
                cfg["command"] = [cfg["command"]] + cfg.get("args", [])
                cfg.pop("args", None)
            cfg.setdefault("transport", "stdio")

            baglanti = MCPServerBaglantisi(ad, cfg)
            self._sunucular[ad] = baglanti
            try:
                sayi = await baglanti.tools_kesfet()
                logger.info(
                    "MCP [%s]: %s tool keşfedildi (%s)",
                    ad, sayi, cfg.get("transport"),
                )
                toplam += sayi
            except Exception as e:
                logger.warning("MCP [%s] başlatılamadı: %s", ad, e)

        self._basladi = True
        logger.info("MCP: %s sunucu, %s tool", len(self._sunucular), toplam)
        return toplam

    async def cagir(
        self, sunucu: str, arac: str, args: Optional[dict] = None
    ) -> dict:
        """Bir MCP sunucusunda tool çağır.

        Args:
            sunucu: Sunucu adı
            arac: Tool adı
            args: Parametreler

        Returns:
            {"durum": "basarili", "icerik": "..."} veya {"durum": "hata", "hata": "..."}
        """
        if not self._basladi:
            await self.baslat()

        baglanti = self._sunucular.get(sunucu)
        if not baglanti:
            mevcut = ", ".join(self._sunucular.keys()) or "(yok)"
            return {
                "durum": "hata",
                "hata": f"'{sunucu}' bulunamadı. Mevcut: {mevcut}",
            }

        return await baglanti.tool_cagir(arac, args)

    def tum_araclari_getir(self) -> list[dict]:
        """Tüm sunuculardaki tool'ları döndür."""
        tools = []
        for baglanti in self._sunucular.values():
            tools.extend(baglanti.tool_listesi())
        return tools

    def sunucu_listesi(self) -> list[str]:
        """Kayıtlı sunucu adlarını döndür."""
        return list(self._sunucular.keys())

    def ekle(self, ad: str, cfg: dict) -> MCPServerBaglantisi:
        """Elle MCP sunucusu ekle (çalışma zamanında)."""
        cfg.setdefault("transport", "stdio")
        baglanti = MCPServerBaglantisi(ad, cfg)
        self._sunucular[ad] = baglanti
        return baglanti

    def kaldir(self, ad: str) -> bool:
        """MCP sunucusunu kaldır."""
        if ad in self._sunucular:
            del self._sunucular[ad]
            return True
        return False


# ── Singleton erişimcisi ─────────────────────────────────────────
_mcp_manager_instance: Optional[MCPManager] = None


def mcp_manager() -> MCPManager:
    global _mcp_manager_instance
    if _mcp_manager_instance is None:
        _mcp_manager_instance = MCPManager()
    return _mcp_manager_instance
