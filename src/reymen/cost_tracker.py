"""💰 Cost tracking — API harcama takibi + log.

Model API çağrılarının token maliyetlerini ve dolar bazlı harcamalarını
izler. Veriler SQLite ile kalıcı olarak saklanır; tablo yoksa otomatik
oluşturulur. Fiyat tablosu config üzerinden geçersiz kılınabilir.

Örnek::

    from ReYMeN.cost_tracker import record_usage, summary
import logging
logger = logging.getLogger(__name__)

    record_usage(model="gpt-4o", prompt_tokens=1200, completion_tokens=300)
    print(summary())
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

__all__ = [
    "DEFAULT_PRICE_TABLE",
    "CostRecord",
    "CostTracker",
    "record_usage",
    "summary",
    "reset",
    "dump_log",
    "set_db_path",
    "set_price_table",
]

# ---------------------------------------------------------------------------
# Varsayılan fiyat tablosu (USD / 1M token). Config ile geçersiz kılınabilir.
# ---------------------------------------------------------------------------
DEFAULT_PRICE_TABLE: dict[str, dict[str, float]] = {
    "gpt-4o": {"prompt": 5.0, "completion": 15.0},
    "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    "gpt-4-turbo": {"prompt": 10.0, "completion": 30.0},
    "gpt-3.5-turbo": {"prompt": 0.50, "completion": 1.50},
    "claude-3-5-sonnet": {"prompt": 3.0, "completion": 15.0},
    "claude-3-5-haiku": {"prompt": 0.80, "completion": 4.0},
    "claude-3-opus": {"prompt": 15.0, "completion": 75.0},
    "o1": {"prompt": 15.0, "completion": 60.0},
    "o1-mini": {"prompt": 3.0, "completion": 12.0},
    # Bilinmeyen modeller için güvenli fallback
    "default": {"prompt": 1.0, "completion": 3.0},
}


def _default_db_path() -> Path:
    """ReYMeN home dizini altında costs.db yolu döndürür."""
    home = os.environ.get("ReYMeN_HOME")
    if home:
        base = Path(home)
    else:
        base = Path.home() / ".ReYMeN"
    base.mkdir(parents=True, exist_ok=True)
    return base / "costs.db"


@dataclass
class CostRecord:
    """Tek bir API çağrısının maliyet kaydı."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    provider: str = ""
    timestamp: float = field(default_factory=time.time)
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": self.cost_usd,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "metadata": self.metadata,
        }


class CostTracker:
    """Thread-safe, SQLite destekli maliyet takipçisi.

    Tüm metotlar aynı ``CostTracker`` örneği üzerinde thread-safe'dir.
    Modül seviyesindeki kolaylık fonksiyonları (``record_usage`` vb.) global
    bir singleton üzerinden çalışır.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        price_table: dict[str, dict[str, float]] | None = None,
    ) -> None:
        self._db_path = Path(db_path) if db_path else _default_db_path()
        self._price_table = price_table or DEFAULT_PRICE_TABLE
        self._lock = threading.Lock()
        self._init_db()

    # -- DB -----------------------------------------------------------------
    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    model TEXT NOT NULL,
                    provider TEXT DEFAULT '',
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    session_id TEXT,
                    metadata TEXT
                )
                """
            )
            # Migration: add missing columns for existing DBs
            self._migrate_add_column(conn, "cost_log", "provider", "TEXT DEFAULT ''")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cost_model ON cost_log(model)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cost_ts ON cost_log(timestamp)"
            )

    @staticmethod
    def _migrate_add_column(conn: sqlite3.Connection, table: str, column: str, col_def: str) -> None:
        """Add a column to an existing table if it doesn't already exist."""
        cursor = conn.execute(f"PRAGMA table_info({table})")
        existing_cols = {row[1] for row in cursor.fetchall()}
        if column not in existing_cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # -- Fiyat hesaplama ----------------------------------------------------
    def _price_for(self, model: str) -> dict[str, float]:
        if model in self._price_table:
            return self._price_table[model]
        # Prefix eşleştirme: "gpt-4o-2024-08-06" -> "gpt-4o"
        for key in self._price_table:
            if key != "default" and model.startswith(key):
                return self._price_table[key]
        return self._price_table["default"]

    def compute_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Verilen token sayıları için USD maliyeti hesaplar."""
        price = self._price_for(model)
        cost = (
            (prompt_tokens / 1_000_000.0) * price["prompt"]
            + (completion_tokens / 1_000_000.0) * price["completion"]
        )
        return round(cost, 6)

    # -- Kayıt --------------------------------------------------------------
    def record(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        *,
        provider: str = "",
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CostRecord:
        """Tek bir API kullanımını kaydeder ve ``CostRecord`` döndürür."""
        if prompt_tokens < 0 or completion_tokens < 0:
            raise ValueError("token sayıları negatif olamaz")
        cost = self.compute_cost(model, prompt_tokens, completion_tokens)
        record = CostRecord(
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            session_id=session_id,
            metadata=metadata or {},
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO cost_log
                    (timestamp, model, provider, prompt_tokens, completion_tokens,
                     cost_usd, session_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.timestamp,
                    record.model,
                    record.provider,
                    record.prompt_tokens,
                    record.completion_tokens,
                    record.cost_usd,
                    record.session_id,
                    json.dumps(record.metadata, ensure_ascii=False),
                ),
            )
        # Analitik modulune de kaydet (varsa)
        try:
            from reymen.sistem.analitik import kaydet
            kaydet(
                tur="maliyet",
                kaynak=provider or model,
                token_giris=prompt_tokens,
                token_cikis=completion_tokens,
                maliyet=cost,
                detay={"model": model, "provider": provider},
            )
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )
        return record

    # -- Sorgu --------------------------------------------------------------
    def summary(
        self,
        *,
        model: str | None = None,
        session_id: str | None = None,
        since: float | None = None,
    ) -> dict[str, Any]:
        """Özet rapor döndürür.

        Parametreler ile filtreleme yapılabilir. Dönüş değeri::

            {
                "total_calls": int,
                "total_prompt_tokens": int,
                "total_completion_tokens": int,
                "total_tokens": int,
                "total_cost_usd": float,
                "by_model": {model: {...}},
            }
        """
        clauses: list[str] = []
        params: list[Any] = []
        if model is not None:
            clauses.append("model = ?")
            params.append(model)
        if session_id is not None:
            clauses.append("session_id = ?")
            params.append(session_id)
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(since)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT COUNT(*) AS total_calls,
                       COALESCE(SUM(prompt_tokens), 0) AS prompt,
                       COALESCE(SUM(completion_tokens), 0) AS completion,
                       COALESCE(SUM(cost_usd), 0.0) AS cost
                FROM cost_log{where}
                """,
                params,
            ).fetchone()

            by_model_rows = conn.execute(
                f"""
                SELECT model,
                       COUNT(*) AS calls,
                       COALESCE(SUM(prompt_tokens), 0) AS prompt,
                       COALESCE(SUM(completion_tokens), 0) AS completion,
                       COALESCE(SUM(cost_usd), 0.0) AS cost
                FROM cost_log{where}
                GROUP BY model
                ORDER BY cost DESC
                """,
                params,
            ).fetchall()

            by_provider_rows = conn.execute(
                f"""
                SELECT provider,
                       COUNT(*) AS calls,
                       COALESCE(SUM(prompt_tokens), 0) AS prompt,
                       COALESCE(SUM(completion_tokens), 0) AS completion,
                       COALESCE(SUM(cost_usd), 0.0) AS cost
                FROM cost_log{where + " AND" if clauses else " WHERE"} provider != ''
                GROUP BY provider
                ORDER BY cost DESC
                """,
                params,
            ).fetchall()

        prompt = int(row["prompt"])
        completion = int(row["completion"])
        return {
            "total_calls": int(row["total_calls"]),
            "total_prompt_tokens": prompt,
            "total_completion_tokens": completion,
            "total_tokens": prompt + completion,
            "total_cost_usd": round(float(row["cost"]), 6),
            "by_model": {
                r["model"]: {
                    "calls": int(r["calls"]),
                    "prompt_tokens": int(r["prompt"]),
                    "completion_tokens": int(r["completion"]),
                    "cost_usd": round(float(r["cost"]), 6),
                }
                for r in by_model_rows
            },
            "by_provider": {
                r["provider"]: {
                    "calls": int(r["calls"]),
                    "prompt_tokens": int(r["prompt"]),
                    "completion_tokens": int(r["completion"]),
                    "cost_usd": round(float(r["cost"]), 6),
                }
                for r in by_provider_rows
            },
        }

    def dump_log(
        self,
        *,
        limit: int = 100,
        model: str | None = None,
    ) -> list[dict[str, Any]]:
        """Ham kayıtları döndürür (en yeni first)."""
        clauses: list[str] = []
        params: list[Any] = []
        if model is not None:
            clauses.append("model = ?")
            params.append(model)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT timestamp, model, prompt_tokens, completion_tokens,
                       cost_usd, session_id, metadata
                FROM cost_log{where}
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                params,
            ).fetchall()

        result: list[dict[str, Any]] = []
        for r in rows:
            try:
                meta = json.loads(r["metadata"]) if r["metadata"] else {}
            except (json.JSONDecodeError, TypeError):
                meta = {}
            result.append(
                {
                    "timestamp": float(r["timestamp"]),
                    "model": r["model"],
                    "prompt_tokens": int(r["prompt_tokens"]),
                    "completion_tokens": int(r["completion_tokens"]),
                    "cost_usd": round(float(r["cost_usd"]), 6),
                    "session_id": r["session_id"],
                    "metadata": meta,
                }
            )
        return result

    def reset(self) -> int:
        """Tüm kayıtları siler, silinen satır sayısını döndürür."""
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM cost_log")
            return int(cur.rowcount)

    def iter_records(self) -> Iterable[CostRecord]:
        """Tüm kayıtları ``CostRecord`` olarak iterasyon."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT timestamp, model, prompt_tokens, completion_tokens,
                       cost_usd, session_id, metadata
                FROM cost_log ORDER BY timestamp ASC
                """
            ).fetchall()
        for r in rows:
            try:
                meta = json.loads(r["metadata"]) if r["metadata"] else {}
            except (json.JSONDecodeError, TypeError):
                meta = {}
            yield CostRecord(
                model=r["model"],
                prompt_tokens=int(r["prompt_tokens"]),
                completion_tokens=int(r["completion_tokens"]),
                cost_usd=float(r["cost_usd"]),
                timestamp=float(r["timestamp"]),
                session_id=r["session_id"],
                metadata=meta,
            )


# ---------------------------------------------------------------------------
# Modül-seviyesi singleton + kolaylık fonksiyonları
# ---------------------------------------------------------------------------
_singleton: CostTracker | None = None
_singleton_lock = threading.Lock()


def _get_tracker() -> CostTracker:
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = CostTracker()
    return _singleton


def set_db_path(path: str | Path) -> None:
    """Singleton tracker'ı yeniden oluşturur ve DB yolunu ayarlar."""
    global _singleton
    with _singleton_lock:
        _singleton = CostTracker(db_path=path)


def set_price_table(table: dict[str, dict[str, float]]) -> None:
    """Singleton tracker için fiyat tablosunu günceller."""
    _get_tracker()._price_table = table


def record_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    *,
    provider: str = "",
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> CostRecord:
    """Global tracker üzerinden kullanım kaydı ekler."""
    return _get_tracker().record(
        model,
        prompt_tokens,
        completion_tokens,
        provider=provider,
        session_id=session_id,
        metadata=metadata,
    )


def summary(**filters: Any) -> dict[str, Any]:
    """Global tracker üzerinden özet rapor."""
    return _get_tracker().summary(**filters)


def dump_log(**filters: Any) -> list[dict[str, Any]]:
    """Global tracker üzerinden ham kayıtlar."""
    return _get_tracker().dump_log(**filters)


def reset() -> int:
    """Global tracker kayıtlarını temizler."""
    return _get_tracker().reset()