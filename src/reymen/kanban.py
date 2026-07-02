"""📊 Kanban Board + Worker — ReYMeN Kanban Worker seviyesinde.

Görevleri kanban panosunda yönetir. Kartlar kolonlar arasında taşınabilir,
önceliklendirilebilir, deadline takibi yapılabilir. Worker lifecycle
(orient → work → heartbeat → block/complete) desteği sunar.

Örnek::

    board = Board.load(\"board.json\")
    card = board.add(Card(title=\"Özellik ekle\", priority=Priority.HIGH), \"backlog\")
    board.move(card.id, \"ready\")
    board.claim(card.id, \"worker_1\")
    board.complete(card.id, summary=\"yapildi\", metadata={\"files\": [\"x.py\"]})
    board.save()
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import Any
import logging


__all__ = [
    "Priority",
    "CardStatus",
    "RunRecord",
    "Card",
    "Column",
    "Board",
    # Worker API
    "kanban_create",
    "kanban_show",
    "kanban_complete",
    "kanban_block",
    "kanban_comment",
    "kanban_heartbeat",
    "kanban_claim",
    "kanban_list",
    "kanban_summary",
    "kanban_delete_card",
]


# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------
class Priority(IntEnum):
    """Kart öncelik seviyeleri (düşük sayı = yüksek öncelik)."""

    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKLOG = 4

    @classmethod
    def from_str(cls, value: str | int | Priority) -> Priority:
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            return cls(value)
        s = str(value).strip().upper()
        for p in cls:
            if p.name == s or str(p.value) == s:
                return p
        aliases = {"URGENT": cls.CRITICAL, "BLOCKER": cls.CRITICAL,
                    "NORMAL": cls.MEDIUM, "TRIVIAL": cls.LOW}
        if s in aliases:
            return aliases[s]
        raise ValueError(f"Geçersiz öncelik: {value!r}")

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# CardStatus — state machine
# ---------------------------------------------------------------------------
class CardStatus(str):
    """Kart durumu (state machine)."""
    BACKLOG    = "backlog"     # Henüz başlanmadı
    TODO       = "todo"        # Sıradaki
    READY      = "ready"       # Bağımlılıkları tamam, başlanabilir
    INPROGRESS = "in_progress" # Çalışılıyor
    BLOCKED    = "blocked"     # Engel var (review bekliyor veya dış bağımlılık)
    REVIEW     = "review"      # İnceleme bekliyor
    DONE       = "done"        # Tamamlandı

    # Geçerli geçişler
    _GECISLER = {
        BACKLOG:    [TODO, READY, DONE],
        TODO:       [READY, INPROGRESS, DONE],
        READY:      [INPROGRESS, DONE],
        INPROGRESS: [BLOCKED, REVIEW, DONE],
        BLOCKED:    [INPROGRESS, REVIEW, DONE],
        REVIEW:     [INPROGRESS, BLOCKED, DONE],
        DONE:       [],  # terminal
    }

    @classmethod
    def gecerli_mi(cls, from_status: str, to_status: str) -> bool:
        """Geçerli bir durum geçişi mi kontrol et."""
        gecisler = cls._GECISLER.get(from_status, [])
        return to_status in gecisler


# ---------------------------------------------------------------------------
# RunRecord — her worker çalıştırma kaydı
# ---------------------------------------------------------------------------
@dataclass
class RunRecord:
    """Worker çalıştırma kaydı."""

    worker: str                    # Worker profil adı
    started_at: str                # ISO timestamp
    ended_at: str | None = None    # ISO timestamp
    outcome: str = "running"       # running / completed / blocked / timed_out / crashed
    summary: str = ""              # Özet
    error: str = ""                # Hata
    heartbeats: list[dict] = field(default_factory=list)  # Kalp atışları

    def as_dict(self) -> dict:
        return {
            "worker": self.worker,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "outcome": self.outcome,
            "summary": self.summary,
            "error": self.error,
            "heartbeats": self.heartbeats,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RunRecord:
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Card
# ---------------------------------------------------------------------------
@dataclass
class Card:
    """Kanban kartı — ReYMeN worker lifecycle destekli."""

    title: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    status: str = "backlog"
    priority: Priority = Priority.MEDIUM
    assignee: str | None = None      # Worker profil adı
    deadline: str | None = None      # ISO 8601
    tags: list[str] = field(default_factory=list)
    # Bağımlılık
    parents: list[str] = field(default_factory=list)    # Bu kartın bağımlı olduğu kart ID'leri
    children: list[str] = field(default_factory=list)   # Bu karta bağımlı kart ID'leri
    # Worker lifecycle
    runs: list[RunRecord] = field(default_factory=list)
    heartbeats: list[dict] = field(default_factory=list)  # Son worker heartbeats
    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    comment_thread: list[dict[str, Any]] = field(default_factory=list)
    # Zaman
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    order: int = 0

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def is_overdue(self, now: str | None = None) -> bool:
        if not self.deadline:
            return False
        now = now or datetime.now(timezone.utc).isoformat()
        return self.deadline < now

    def add_comment(self, author: str, body: str) -> dict:
        """Karta yorum ekle."""
        entry = {
            "id": uuid.uuid4().hex[:8],
            "author": author,
            "body": body,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.comment_thread.append(entry)
        self.touch()
        return entry

    def add_heartbeat(self, status: str, message: str = "") -> dict:
        """Worker heartbeat ekle."""
        hb = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "message": message,
        }
        self.heartbeats.append(hb)
        self.touch()
        return hb

    def start_run(self, worker: str) -> RunRecord:
        """Yeni bir worker run'ı başlat."""
        run = RunRecord(worker=worker, started_at=datetime.now(timezone.utc).isoformat())
        self.runs.append(run)
        self.touch()
        return run

    def end_run(self, outcome: str, summary: str = "", error: str = "") -> None:
        """Son run'ı sonlandır."""
        if self.runs:
            run = self.runs[-1]
            run.ended_at = datetime.now(timezone.utc).isoformat()
            run.outcome = outcome
            run.summary = summary
            run.error = error
            self.summary = summary
            self.touch()

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["priority"] = int(self.priority)
        d["priority_name"] = self.priority.name
        d["runs"] = [r.as_dict() for r in self.runs]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Card:
        data = dict(data)
        if "priority" in data:
            data["priority"] = Priority.from_str(data["priority"])
        if "runs" in data:
            data["runs"] = [RunRecord.from_dict(r) for r in data["runs"]]
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Column
# ---------------------------------------------------------------------------
@dataclass
class Column:
    """Kanban kolonu (kart listesi)."""

    name: str
    cards: list[Card] = field(default_factory=list)
    wip_limit: int | None = None

    def add(self, card: Card) -> None:
        if self.wip_limit is not None and len(self.cards) >= self.wip_limit:
            raise ValueError(
                f"Kolon '{self.name}' WIP limitine ({self.wip_limit}) ulaştı")
        card.order = len(self.cards)
        self.cards.append(card)

    def remove(self, card_id: str) -> Card | None:
        for i, c in enumerate(self.cards):
            if c.id == card_id:
                return self.cards.pop(i)
        return None

    def get(self, card_id: str) -> Card | None:
        for c in self.cards:
            if c.id == card_id:
                return c
        return None

    def sort_by_priority(self) -> None:
        self.cards.sort(key=lambda c: (c.priority, c.order))
        for i, c in enumerate(self.cards):
            c.order = i

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "wip_limit": self.wip_limit,
            "cards": [c.as_dict() for c in self.cards],
        }


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------
class Board:
    """Kanban panosu — ReYMeN worker lifecycle destekli.

    Varsayılan kolonlar:
        backlog → todo → ready → in_progress → blocked → review → done
    """

    DEFAULT_COLUMNS = ["backlog", "todo", "ready", "in_progress",
                       "blocked", "review", "done"]

    def __init__(self, name: str = "Pano", columns: list[Column] | None = None):
        self.name = name
        if columns is None:
            self.columns = [Column(name=n) for n in self.DEFAULT_COLUMNS]
        else:
            self.columns = columns

    # -- Kolon işlemleri ----------------------------------------------------

    def add_column(self, name: str, wip_limit: int | None = None) -> Column:
        if self.get_column(name):
            raise ValueError(f"Kolon '{name}' zaten var")
        col = Column(name=name, wip_limit=wip_limit)
        self.columns.append(col)
        return col

    def get_column(self, name: str) -> Column | None:
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def remove_column(self, name: str) -> bool:
        col = self.get_column(name)
        if col is None:
            return False
        self.columns.remove(col)
        return True

    # -- Kart işlemleri -----------------------------------------------------

    def _kolon_ismi(self, status: str) -> str:
        """status değerini kolon adına çevir."""
        status_to_column = {
            "backlog": "backlog", "todo": "todo", "ready": "ready",
            "in_progress": "in_progress", "blocked": "blocked",
            "review": "review", "done": "done",
        }
        return status_to_column.get(status, status)

    def add(self, card: Card, column: str = "backlog") -> Card:
        col = self.get_column(column)
        if col is None:
            raise ValueError(f"Kolon '{column}' bulunamadı")
        card.status = column
        col.add(card)
        return card

    def move(self, card_id: str, to_column: str) -> Card:
        """Kartı bir kolona taşı. Status geçişini kontrol eder."""
        card = self.find(card_id)
        if card is None:
            raise ValueError(f"Kart '{card_id}' bulunamadı")

        # Aynı durum → idempotent, sessiz geç
        if card.status == to_column:
            return card

        # Status geçiş kontrolü
        if not CardStatus.gecerli_mi(card.status, to_column):
            raise ValueError(
                f"Geçersiz durum geçişi: '{card.status}' -> '{to_column}'. "
                f"İzin verilenler: {CardStatus._GECISLER.get(card.status, [])}"
            )

        target = self.get_column(to_column)
        if target is None:
            raise ValueError(f"Hedef kolon '{to_column}' bulunamadı")

        # Kaynaktan çıkar
        for col in self.columns:
            if col.get(card_id):
                col.remove(card_id)
                break

        card.status = to_column
        card.touch()
        target.add(card)

        # Auto-promotion: parent'ları kontrol et
        self._auto_promote_children(card_id)

        return card

    def _auto_promote_children(self, card_id: str) -> None:
        """Eğer kart DONE olduysa ve child'ları varsa, onları ready'e al."""
        card = self.find(card_id)
        if card is None or card.status != "done":
            return

        changed = []
        for child_id in list(card.children):
            child = self.find(child_id)
            if child and child.status == "todo":
                # Tüm parent'ları done mı kontrol et
                tum_parent_done = all(
                    (p := self.find(pid)) and p.status == "done"
                    for pid in child.parents
                )
                if tum_parent_done:
                    self.move(child_id, "ready")
                    changed.append(child.title)

    def set_status(self, card_id: str, new_status: str) -> Card:
        """Kartın durumunu güncelle (otomatik kolon taşıma ile)."""
        col_name = self._kolon_ismi(new_status)
        return self.move(card_id, col_name)

    def prioritize(self, card_id: str, priority: Priority | str) -> Card:
        priority = Priority.from_str(priority)
        for col in self.columns:
            card = col.get(card_id)
            if card:
                card.priority = priority
                card.touch()
                col.sort_by_priority()
                return card
        raise ValueError(f"Kart '{card_id}' bulunamadı")

    def set_deadline(self, card_id: str, deadline: str) -> Card:
        for col in self.columns:
            card = col.get(card_id)
            if card:
                card.deadline = deadline
                card.touch()
                return card
        raise ValueError(f"Kart '{card_id}' bulunamadı")

    def find(self, card_id: str) -> Card | None:
        for col in self.columns:
            card = col.get(card_id)
            if card is not None:
                return card
        return None

    def all_cards(self) -> list[Card]:
        return [c for col in self.columns for c in col.cards]

    def overdue_cards(self) -> list[Card]:
        return [c for c in self.all_cards() if c.is_overdue()]

    def cards_by_assignee(self, assignee: str) -> list[Card]:
        """Bir worker'a atanmış tüm kartları döndür."""
        return [c for c in self.all_cards()
                if c.assignee == assignee and c.status not in ("done",)]

    # -- Worker lifecycle ---------------------------------------------------

    def claim(self, card_id: str, worker: str) -> Card:
        """Worker bir kartı üstlenir → in_progress."""
        card = self.find(card_id)
        if card is None:
            raise ValueError(f"Kart '{card_id}' bulunamadı")
        if card.assignee and card.assignee != worker:
            raise ValueError(f"Kart '{card_id}' zaten {card.assignee}'a atanmış")
        card.assignee = worker
        card.start_run(worker)
        return self.set_status(card_id, "in_progress")

    def complete(self, card_id: str, summary: str = "",
                 metadata: dict | None = None) -> Card:
        """Worker kartı tamamlar → done."""
        card = self.find(card_id)
        if card is None:
            raise ValueError(f"Kart '{card_id}' bulunamadı")
        card.end_run("completed", summary=summary)
        if metadata:
            card.metadata.update(metadata)
        return self.set_status(card_id, "done")

    def block(self, card_id: str, reason: str) -> Card:
        """Worker kartı bloke eder."""
        card = self.find(card_id)
        if card is None:
            raise ValueError(f"Kart '{card_id}' bulunamadı")
        card.metadata["block_reason"] = reason
        return self.set_status(card_id, "blocked")

    def unblock(self, card_id: str) -> Card:
        """Worker kartın blokesini kaldırır → in_progress."""
        card = self.find(card_id)
        if card is None:
            raise ValueError(f"Kart '{card_id}' bulunamadı")
        if card.status != "blocked":
            raise ValueError(f"Kart '{card_id}' bloke durumunda değil (={card.status})")
        return self.set_status(card_id, "in_progress")

    def comment(self, card_id: str, author: str, body: str) -> dict:
        """Karta yorum ekle."""
        card = self.find(card_id)
        if card is None:
            raise ValueError(f"Kart '{card_id}' bulunamadı")
        return card.add_comment(author, body)

    def heartbeat(self, card_id: str, worker: str, message: str = "") -> dict:
        """Worker heartbeat."""
        card = self.find(card_id)
        if card is None:
            raise ValueError(f"Kart '{card_id}' bulunamadı")
        return card.add_heartbeat(worker, message)

    def link(self, parent_id: str, child_id: str) -> None:
        """İki kart arasında parent-child bağı kur."""
        parent = self.find(parent_id)
        child = self.find(child_id)
        if parent is None or child is None:
            raise ValueError("Parent veya child kart bulunamadı")
        if child_id not in parent.children:
            parent.children.append(child_id)
        if parent_id not in child.parents:
            child.parents.append(parent_id)
        parent.touch()
        child.touch()

    # -- Sorgu --------------------------------------------------------------

    def query(self, status: str | None = None,
              assignee: str | None = None,
              tag: str | None = None,
              overdue: bool | None = None,
              limit: int = 50) -> list[Card]:
        """Kartları filtrele."""
        cards = self.all_cards()
        if status:
            cards = [c for c in cards if c.status == status]
        if assignee:
            cards = [c for c in cards if c.assignee == assignee]
        if tag:
            cards = [c for c in cards if tag in c.tags]
        if overdue:
            cards = [c for c in cards if c.is_overdue()]
        cards.sort(key=lambda c: (c.priority, c.order))
        return cards[:limit]

    # -- Özet ---------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "columns": {
                col.name: {
                    "count": len(col.cards),
                    "wip_limit": col.wip_limit,
                    "over_limit": (col.wip_limit is not None
                                   and len(col.cards) > col.wip_limit),
                }
                for col in self.columns
            },
            "total_cards": len(self.all_cards()),
            "overdue": len(self.overdue_cards()),
            "by_priority": {
                p.name: len([c for c in self.all_cards() if c.priority == p])
                for p in Priority
            },
        }

    # -- Serileştirme -------------------------------------------------------

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "columns": [col.as_dict() for col in self.columns],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.as_dict(), indent=indent, ensure_ascii=False)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Board:
        columns = [
            Column(
                name=c["name"],
                wip_limit=c.get("wip_limit"),
                cards=[Card.from_dict(card) for card in c.get("cards", [])],
            )
            for c in data.get("columns", [])
        ]
        return cls(name=data.get("name", "Pano"), columns=columns)

    @classmethod
    def load(cls, path: str | Path) -> Board:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# Global Board singleton (JSON dosyası tabanlı)
# ---------------------------------------------------------------------------

_VARSAYILAN_PANO_YOLU = Path("~/.hermes/kanban_board.json").expanduser()


def _pano() -> Board:
    """Global board singleton'ını döndür (JSON'dan yükler)."""
    pano_yolu = _VARSAYILAN_PANO_YOLU
    if pano_yolu.exists():
        return Board.load(pano_yolu)

    board = Board(name="ReYMeN Kanban")
    board.save(pano_yolu)
    return board


def _pano_kaydet(board: Board) -> None:
    """Board'u JSON'a kaydet."""
    board.save(_VARSAYILAN_PANO_YOLU)


# ---------------------------------------------------------------------------
# Worker API — motor tool'ları için fonksiyonlar
# ---------------------------------------------------------------------------

def kanban_create(title: str, description: str = "", assignee: str | None = None,
                   priority: str = "MEDIUM", parents: list[str] | None = None,
                   tags: list[str] | None = None, deadline: str | None = None) -> str:
    """Yeni bir kart oluştur.

    Args:
        title: Kart başlığı.
        description: Açıklama.
        assignee: Worker profil adı.
        priority: Öncelik (CRITICAL/HIGH/MEDIUM/LOW/BACKLOG).
        parents: Bağımlı olunan kart ID'leri (child otomatik 'todo' olur).
        tags: Etiketler.
        deadline: ISO 8601 deadline.

    Returns:
        Oluşturulan kartın ID'si.
    """
    board = _pano()
    prio = Priority.from_str(priority)

    # Varsayılan olarak 'todo'
    ilk_kolon = "todo"

    card = Card(
        title=title,
        description=description,
        priority=prio,
        assignee=assignee,
        deadline=deadline,
        tags=tags or [],
    )

    board.add(card, ilk_kolon)

    # Parent-child bağı
    if parents:
        for pid in parents:
            parent_card = board.find(pid)
            if parent_card:
                board.link(pid, card.id)

    _pano_kaydet(board)
    return card.id


def kanban_show(card_id: str) -> str:
    """Kart detayını göster.

    Args:
        card_id: Kart ID'si.

    Returns:
        Kart detayı metni.
    """
    board = _pano()
    card = board.find(card_id)
    if card is None:
        return f"[KANBAN] Kart '{card_id}' bulunamadı"

    satirlar = [
        f"📋 {card.title} ({card.id})",
        f"  Durum: {card.status}",
        f"  Öncelik: {card.priority.name}",
        f"  Atanan: {card.assignee or '—'}",
        f"  Deadline: {card.deadline or '—'}",
        f"  Etiketler: {', '.join(card.tags) if card.tags else '—'}",
        f"  Oluşturma: {card.created_at[:19]}",
        f"  Güncelleme: {card.updated_at[:19]}",
    ]

    if card.parents:
        parent_isl = [f"{board.find(pid).title if board.find(pid) else pid} ({pid})"
                       for pid in card.parents]
        satirlar.append(f"  Bağımlı olduğu: {', '.join(parent_isl)}")

    if card.children:
        child_isl = [f"{board.find(cid).title if board.find(cid) else cid} ({cid})"
                      for cid in card.children]
        satirlar.append(f"  Alt kartlar: {', '.join(child_isl)}")

    if card.metadata:
        satirlar.append(f"  Metadata: {json.dumps(card.metadata, ensure_ascii=False)[:200]}")

    if card.comment_thread:
        satirlar.append(f"  Yorumlar ({len(card.comment_thread)}):")
        for y in card.comment_thread[-3:]:
            satirlar.append(f"    [{y['author']}] {y['body'][:100]}")

    if card.runs:
        son_run = card.runs[-1]
        satirlar.append(f"  Son run: {son_run.worker} -> {son_run.outcome}"
                        f"{' | ' + son_run.summary[:80] if son_run.summary else ''}")

    return "\n".join(satirlar)


def kanban_complete(card_id: str, summary: str = "",
                    metadata: str | None = None) -> str:
    """Kartı tamamla.

    Args:
        card_id: Kart ID'si.
        summary: Özet (downstream worker'ların okuyacağı).
        metadata: JSON string metadata (örn. changed_files, tests_passed).

    Returns:
        İşlem sonucu.
    """
    board = _pano()
    meta_dict = json.loads(metadata) if metadata else None
    card = board.complete(card_id, summary=summary, metadata=meta_dict)
    _pano_kaydet(board)
    return f"[KANBAN] '{card.title}' tamamlandı (id={card_id})"


def kanban_block(card_id: str, reason: str) -> str:
    """Kartı bloke et (review bekliyor, dış bağımlılık vb.).

    Args:
        card_id: Kart ID'si.
        reason: Blok nedeni. 'review-required: ' öneki dashboard'da gösterilir.

    Returns:
        İşlem sonucu.
    """
    board = _pano()
    card = board.find(card_id)
    if card is None:
        return f"[KANBAN] Kart '{card_id}' bulunamadı"
    board.block(card_id, reason)
    card.end_run("blocked", error=reason)
    _pano_kaydet(board)
    return f"[KANBAN] '{card.title}' bloke edildi: {reason[:100]}"


def kanban_unblock(card_id: str) -> str:
    """Kartın blokesini kaldır.

    Args:
        card_id: Kart ID'si.

    Returns:
        İşlem sonucu.
    """
    board = _pano()
    card = board.find(card_id)
    if card is None:
        return f"[KANBAN] Kart '{card_id}' bulunamadı"
    board.unblock(card_id)
    _pano_kaydet(board)
    return f"[KANBAN] '{card.title}' blokesi kaldırıldı"


def kanban_comment(card_id: str, body: str) -> str:
    """Karta yorum ekle.

    Args:
        card_id: Kart ID'si.
        body: Yorum metni (JSON formatında metadata içerebilir).

    Returns:
        İşlem sonucu.
    """
    board = _pano()
    card = board.find(card_id)
    if card is None:
        return f"[KANBAN] Kart '{card_id}' bulunamadı"
    card.add_comment("worker", body)
    _pano_kaydet(board)
    return f"[KANBAN] Yorum eklendi: {card_id}"


def kanban_heartbeat(card_id: str, worker: str, message: str = "") -> str:
    """Worker heartbeat gönder.

    Args:
        card_id: Kart ID'si.
        worker: Worker adı.
        message: Durum mesajı.

    Returns:
        İşlem sonucu.
    """
    board = _pano()
    card = board.find(card_id)
    if card is None:
        return f"[KANBAN] Kart '{card_id}' bulunamadı"
    card.add_heartbeat(worker, message)
    _pano_kaydet(board)
    return f"[KANBAN] Heartbeat: {card_id} ({message[:50]})"


def kanban_claim(card_id: str, worker: str) -> str:
    """Worker bir kartı üstlenir.

    Args:
        card_id: Kart ID'si.
        worker: Worker profil adı.

    Returns:
        İşlem sonucu.
    """
    board = _pano()
    card = board.claim(card_id, worker)
    _pano_kaydet(board)
    return f"[KANBAN] '{card.title}' -> {worker} (id={card_id})"


def kanban_list(status: str | None = None, assignee: str | None = None,
                tag: str | None = None, overdue: bool = False) -> str:
    """Kartları listele.

    Args:
        status: Durum filtre (backlog/todo/ready/in_progress/blocked/review/done).
        assignee: Worker filtresi.
        tag: Etiket filtresi.
        overdue: Sadece deadline geçmiş kartlar.

    Returns:
        Kart listesi metni.
    """
    board = _pano()
    cards = board.query(status=status, assignee=assignee, tag=tag,
                         overdue=overdue if overdue else None)

    if not cards:
        return "[KANBAN] Kart bulunamadı"

    satirlar = [
        f"[KANBAN] {len(cards)} kart"
        + (f" (status={status})" if status else "")
        + (f" (assignee={assignee})" if assignee else "")
        + ":"
    ]

    for c in cards:
        deadline_str = f" ⏰{c.deadline[:10]}" if c.deadline else ""
        emoji = {"done": "✅", "in_progress": "🔄", "blocked": "🚫",
                 "review": "👁", "todo": "📝", "ready": "▶️", "backlog": "📦"}.get(c.status, "📋")
        satirlar.append(f"  {emoji} [{c.id[:8]}] {c.title}{deadline_str}"
                        f" ({c.priority.name})"
                        f"{' -> ' + c.assignee if c.assignee else ''}")

    return "\n".join(satirlar)


def kanban_summary() -> str:
    """Pano özetini göster.

    Returns:
        Özet metni.
    """
    board = _pano()
    s = board.summary()
    satirlar = [
        f"[KANBAN] Pano: {s['name']}",
        f"  Toplam kart: {s['total_cards']}",
        f"  Gecikmiş: {s['overdue']}",
    ]
    for col_name, col_data in s["columns"].items():
        wip_str = f" (WIP: {col_data['count']}/{col_data['wip_limit']})" if col_data['wip_limit'] else ""
        over_str = " ⚠️ LIMIT ASIMI" if col_data.get("over_limit") else ""
        satirlar.append(f"  {col_name}: {col_data['count']}{wip_str}{over_str}")

    satirlar.append("\n  Öncelik dağılımı:")
    for pname, count in s["by_priority"].items():
        satirlar.append(f"    {pname}: {count}")

    return "\n".join(satirlar)


def kanban_delete_card(card_id: str) -> str:
    """Kartı sil.

    Args:
        card_id: Kart ID'si.

    Returns:
        İşlem sonucu.
    """
    board = _pano()
    card = board.find(card_id)
    if card is None:
        return f"[KANBAN] Kart '{card_id}' bulunamadı"

    baslik = card.title
    for col in board.columns:
        if col.remove(card_id):
            break

    _pano_kaydet(board)
    return f"[KANBAN] '{baslik}' silindi (id={card_id})"


# ---------------------------------------------------------------------------
# Motor kayıt
# ---------------------------------------------------------------------------

def motor_kaydet(motor: Any) -> None:
    """Motor'a Kanban araçlarını kaydet.

    Args:
        motor: Motor instance'ı.
    """
    motor._plugin_arac_kaydet(
        "KANBAN_CREATE", kanban_create,
        "Kanban kartı oluştur. Parametreler: title (str, zorunlu), description (str), "
        "assignee (str), priority (str: CRITICAL/HIGH/MEDIUM/LOW/BACKLOG), "
        "parents (list[str]): bağımlılık listesi, tags (list[str]), deadline (str: ISO 8601)"
    )
    motor._plugin_arac_kaydet(
        "KANBAN_SHOW", kanban_show,
        "Kart detayını göster. Parametre: card_id (str)"
    )
    motor._plugin_arac_kaydet(
        "KANBAN_COMPLETE", kanban_complete,
        "Kartı tamamla. Parametreler: card_id (str), summary (str), "
        "metadata (str: JSON string — changed_files, tests_passed, decisions vb.)"
    )
    motor._plugin_arac_kaydet(
        "KANBAN_BLOCK", kanban_block,
        "Kartı bloke et. Parametreler: card_id (str), reason (str). "
        "'review-required: ' öneki ile inceleme bekleme"
    )
    motor._plugin_arac_kaydet(
        "KANBAN_UNBLOCK", kanban_unblock,
        "Kartın blokesini kaldır. Parametre: card_id (str)"
    )
    motor._plugin_arac_kaydet(
        "KANBAN_COMMENT", kanban_comment,
        "Karta yorum ekle. Parametreler: card_id (str), body (str)"
    )
    motor._plugin_arac_kaydet(
        "KANBAN_HEARTBEAT", kanban_heartbeat,
        "Worker heartbeat gönder. Parametreler: card_id (str), worker (str), message (str)"
    )
    motor._plugin_arac_kaydet(
        "KANBAN_CLAIM", kanban_claim,
        "Worker kartı üstlenir. Parametreler: card_id (str), worker (str)"
    )
    motor._plugin_arac_kaydet(
        "KANBAN_LIST", kanban_list,
        "Kartları listele. Parametreler: status (str), assignee (str), "
        "tag (str), overdue (bool)"
    )
    motor._plugin_arac_kaydet(
        "KANBAN_SUMMARY", kanban_summary,
        "Pano özetini göster. Parametre yok."
    )
    motor._plugin_arac_kaydet(
        "KANBAN_DELETE", kanban_delete_card,
        "Kartı sil. Parametre: card_id (str)"
    )

    logger = logging.getLogger(__name__)
    logger.info("[KANBAN] Motor'a 11 arac kaydedildi")


def kanban_worker_baslat(interval: int = 300) -> str:
    """KANBAN_WORKER_BASLAT(interval=300) — Kanban worker dongusu baslat."""
    try:
        from reymen.kanban import Board
        board = Board()
        import threading, time
        def _loop():
            while True:
                try:
                    for col in board.columns:
                        for card in col.cards[:]:  # copy
                            if card.status.name == "TODO" or card.status == "todo":
                                col.remove(card.id)
                                done_col = board.get_column("DONE") or board.get_column("done")
                                if done_col:
                                    done_col.add(card)
                                    card.status = "done"
                                    card.add_comment("Worker", "Auto-completed by worker")
                    board.save()
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )
                time.sleep(interval)
        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        return f"[Kanban] Worker baslatildi (interval={interval}s)"
    except Exception as e:
        return f"[Kanban] Worker hatasi: {e}"


def motor_kaydet(motor):
    """Kanban motor araclarini kaydeder."""
    from reymen.kanban import (
        kanban_create, kanban_list, kanban_move, kanban_summary, kanban_delete_card
    )
    motor._plugin_arac_kaydet("KANBAN_CREATE", kanban_create, "Kart olustur")
    motor._plugin_arac_kaydet("KANBAN_LIST", kanban_list, "Kartlari listele")
    motor._plugin_arac_kaydet("KANBAN_MOVE", kanban_move, "Kart tasi")
    motor._plugin_arac_kaydet("KANBAN_SUMMARY", kanban_summary, "Pano ozeti")
    motor._plugin_arac_kaydet("KANBAN_DELETE", kanban_delete_card, "Kart sil")
    motor._plugin_arac_kaydet("KANBAN_WORKER_BASLAT", kanban_worker_baslat, "Worker dongusu baslat")
    logger = logging.getLogger(__name__)
    logger.info("[KANBAN] Motor'a 6 arac kaydedildi")

