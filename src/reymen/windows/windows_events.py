# -*- coding: utf-8 -*-
"""
windows_events.py — Windows Otomasyon Event Sistemi

Modüller arası haberleşme için merkezi event bus.
Her modül olay bildirir, diğer modüller dinler.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class WindowsEventBus:
    """Thread-safe event bus for Windows automation modules."""

    def __init__(self):
        self._dinleyiciler = {}
        self._lock = threading.Lock()
        self._gecmis = []
        self._maks_gecmis = 100

    def dinle(self, olay_tipi, fonksiyon, sirano=0):
        """Bir olay tipini dinlemeye basla."""
        with self._lock:
            self._dinleyiciler.setdefault(olay_tipi, [])
            self._dinleyiciler[olay_tipi].append((sirano, fonksiyon))
            self._dinleyiciler[olay_tipi].sort(key=lambda x: x[0])

    def dinleme_kes(self, olay_tipi, fonksiyon):
        """Dinlemeyi durdur."""
        with self._lock:
            if olay_tipi in self._dinleyiciler:
                self._dinleyiciler[olay_tipi] = [
                    (s, f) for s, f in self._dinleyiciler[olay_tipi]
                    if f is not fonksiyon
                ]

    def yayinla(self, olay_tipi, veri=None):
        """Bir olay yayinla, tum dinleyicilere haber ver."""
        if veri is None:
            veri = {}

        # Gecmise ekle
        with self._lock:
            self._gecmis.append({
                "tip": olay_tipi, "veri": veri, "zaman": time.monotonic()
            })
            if len(self._gecmis) > self._maks_gecmis:
                self._gecmis = self._gecmis[-self._maks_gecmis:]

        # Dinleyicileri cagir (lock disinda, deadlock riski yok)
        with self._lock:
            dinleyiciler = list(self._dinleyiciler.get(olay_tipi, []))

        for _, fonk in dinleyiciler:
            try:
                fonk(veri)
            except Exception as e:
                logger.error("[EventBus] %s dinleyicisi hata: %s", olay_tipi, e)

    def son_olaylar(self, limit=10):
        """Son N olayi goster."""
        with self._lock:
            return list(self._gecmis[-limit:])

    def temizle(self):
        with self._lock:
            self._gecmis.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

_event_bus = None
_event_bus_lock = threading.Lock()


def event_bus_al():
    global _event_bus
    if _event_bus is None:
        with _event_bus_lock:
            if _event_bus is None:
                _event_bus = WindowsEventBus()
    return _event_bus


# ── Olay tipleri ──────────────────────────────────────────────────────────────

OLAY_HATA = "hata"
OLAY_NISAN = "nisan"
OLAY_TOR_HATA = "tor_hata"
OLAY_COKUS = "cokus"
OLAY_TOR_BASARILI = "tor_basarili"
OLAY_COZUM_UYGULANDI = "cozum_uygulandi"
OLAY_SISTEM_UYARI = "sistem_uyari"
