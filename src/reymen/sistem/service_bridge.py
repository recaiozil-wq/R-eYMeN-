# -*- coding: utf-8 -*-
"""
service_bridge.py — ReYMeN Servis Köprüsü (Event Bus).

Component'ler arası gevşek bağlı iletişim sağlar.
Publish/Subscribe pattern ile çalışır:
    bridge = ServiceBridge()
    bridge.subscribe("state_changed", on_state_change)
    bridge.publish("state_changed", {"from": "idle", "to": "thinking"})

Desteklenen event tipleri:
    - state_changed:     State machine geçişleri
    - tool_call_start:   Araç çağrısı başladı
    - tool_call_end:     Araç çağrısı bitti
    - error:             Bileşen hatası
    - recovery_start:    Kurtarma başladı
    - recovery_end:      Kurtarma tamamlandı
    - heartbeat:         Bileşen canlılık sinyali
    - shutdown:          Sistem kapanıyor
    - config_reload:     Config yeniden yüklendi
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class EventType(enum.Enum):
    """Sistem event tipleri."""
    STATE_CHANGED = "state_changed"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    ERROR = "error"
    RECOVERY_START = "recovery_start"
    RECOVERY_END = "recovery_end"
    HEARTBEAT = "heartbeat"
    SHUTDOWN = "shutdown"
    CONFIG_RELOAD = "config_reload"
    COMPONENT_START = "component_start"
    COMPONENT_STOP = "component_stop"
    BRIDGE_STATUS = "bridge_status"
    CUSTOM = "custom"  # Kullanıcı tanımlı event'ler için joker


@dataclass
class Event:
    """Event mesajı."""
    type: str  # EventType.value veya özel isim
    source: str  # Hangi bileşenden geldiği
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    id: Optional[str] = None  # Opsiyonel event kimliği

    def __post_init__(self):
        if self.id is None:
            self.id = f"{self.source}_{int(self.timestamp * 1000)}"


EventHandler = Callable[[Event], None]
"""Event handler imzası: (Event) -> None"""


class ServiceBridge:
    """Thread-safe event bus / servis köprüsü."""

    def __init__(self, max_queue_size: int = 1000, log_events: bool = True):
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._lock = threading.RLock()
        self._max_queue_size = max_queue_size
        self._log_events = log_events
        self._event_count: int = 0
        self._last_events: List[Event] = []  # Son N event (debug için)
        self._started_at: float = time.time()
        self._component_health: Dict[str, float] = {}  # bileşen -> son heartbeat

    # ── Abonelik ───────────────────────────────────────────────────────

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Bir event tipine abone ol.

        Args:
            event_type: EventType.value veya "*" (tüm eventler)
            handler: Callback fonksiyonu
        """
        with self._lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                logger.debug(f"Abone eklendi: {event_type} -> {handler.__name__}")

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Abonelikten çık."""
        with self._lock:
            if handler in self._subscribers.get(event_type, []):
                self._subscribers[event_type].remove(handler)
                logger.debug(f"Abone cikarildi: {event_type} -> {handler.__name__}")

    def subscribe_all(self, handler: EventHandler) -> None:
        """Tüm eventlere abone ol (wildcard)."""
        self.subscribe("*", handler)

    # ── Yayınlama ──────────────────────────────────────────────────────

    def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None,
                source: str = "unknown", event_id: Optional[str] = None) -> Event:
        """Event yayınla — tüm abonelere ilet.

        Args:
            event_type: Event tipi (EventType.value veya özel)
            data: Event verisi
            source: Gönderen bileşen adı
            event_id: Opsiyonel event ID

        Returns:
            Oluşturulan Event nesnesi
        """
        event = Event(
            type=event_type,
            source=source,
            data=data or {},
            id=event_id,
        )

        with self._lock:
            self._event_count += 1
            self._last_events.append(event)
            if len(self._last_events) > self._max_queue_size:
                self._last_events.pop(0)

            # Belirtilen event tipi aboneleri
            handlers = list(self._subscribers.get(event_type, []))
            # Wildcard aboneleri (tekrarları önle)
            wildcard_handlers = list(self._subscribers.get("*", []))

        if self._log_events and event_type not in ("heartbeat",):
            logger.debug(f"[Bridge] {source} -> {event_type}: {data}")

        # Handler'ları lock dışında çağır (deadlock riski yok)
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Bridge handler hatasi [{event_type}]: {e}")

        for handler in wildcard_handlers:
            if handler in handlers:  # Çift çağrıyı önle
                continue
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Bridge wildcard handler hatasi [{event_type}]: {e}")

        return event

    # ── Heartbeat (bileşen canlılık) ────────────────────────────────────

    def heartbeat(self, component: str) -> None:
        """Bileşen canlılık sinyali."""
        with self._lock:
            self._component_health[component] = time.time()

    def component_healthy(self, component: str, max_age_sec: float = 30.0) -> bool:
        """Bileşen belirtilen süre içinde heartbeat göndermiş mi?"""
        with self._lock:
            last = self._component_health.get(component)
            if last is None:
                return False
            return (time.time() - last) < max_age_sec

    def all_components_healthy(self, components: List[str], max_age_sec: float = 30.0) -> bool:
        """Tüm belirtilen bileşenler sağlıklı mı?"""
        return all(self.component_healthy(c, max_age_sec) for c in components)

    # ── Durum / metrik ─────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Köprü durum raporu."""
        with self._lock:
            return {
                "aktif": True,
                "uptime_sec": round(time.time() - self._started_at, 1),
                "event_count": self._event_count,
                "subscriber_count": {
                    et: len(hs)
                    for et, hs in self._subscribers.items()
                },
                "known_components": list(self._component_health.keys()),
                "healthy_components": [
                    c for c in self._component_health
                    if (time.time() - self._component_health[c]) < 30
                ],
            }

    def last_events(self, count: int = 10) -> List[Event]:
        """Son N event."""
        with self._lock:
            return list(self._last_events[-count:])


# ── Hızlı test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    bridge = ServiceBridge()

    results = []

    def on_state_change(event):
        results.append(f"STATE: {event.data}")
        print(f"  [Handler] State degisti: {event.data}")

    def on_error(event):
        results.append(f"ERROR: {event.data}")
        print(f"  [Handler] Hata: {event.data}")

    bridge.subscribe(EventType.STATE_CHANGED.value, on_state_change)
    bridge.subscribe(EventType.ERROR.value, on_error)
    bridge.subscribe_all(lambda e: results.append(f"ALL: {e.type}"))

    bridge.publish(EventType.STATE_CHANGED.value, {"to": "thinking"}, source="state_machine")
    bridge.publish(EventType.ERROR.value, {"component": "provider", "msg": "API timeout"}, source="auto_recovery")

    status = bridge.status()
    print(f"Event count: {status['event_count']}")
    print(f"Bilesenler: {status['known_components']}")
    print(f"Sonuclar: {len(results)} handler cagrildi")
    assert len(results) >= 3, f"Sadece {len(results)} handler cagrildi"
    print("Tum testler GECTI")
