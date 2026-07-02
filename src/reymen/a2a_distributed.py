# -*- coding: utf-8 -*-
"""🌐 Dağıtık A2A Konfigürasyonu — uzak node'ları tanımla + otomatik bağlan.

Bu modül, A2A transport katmanına konfigürasyon dosyası üzerinden
uzak node tanımlama ve otomatik bağlanma özelliği ekler.

Kullanim:
    # .ReYMeN/a2a_nodes.json
    # {
    #   "nodes": [
    #     {"name": "sunucu1", "url": "http://192.168.1.100:9100", "agent_id": "reymen_1"},
    #     {"name": "sunucu2", "url": "http://10.0.0.50:9100", "agent_id": "reymen_2"}
    #   ]
    # }

    from reymen.a2a_distributed import A2ADistributed
    dist = A2ADistributed()
    dist.oyle_gor()  # config'den oku + baglan
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJE_KOK = Path(__file__).resolve().parent
A2A_CONFIG_PATH = PROJE_KOK.parent / ".ReYMeN" / "a2a_nodes.json"

# ---------------------------------------------------------------------------
# Dağıtık A2A Yöneticisi
# ---------------------------------------------------------------------------

class A2ADistributed:
    """Dağıtık A2A node yöneticisi — config dosyası + heartbeat + otomatik bağlan.

    Her N saniyede bir uzak node'ların health'ini kontrol eder,
    kopan bağlantıları yeniden kurar.
    """

    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path) if config_path else A2A_CONFIG_PATH
        self._nodes: dict[str, Any] = {}  # name -> {url, agent_id, remote}
        self._heartbeat_thread: threading.Thread | None = None
        self._calisiyor = False

    def oku_config(self) -> list[dict]:
        """A2A node config dosyasını oku.

        Format:
            {
              "nodes": [
                {"name": "...", "url": "...", "agent_id": "..."},
                ...
              ],
              "heartbeat_interval": 30
            }
        """
        if not self.config_path.exists():
            logger.info("[A2A-DIST] Config yok: %s", self.config_path)
            return []
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            return data.get("nodes", [])
        except Exception as e:
            logger.warning("[A2A-DIST] Config okuma hatasi: %s", e)
            return []

    def baglan(self, node: dict) -> str:
        """Tek bir uzak node'a bağlan."""
        from reymen.a2a_transport import A2ARemote

        name = node.get("name", "unknown")
        url = node.get("url", "")
        agent_id = node.get("agent_id", "reymen_dist")

        if not url:
            return f"[A2A-DIST] {name}: url eksik"

        remote = A2ARemote(url, agent_id)
        sonuc = remote.baglan()

        if "basarili" in sonuc:
            self._nodes[name] = {
                "url": url,
                "agent_id": agent_id,
                "remote": remote,
                "connected": time.time(),
            }
        return f"[A2A-DIST] {name}: {sonuc}"

    def bagli_mi(self, name: str) -> bool:
        """Belirli bir node'a bağlı mı?"""
        node = self._nodes.get(name)
        if not node:
            return False
        try:
            remote = node.get("remote")
            if remote:
                s = remote._get_session()
                r = s.get(f"{remote.base_url}/api/a2a/health", timeout=3)
                return r.status_code == 200
        except Exception:
            return False
        return False

    def oyle_gor(self) -> list[str]:
        """Config'deki tüm node'lara bağlan."""
        sonuclar = []
        nodes = self.oku_config()
        if not nodes:
            return ["[A2A-DIST] Baglanilacak node yok (config bos)"]

        for node in nodes:
            sonuc = self.baglan(node)
            sonuclar.append(sonuc)
            logger.info(sonuc)

        # Heartbeat başlat
        self._heartbeat_baslat()

        return sonuclar

    def _heartbeat_baslat(self, interval: int = 30) -> None:
        """Periyodik olarak uzak node'lari kontrol et."""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return

        self._calisiyor = True

        def _loop():
            while self._calisiyor:
                time.sleep(interval)
                for name, node in list(self._nodes.items()):
                    if not self.bagli_mi(name):
                        logger.warning("[A2A-DIST] %s baglantisi koptu, yeniden baglaniliyor...", name)
                        self.baglan(node)

        self._heartbeat_thread = threading.Thread(target=_loop, daemon=True)
        self._heartbeat_thread.start()
        logger.info("[A2A-DIST] Heartbeat baslatildi (%ds)", interval)

    def durdur(self) -> None:
        """Tüm bağlantıları kapat."""
        self._calisiyor = False
        for name, node in self._nodes.items():
            remote = node.get("remote")
            if remote:
                try:
                    remote.kapat()
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )
        self._nodes.clear()
        logger.info("[A2A-DIST] Tüm baglantilar kapatildi")

    def durum(self) -> str:
        """Bağlı node'ların durumu."""
        if not self._nodes:
            return "  A2A-DIST: Bagli node yok"
        satirlar = [f"  A2A-DIST: {len(self._nodes)} node"]
        for name, node in self._nodes.items():
            durum = "✅" if self.bagli_mi(name) else "❌"
            satirlar.append(f"    {durum} {name} -> {node['url']} ({node['agent_id']})")
        return "\n".join(satirlar)

    def mesaj_gonder(self, receiver: str, content: str) -> list[str]:
        """Tüm bağlı node'lar üzerinden mesaj gönder."""
        sonuclar = []
        for name, node in self._nodes.items():
            remote = node.get("remote")
            if remote:
                s = remote.send(receiver, content)
                sonuclar.append(f"  {name}: {s}")
        return sonuclar


# ---------------------------------------------------------------------------
# Motor Entegrasyonu
# ---------------------------------------------------------------------------

_A2A_DIST = None


def motor_kaydet(motor) -> None:
    """Motor'a dağıtık A2A araçlarını kaydet."""
    motor._plugin_arac_kaydet(
        "A2A_DIST_BASLAT", _dist_baslat,
        "Config dosyasindaki tum uzak A2A node'larina baglan. "
        "Parametre yok. Config: .ReYMeN/a2a_nodes.json"
    )
    motor._plugin_arac_kaydet(
        "A2A_DIST_DURUM", _dist_durum,
        "Bagli uzak A2A node'larinin durumunu goster."
    )
    motor._plugin_arac_kaydet(
        "A2A_DIST_GONDER", _dist_gonder,
        "Tum bagli node'lara mesaj gonder. Parametre: receiver, content"
    )
    logger.info("[A2A-DIST] Motor'a 3 arac kaydedildi")


def _dist_baslat(**kw) -> str:
    """Dağıtık A2A'yı başlat (config'deki node'lara bağlan)."""
    global _A2A_DIST
    _A2A_DIST = A2ADistributed()
    sonuclar = _A2A_DIST.oyle_gor()
    return "\n".join(sonuclar)


def _dist_durum(**kw) -> str:
    """Dağıtık A2A durumu."""
    if _A2A_DIST:
        return _A2A_DIST.durum()
    return "  A2A-DIST: Baslatilmadi (A2A_DIST_BASLAT ile baslat)"


def _dist_gonder(**kw) -> str:
    """Tüm bağlı node'lara mesaj gönder."""
    args = kw.get("args", [])
    if len(args) < 2:
        return "[A2A-DIST] Kullanim: A2A_DIST_GONDER <receiver> <content>"
    if not _A2A_DIST:
        return "[A2A-DIST] Once A2A_DIST_BASLAT ile baslat"
    sonuclar = _A2A_DIST.mesaj_gonder(args[0], args[1])
    return "\n".join(sonuclar)
