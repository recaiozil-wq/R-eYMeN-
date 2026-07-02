# -*- coding: utf-8 -*-
"""mcp_tool.py — MCP (Model Context Protocol) İstemci Aracı.

MCP sunucularına bağlanır ve araçlarını ReYMeN'e açar.
JSON-RPC 2.0 over stdio veya HTTP.
"""

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional
import logging
logger = logging.getLogger(__name__)

MCP_KONFIG_YOLU = Path(__file__).parent / ".ReYMeN" / "mcp_servers.json"


class MCPSunucusu:
    """Tek bir MCP sunucusu bağlantısı (stdio tabanlı)."""

    def __init__(self, ad: str, komut: list[str], calisma_dizini: str = ""):
        self.ad             = ad
        self.komut          = komut
        self.calisma_dizini = calisma_dizini
        self._proses: Optional[subprocess.Popen] = None
        self._istek_id      = 0
        self._kilit         = threading.Lock()
        self._araclar: list[dict] = []

    def baslat(self) -> bool:
        try:
            self._proses = subprocess.Popen(
                self.komut,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.calisma_dizini or None,
            )
            # İlk initialize mesajı
            self._json_rpc("initialize", {
                "protocolVersion": "0.1.0",
                "capabilities":    {},
                "clientInfo":      {"name": "ReYMeN", "version": "1.0"},
            })
            # Araç listesini al
            yanit = self._json_rpc("tools/list", {})
            self._araclar = yanit.get("result", {}).get("tools", [])
            return True
        except Exception:
            return False

    def _json_rpc(self, metod: str, params: dict) -> dict:
        with self._kilit:
            self._istek_id += 1
            istek = json.dumps({
                "jsonrpc": "2.0",
                "id":      self._istek_id,
                "method":  metod,
                "params":  params,
            }) + "\n"
            try:
                self._proses.stdin.write(istek)
                self._proses.stdin.flush()
                satir = self._proses.stdout.readline()
                return json.loads(satir) if satir else {}
            except Exception:
                return {}

    def arac_cagir(self, arac_adi: str, parametreler: dict) -> Any:
        yanit = self._json_rpc("tools/call", {
            "name":      arac_adi,
            "arguments": parametreler,
        })
        sonuc = yanit.get("result", {})
        icerik = sonuc.get("content", [])
        if icerik and isinstance(icerik, list):
            return " ".join(c.get("text", "") for c in icerik if c.get("type") == "text")
        return str(sonuc)

    def araclar(self) -> list[dict]:
        return self._araclar

    def durdur(self):
        if self._proses and self._proses.poll() is None:
            self._proses.terminate()


class MCPIstemci:
    """Çoklu MCP sunucusu yöneticisi."""

    def __init__(self):
        self._sunucular: dict[str, MCPSunucusu] = {}
        self._konfig_yukle()

    def _konfig_yukle(self):
        if not MCP_KONFIG_YOLU.exists():
            return
        try:
            konfig = json.loads(MCP_KONFIG_YOLU.read_text(encoding="utf-8"))
            for ad, ayar in konfig.get("servers", {}).items():
                komut = ayar.get("command", [])
                if isinstance(komut, str):
                    komut = komut.split()
                self.sunucu_ekle(ad, komut, ayar.get("cwd", ""))
        except Exception as _mcp_tool_e106:
            print(f"[UYARI] mcp_tool.py:107 - {_mcp_tool_e106}")

    def sunucu_ekle(self, ad: str, komut: list[str], cwd: str = "") -> bool:
        s = MCPSunucusu(ad, komut, cwd)
        if s.baslat():
            self._sunucular[ad] = s
            return True
        return False

    def sunucu_kaldir(self, ad: str):
        if ad in self._sunucular:
            self._sunucular[ad].durdur()
            del self._sunucular[ad]

    def arac_cagir(self, sunucu: str, arac: str, params: dict) -> str:
        if sunucu not in self._sunucular:
            return f"[MCP]: '{sunucu}' sunucusu bulunamadı."
        return str(self._sunucular[sunucu].arac_cagir(arac, params))

    def tum_araclar(self) -> dict[str, list[dict]]:
        return {ad: s.araclar() for ad, s in self._sunucular.items()}

    def motor_kaydet(self, motor):
        """Tüm MCP araçlarını motora kaydet."""
        for sunucu_ad, araclar in self.tum_araclar().items():
            for arac in araclar:
                arac_adi = f"MCP_{sunucu_ad.upper()}_{arac['name'].upper()}"
                params   = arac.get("inputSchema", {}).get("properties", {})

                def _fn(sun=sunucu_ad, ar=arac["name"], **kw):
                    return self.arac_cagir(sun, ar, kw)

                if hasattr(motor, "_plugin_arac_kaydet"):
                    motor._plugin_arac_kaydet(
                        arac_adi, _fn,
                        arac.get("description", f"MCP: {sunucu_ad}/{arac['name']}"),
                    )

    def durum(self) -> dict:
        return {
            ad: {
                "arac_sayisi": len(s.araclar()),
                "aktif":       s._proses is not None and s._proses.poll() is None,
            }
            for ad, s in self._sunucular.items()
        }


_ISTEMCI: Optional[MCPIstemci] = None


def mcp_istemci() -> MCPIstemci:
    global _ISTEMCI
    if _ISTEMCI is None:
        _ISTEMCI = MCPIstemci()
    return _ISTEMCI


if __name__ == "__main__":
    istemci = MCPIstemci()
    print(f"Sunucular: {istemci.durum()}")
    print(f"Araçlar: {istemci.tum_araclar()}")
