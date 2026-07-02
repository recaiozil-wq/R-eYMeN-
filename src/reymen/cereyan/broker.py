# -*- coding: utf-8 -*-
"""
broker.py — MessageBroker: queue.Queue tabanlı, thread-safe mesajlaşma katmanı.

Mevcut threading yapısına %90 uyumlu:
  - ThreadPoolExecutor (8 worker) → consumer pool
  - threading.Thread (daemon=True) → background consumer
  - threading.local() → correlation ID tracing
  - asyncio GEREKSİZ, ThreadPoolExecutor yeterli

Kullanım:
    broker = MessageBroker(max_workers=4)
    broker.abone_ol(MesajTipi.HATA, hata_handler)
    broker.baslat()  # background thread'de başlar
    broker.yayinla(Mesaj(MesajTipi.HATA, {"hata": "test"}))
    broker.durdur()
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ── Mesaj Tipleri ──────────────────────────────────────────────────────────────

class MesajTipi(Enum):
    """Sistemdeki tüm mesaj tipleri. Her tip bir consumer queue'suna karşılık gelir."""
    # Çözüm döngüsü
    HATA       = auto()  # hata_cozucu'ya: hata yakalandı, çözüm üret
    COZUM_ARA  = auto()  # ogrenme'ye: çözüm hafızasında ara
    COZUM_BULUNDU = auto()  # orchestrator'a: çözüm bulundu, uygula
    COZUM_KAYDET = auto()  # ogrenme'ye: başarılı çözümü kaydet
    BECERI_KRISTAL = auto()  # closed_learning_loop'a: skill kartı oluştur

    # Workflow pipeline
    GOREV_BASLAT   = auto()  # motor'a: yeni görev başlat
    GOREV_PLANLA   = auto()  # planlayıcıya: görevi alt adımlara böl
    GOREV_DOGRULA  = auto()  # doğrulayıcıya: ön koşulları kontrol et
    GOREV_KOD      = auto()  # kodlayıcıya: Python script'i üret
    GOREV_TEST     = auto()  # testçiye: script'i çalıştır/doğrula
    GOREV_INCELE   = auto()  # inceleyiciye: kodu gözden geçir
    GOREV_KAYDET   = auto()  # kaydediciye: .py dosyasına yaz
    GOREV_BASARILI = auto()  # orchestrator'a: görev tamam
    GOREV_HATA     = auto()  # orchestrator'a: görev başarısız

    # Tool çağrıları
    TOOL_CALL      = auto()  # conversation_loop'a: tool çağrısı hazır
    TOOL_SONUC     = auto()  # conversation_loop'a: tool sonucu döndü

    # Kontrol
    DURDUR = auto()  # broker'ı kapat


@dataclass
class Mesaj:
    """Thread-safe mesaj veri yapısı."""
    tip: MesajTipi
    veri: dict = field(default_factory=dict)
    kaynak: str = ""
    correlation_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        return f"Mesaj({self.tip.name}, corr={self.correlation_id[:8]}, kaynak={self.kaynak})"


# ── Mesaj Kuyruğu (thread-safe) ───────────────────────────────────────────────

class MesajKuyrugu:
    """Her consumer için ayrı queue + abone yönetimi."""

    def __init__(self, tip: MesajTipi):
        self.tip = tip
        self.kuyruk: queue.Queue[Mesaj] = queue.Queue()
        self.aboneler: list[Callable[[Mesaj], None]] = []

    def abone_ekle(self, callback: Callable[[Mesaj], None]):
        self.aboneler.append(callback)

    def mesaj_at(self, mesaj: Mesaj):
        self.kuyruk.put_nowait(mesaj)

    def mesaj_al(self, timeout: float = 1.0) -> Optional[Mesaj]:
        try:
            return self.kuyruk.get(timeout=timeout)
        except queue.Empty:
            return None

    def abone_sayisi(self) -> int:
        return len(self.aboneler)


# ── Message Broker ─────────────────────────────────────────────────────────────

class MessageBroker:
    """
    Merkezi mesajlaşma katmanı.
    
    - Her MesajTipi için ayrı queue
    - ThreadPoolExecutor consumer pool
    - Abonelik bazlı routing
    - Otomatik correlation ID
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._kuyruklar: dict[MesajTipi, MesajKuyrugu] = {}
        self._running = False
        self._threads: list[threading.Thread] = []
        self._executor: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Tüm mesaj tipleri için queue oluştur
        for tip in MesajTipi:
            self._kuyruklar[tip] = MesajKuyrugu(tip)

    # ── Abone Yönetimi ─────────────────────────────────────────────────────

    def abone_ol(self, tip: MesajTipi, callback: Callable[[Mesaj], None]) -> None:
        """Bir mesaj tipine abone ol. Callback consumer thread'de çalışır."""
        kuyruk = self._kuyruklar.get(tip)
        if kuyruk:
            kuyruk.abone_ekle(callback)

    def abone_ol_liste(self, abonelikler: list[tuple[MesajTipi, Callable]]) -> None:
        """Toplu abonelik."""
        for tip, cb in abonelikler:
            self.abone_ol(tip, cb)

    # ── Mesaj Gönderme ─────────────────────────────────────────────────────

    def yayinla(self, mesaj: Mesaj) -> None:
        """Bir mesajı ilgili queue'suna gönder."""
        if not self._running:
            logger.warning("[Broker] Çalışmıyor, mesaj atıldı: %s", mesaj)
            return
        kuyruk = self._kuyruklar.get(mesaj.tip)
        if kuyruk:
            mesaj.correlation_id = mesaj.correlation_id or uuid.uuid4().hex[:12]
            kuyruk.mesaj_at(mesaj)

    def yayinla_basit(self, tip: MesajTipi, veri: dict, kaynak: str = "") -> None:
        """Hızlı mesaj gönderme (Mesaj nesnesi oluşturmadan)."""
        mesaj = Mesaj(tip=tip, veri=veri, kaynak=kaynak)
        self.yayinla(mesaj)

    # ── Consumer Thread ────────────────────────────────────────────────────

    def _consumer_loop(self, kuyruk: MesajKuyrugu) -> None:
        """Tek bir queue için consumer thread döngüsü."""
        thread_name = threading.current_thread().name
        logger.debug("[Broker] Consumer başladı: %s <- %s", thread_name, kuyruk.tip.name)

        while self._running:
            mesaj = kuyruk.mesaj_al(timeout=0.5)
            if mesaj is None:
                continue
            if mesaj.tip == MesajTipi.DURDUR:
                break

            # Abonelere dağıt
            for abone in kuyruk.aboneler:
                try:
                    abone(mesaj)
                except Exception as e:
                    logger.error("[Broker] Abone hatası (%s): %s", kuyruk.tip.name, e)

        logger.debug("[Broker] Consumer durdu: %s", thread_name)

    # ── Başlat / Durdur ────────────────────────────────────────────────────

    def baslat(self) -> None:
        """
        Her mesaj tipi için bir consumer thread başlatır.
        Thread'ler daemon=True olduğu için ana thread bitince otomatik kapanır.
        """
        if self._running:
            return
        self._running = True

        for tip, kuyruk in self._kuyruklar.items():
            if kuyruk.abone_sayisi() > 0 or tip in (MesajTipi.DURDUR,):
                t = threading.Thread(
                    target=self._consumer_loop,
                    args=(kuyruk,),
                    name=f"broker-{tip.name.lower()}",
                    daemon=True,
                )
                t.start()
                self._threads.append(t)

        logger.info("[Broker] %d consumer thread başlatıldı", len(self._threads))

    def durdur(self) -> None:
        """Tüm consumer thread'leri durdur."""
        self._running = False
        # DURDUR mesajı göndererek bekleyen thread'leri uyandır
        for kuyruk in self._kuyruklar.values():
            kuyruk.mesaj_at(Mesaj(MesajTipi.DURDUR, kaynak="broker"))
        logger.info("[Broker] Durduruldu")

    # ── Durum ──────────────────────────────────────────────────────────────

    def durum(self) -> dict:
        """Broker durum raporu."""
        return {
            "running": self._running,
            "threads": len(self._threads),
            "kuyruklar": {
                tip.name: {
                    "abone": kuyruk.abone_sayisi(),
                    "boyut": kuyruk.kuyruk.qsize(),
                }
                for tip, kuyruk in self._kuyruklar.items()
                if kuyruk.abone_sayisi() > 0 or kuyruk.kuyruk.qsize() > 0
            },
        }


# ── Yardımcı Fonksiyonlar ─────────────────────────────────────────────────────

def mesaj_gonder(broker: Optional[MessageBroker], tip: MesajTipi, veri: dict, kaynak: str = "") -> None:
    """Broker varsa mesaj gönder, yoksa sessiz geç."""
    if broker:
        broker.yayinla(Mesaj(tip=tip, veri=veri, kaynak=kaynak or __name__))


# ── Singleton ──────────────────────────────────────────────────────────────────

_broker_instance: Optional[MessageBroker] = None
_broker_lock = threading.Lock()


def get_broker(max_workers: int = 4) -> MessageBroker:
    """Tekil broker instance'ı (thread-safe)."""
    global _broker_instance
    if _broker_instance is None:
        with _broker_lock:
            if _broker_instance is None:
                _broker_instance = MessageBroker(max_workers=max_workers)
    return _broker_instance
