"""📋 WebSocket ile canlı log akışı."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# WebSocket bağlantıları (basit in-memory)
_log_aboneler: list[Callable] = []
_log_kuyruk: asyncio.Queue[str] = asyncio.Queue(maxsize=500)
_log_tail: list[str] = []  # Son 200 satır (yeni bağlananlara gönderilir)


class LogStreamer:
    """Log dosyasını izler ve WebSocket abonelerine iletir."""

    def __init__(self, log_dosyasi: Path, max_tail: int = 200) -> None:
        self.log_dosyasi = log_dosyasi
        self.max_tail = max_tail
        self._son_boyut: int = 0
        self._basladi: bool = False

    async def basla(self) -> None:
        """Log dosyasını izlemeye başla."""
        if self._basladi:
            return
        self._basladi = True

        if not self.log_dosyasi.exists():
            logger.info("Log dosyasi yok, olusturuluyor: %s", self.log_dosyasi)
            self.log_dosyasi.parent.mkdir(parents=True, exist_ok=True)
            self.log_dosyasi.touch()

        # Mevcut tail'i yükle
        try:
            satirlar = self.log_dosyasi.read_text(encoding="utf-8", errors="replace").splitlines()
            self._son_boyut = len("".join(satirlar))
            self._log_tail = satirlar[-self.max_tail:]
        except Exception:
            self._son_boyut = 0
            self._log_tail = []

        logger.info("LogStreamer baslatildi: %s", self.log_dosyasi)

    async def tara(self) -> None:
        """Log dosyasını tara ve yeni satırları kuyruğa ekle."""
        try:
            suanki = self.log_dosyasi.stat().st_size
            if suanki <= self._son_boyut:
                return

            with open(str(self.log_dosyasi), "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._son_boyut)
                yeni_satirlar = f.read()

            if not yeni_satirlar:
                return

            self._son_boyut = suanki

            # Tail güncelle
            for satir in yeni_satirlar.splitlines():
                self._log_tail.append(satir)
                await _log_kuyruk.put(satir)

            self._log_tail = self._log_tail[-self.max_tail:]

        except Exception as e:
            logger.debug("Log tarama hatasi (normal): %s", e)

    def tail(self, n: int = 50) -> list[str]:
        """Son N satırı döndür."""
        return self._log_tail[-n:]

    @property
    def son_satir(self) -> str:
        return self._log_tail[-1] if self._log_tail else "(bos)"


# Abone yönetimi

def abone_ekle(callback: Callable) -> None:
    _log_aboneler.append(callback)


def abone_cikar(callback: Callable) -> None:
    if callback in _log_aboneler:
        _log_aboneler.remove(callback)


async def log_kuyrugu_oku() -> str:
    """Log kuyruğundan bir satır al."""
    return await _log_kuyruk.get()
