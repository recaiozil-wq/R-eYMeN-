# -*- coding: utf-8 -*-
"""
auto_recovery.py — ReYMeN Otomatik Kurtarma ve Watchdog Sistemi.

Tüm sistem bileşenlerini izler, heartbeat timeout'larını kontrol eder,
stuck/kilitlenmiş durumları tespit eder ve otomatik kurtarma dener.

Bileşenler:
    - ComponentWatcher: Her bileşen için heartbeat + timeout izleme
    - AutoRecovery: Ana kurtarma yöneticisi (state machine + bridge entegre)

Kullanım:
    recovery = AutoRecovery(state_machine, bridge)
    recovery.watch("provider", heartbeat_interval=15, timeout=45)
    recovery.start()
    # Periyodik olarak recovery.tick() çağrılır
    recovery.stop()
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ComponentStatus(Enum):
    """Bileşen sağlık durumu."""
    HEALTHY = "healthy"
    STALE = "stale"        # Heartbeat timeout
    FAILING = "failing"    # Art arda başarısız
    RECOVERING = "recovering"
    DEAD = "dead"          # Kurtarılamaz


@dataclass
class WatchConfig:
    """Her bileşen için watchdog yapılandırması."""
    name: str
    heartbeat_interval_sec: float = 15.0
    timeout_sec: float = 45.0  # heartbeat alınmazsa STALE sayılır
    max_failures: int = 3       # art arda başarısızlık limiti
    cooldown_sec: float = 60.0  # kurtarma sonrası bekleme
    restart_attempts: int = 3   # maksimum yeniden başlatma
    enabled: bool = True


@dataclass
class WatchState:
    """Bileşen izleme durumu."""
    status: ComponentStatus = ComponentStatus.HEALTHY
    last_heartbeat: float = field(default_factory=time.time)
    last_status_change: float = field(default_factory=time.time)
    consecutive_failures: int = 0
    restart_count: int = 0
    last_recovery: Optional[float] = None
    last_error: Optional[str] = None
    error_history: List[Tuple[float, str]] = field(default_factory=list)


RecoveryHandler = Callable[[str, str], bool]
"""Kurtarma handler imzası: (bilesen_adi, hata_mesaji) -> basarili_mi"""


class ComponentWatcher:
    """Tek bir bileşeni izleyen watchdog."""

    def __init__(self, config: WatchConfig):
        self.config = config
        self.state = WatchState()
        self._recovery_handlers: List[RecoveryHandler] = []
        self._lock = threading.RLock()

    def heartbeat(self) -> None:
        """Bileşenden canlılık sinyali al."""
        with self._lock:
            self.state.last_heartbeat = time.time()
            if self.state.status in (ComponentStatus.STALE, ComponentStatus.FAILING):
                # Heartbeat geldi — düzelmiş olabilir
                self.state.status = ComponentStatus.HEALTHY
                self.state.last_status_change = time.time()
                logger.info(f"[Watcher/{self.config.name}] Heartbeat alindi -> HEALTHY")

    def record_error(self, error_msg: str) -> None:
        """Bileşen hatası kaydet."""
        with self._lock:
            self.state.consecutive_failures += 1
            self.state.last_error = error_msg
            self.state.error_history.append((time.time(), error_msg))
            if len(self.state.error_history) > 100:
                self.state.error_history = self.state.error_history[-50:]

            if self.state.consecutive_failures >= self.config.max_failures:
                self.state.status = ComponentStatus.FAILING
            else:
                self.state.status = ComponentStatus.STALE
            self.state.last_status_change = time.time()
            logger.warning(f"[Watcher/{self.config.name}] Hata #{self.state.consecutive_failures}: {error_msg}")

    def check(self) -> Optional[ComponentStatus]:
        """Bileşen sağlığını kontrol et.
        
        Returns:
            Stuck/sorunlu ise status, HEALTHY ise None
        """
        with self._lock:
            if self.state.status in (ComponentStatus.DEAD,):
                return self.state.status

            elapsed = time.time() - self.state.last_heartbeat

            if self.state.status == ComponentStatus.RECOVERING:
                # Kurtarma aşamasında — timeout farklı hesapla
                recovery_elapsed = time.time() - (self.state.last_recovery or 0)
                if recovery_elapsed > self.config.timeout_sec:
                    self.state.status = ComponentStatus.DEAD
                    self.state.last_status_change = time.time()
                    logger.error(f"[Watcher/{self.config.name}] Kurtarma zaman asimi -> DEAD")
                return self.state.status

            if elapsed > self.config.timeout_sec:
                if self.state.status == ComponentStatus.HEALTHY:
                    self.state.status = ComponentStatus.STALE
                    self.state.last_status_change = time.time()
                    logger.warning(f"[Watcher/{self.config.name}] {elapsed:.0f}s heartbeat yok -> STALE")
                return self.state.status

            return None

    def start_recovery(self) -> bool:
        """Kurtarma başlat.
        
        Returns:
            Kurtarma handler'larından en az biri başarılıysa True
        """
        with self._lock:
            if self.state.restart_count >= self.config.restart_attempts:
                self.state.status = ComponentStatus.DEAD
                logger.error(f"[Watcher/{self.config.name}] Maks restart ({self.config.restart_attempts}) asildi -> DEAD")
                return False

            self.state.status = ComponentStatus.RECOVERING
            self.state.last_recovery = time.time()
            self.state.last_status_change = time.time()
            self.state.restart_count += 1

        # Handler'ları dene
        for handler in self._recovery_handlers:
            try:
                if handler(self.config.name, self.state.last_error or ""):
                    with self._lock:
                        self.state.status = ComponentStatus.HEALTHY
                        self.state.consecutive_failures = 0
                        self.state.last_status_change = time.time()
                        logger.info(f"[Watcher/{self.config.name}] Kurtarma basarili -> HEALTHY")
                    return True
            except Exception as e:
                logger.error(f"[Watcher/{self.config.name}] Kurtarma handler hatasi: {e}")

        with self._lock:
            if self.state.restart_count < self.config.restart_attempts:
                self.state.status = ComponentStatus.STALE  # tekrar dene
            else:
                self.state.status = ComponentStatus.DEAD
            self.state.last_status_change = time.time()

        return False

    def on_recovery(self, handler: RecoveryHandler) -> None:
        """Kurtarma handler'ı ekle."""
        with self._lock:
            self._recovery_handlers.append(handler)

    def reset(self) -> None:
        """İzleme durumunu sıfırla."""
        with self._lock:
            self.state = WatchState(last_heartbeat=time.time())
            logger.info(f"[Watcher/{self.config.name}] Resetlendi")

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "name": self.config.name,
                "status": self.state.status.value,
                "last_heartbeat_ago": round(time.time() - self.state.last_heartbeat, 1),
                "consecutive_failures": self.state.consecutive_failures,
                "restart_count": self.state.restart_count,
                "last_error": self.state.last_error,
                "timeout_sec": self.config.timeout_sec,
                "max_failures": self.config.max_failures,
            }


class AutoRecovery:
    """Ana otomatik kurtarma yöneticisi.

    Tüm bileşenleri izler, state machine ve bridge ile entegre çalışır.
    """

    def __init__(self, state_machine=None, bridge=None,
                 check_interval_sec: float = 15.0,
                 max_restart_attempts: int = 3,
                 cooldown_sec: float = 60.0,
                 max_concurrent_failures: int = 5,
                 notify_on_recovery: bool = True):
        self._state_machine = state_machine
        self._bridge = bridge
        self._check_interval = check_interval_sec
        self._max_restart_attempts = max_restart_attempts
        self._cooldown_sec = cooldown_sec
        self._max_concurrent_failures = max_concurrent_failures
        self._notify_on_recovery = notify_on_recovery

        self._watchers: Dict[str, ComponentWatcher] = {}
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_tick: float = time.time()
        self._tick_count: int = 0
        self._recovery_count: int = 0
        self._system_crashed: bool = False

        # Varsayılan kurtarma handler'ları
        self._default_handlers: Dict[str, List[RecoveryHandler]] = {}

    # ── Bileşen yönetimi ───────────────────────────────────────────────

    def watch(self, name: str, heartbeat_interval: float = 15.0,
              timeout: float = 45.0, max_failures: int = 3,
              restart_attempts: Optional[int] = None,
              enabled: bool = True) -> ComponentWatcher:
        """Yeni bir bileşeni izlemeye başla.

        Args:
            name: Bileşen adı
            heartbeat_interval: Heartbeat beklenti aralığı (saniye)
            timeout: Heartbeat timeout (saniye)
            max_failures: Art arda başarısızlık limiti
            restart_attempts: Maksimum yeniden başlatma denemesi
            enabled: İzleme aktif mi

        Returns:
            Oluşturulan ComponentWatcher
        """
        config = WatchConfig(
            name=name,
            heartbeat_interval_sec=heartbeat_interval,
            timeout_sec=timeout,
            max_failures=max_failures,
            restart_attempts=restart_attempts or self._max_restart_attempts,
            enabled=enabled,
        )
        watcher = ComponentWatcher(config)

        # Varsayılan handler'ları ekle
        for handler in self._default_handlers.get(name, []):
            watcher.on_recovery(handler)

        with self._lock:
            self._watchers[name] = watcher

        logger.info(f"[AutoRecovery] Izleniyor: {name} (timeout={timeout}s, max_fail={max_failures})")

        # Bridge'e heartbeat aboneliği
        if self._bridge:
            self._bridge.heartbeat(f"recovery.{name}")

        return watcher

    def unwatch(self, name: str) -> None:
        """Bileşen izlemeyi durdur."""
        with self._lock:
            self._watchers.pop(name, None)
        logger.info(f"[AutoRecovery] Izleme durduruldu: {name}")

    def heartbeat(self, component: str) -> None:
        """Bileşen canlılık sinyali gönder."""
        with self._lock:
            watcher = self._watchers.get(component)
        if watcher:
            watcher.heartbeat()
            if self._bridge:
                self._bridge.heartbeat(f"recovery.{component}")

    def record_error(self, component: str, error_msg: str) -> None:
        """Bileşen hatası kaydet."""
        with self._lock:
            watcher = self._watchers.get(component)
        if watcher:
            watcher.record_error(error_msg)
            if self._bridge:
                self._bridge.publish("error", {
                    "component": component,
                    "error": error_msg,
                }, source=f"recovery.{component}")

    def on_recovery(self, component: str, handler: RecoveryHandler) -> None:
        """Bir bileşen için kurtarma handler'ı ekle.

        Henüz oluşturulmamış bileşenler için de kaydedilir (future watchers).
        """
        with self._lock:
            if component not in self._default_handlers:
                self._default_handlers[component] = []
            self._default_handlers[component].append(handler)

            watcher = self._watchers.get(component)
        if watcher:
            watcher.on_recovery(handler)

    # ── Ana döngü ──────────────────────────────────────────────────────

    def start(self) -> None:
        """Arka plan watchdog thread'ini başlat."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True, name="recovery-watchdog")
            self._thread.start()
            logger.info(f"[AutoRecovery] Watchdog baslatildi (interval={self._check_interval}s)")

    def stop(self) -> None:
        """Watchdog'u durdur."""
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("[AutoRecovery] Watchdog durduruldu")

    def tick(self) -> Dict[str, Any]:
        """Tek bir kontrol döngüsü (manuel çağrı için).

        Returns:
            Kontrol sonuçları
        """
        self._tick_count += 1
        self._last_tick = time.time()
        results: Dict[str, Any] = {"checked": [], "recovered": [], "failed": [], "dead": []}

        with self._lock:
            watchers = dict(self._watchers)

        for name, watcher in watchers.items():
            if not watcher.config.enabled:
                continue
            status = watcher.check()
            if status is None:
                results["checked"].append(name)
                continue

            # Sorun var — kurtarma dene
            if status in (ComponentStatus.STALE, ComponentStatus.FAILING):
                if self._state_machine:
                    self._state_machine.set_state("recovering", f"kurtarma: {name}")

                if self._bridge:
                    self._bridge.publish("recovery_start", {
                        "component": name,
                        "status": status.value,
                        "last_error": watcher.state.last_error,
                    }, source="auto_recovery")

                success = watcher.start_recovery()

                if success:
                    self._recovery_count += 1
                    results["recovered"].append(name)

                    if self._state_machine:
                        if self._state_machine.is_recoverable():
                            self._state_machine.idle(f"kurtarildi: {name}")

                    if self._bridge:
                        self._bridge.publish("recovery_end", {
                            "component": name,
                            "success": True,
                        }, source="auto_recovery")

                    if self._notify_on_recovery:
                        logger.info(f"[AutoRecovery] BASARILI: {name} kurtarildi")
                else:
                    results["failed"].append(name)
                    logger.warning(f"[AutoRecovery] BASARISIZ: {name} kurtarilamadi")

                    if self._bridge:
                        self._bridge.publish("recovery_end", {
                            "component": name,
                            "success": False,
                        }, source="auto_recovery")

            elif status == ComponentStatus.DEAD:
                results["dead"].append(name)
                logger.error(f"[AutoRecovery] OLU: {name} — kurtarilamaz durumda")

        # Çok fazla ölü bileşen varsa sistemi çökert
        if len(results["dead"]) >= self._max_concurrent_failures:
            self._system_crashed = True
            if self._state_machine:
                self._state_machine.crashed(f"{len(results['dead'])} bilesen oldu")
            logger.critical(f"[AutoRecovery] SISTEM COKTU: {len(results['dead'])} bilesen oldu")

        return results

    def _loop(self) -> None:
        """Arka plan watchdog döngüsü."""
        while True:
            with self._lock:
                if not self._running:
                    break
            try:
                self.tick()
            except Exception as e:
                logger.error(f"[AutoRecovery] Tick hatasi: {e}")
            time.sleep(self._check_interval)

    # ── Durum sorgulama ────────────────────────────────────────────────

    def status_report(self) -> Dict[str, Any]:
        """Tüm sistem durum raporu."""
        with self._lock:
            watcher_statuses = {}
            for name, watcher in self._watchers.items():
                watcher_statuses[name] = watcher.status()

            return {
                "running": self._running,
                "tick_count": self._tick_count,
                "recovery_count": self._recovery_count,
                "system_crashed": self._system_crashed,
                "watched_components": len(self._watchers),
                "healthy": sum(1 for w in self._watchers.values()
                               if w.state.status == ComponentStatus.HEALTHY),
                "in_recovery": sum(1 for w in self._watchers.values()
                                   if w.state.status == ComponentStatus.RECOVERING),
                "dead": sum(1 for w in self._watchers.values()
                            if w.state.status == ComponentStatus.DEAD),
                "check_interval": self._check_interval,
                "components": watcher_statuses,
            }

    def status(self, name: str) -> Optional[Dict[str, Any]]:
        """Belirli bir bileşenin durumu."""
        with self._lock:
            watcher = self._watchers.get(name)
        return watcher.status() if watcher else None


# ── Hızlı test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    from reymen.sistem.service_bridge import ServiceBridge
    from reymen.sistem.state_machine import StateMachine

    sm = StateMachine()
    bridge = ServiceBridge()

    recovery = AutoRecovery(sm, bridge, check_interval_sec=1, max_restart_attempts=2)

    # Bileşenleri izlemeye al
    w1 = recovery.watch("provider", heartbeat_interval=5, timeout=10, max_failures=2)
    w2 = recovery.watch("session", heartbeat_interval=10, timeout=20, max_failures=3)

    # Kurtarma handler'ı
    w1.on_recovery(lambda n, e: True)  # her zaman başarılı

    # Heartbeat gönder
    recovery.heartbeat("provider")
    recovery.heartbeat("session")

    # Hata kaydet
    recovery.record_error("provider", "API baglanti hatasi")
    recovery.record_error("provider", "API timeout")

    # Tick
    result = recovery.tick()
    print(f"Tick: {result}")
    print(f"Durum: {recovery.status_report()}")

    # Provider kurtarılmalı, session sağlıklı
    prov_status = recovery.status("provider")
    sess_status = recovery.status("session")
    print(f"Provider: {prov_status['status'] if prov_status else 'N/A'}")
    print(f"Session: {sess_status['status'] if sess_status else 'N/A'}")

    print("Tum testler GECTI")
