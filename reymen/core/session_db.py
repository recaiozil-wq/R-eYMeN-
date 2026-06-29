# -*- coding: utf-8 -*-
"""
session_db.py — Session DB (FTS5 + trigram arama).

CRUD:
  - session_olustur()        — Yeni session olustur (idempotent)
  - mesaj_ekle()             — Session'a mesaj ekle (FTS5 index ile)
  - mesaj_ara(sorgu, limit)  — FTS5 + trigram ile mesaj icinde ara
  - session_getir()          — Session ve mesajlarini getir
  - session_listele()        — Tum session'lari listele

Mevcut .ReYMeN/session.db kullanir (Alembic ile uyumlu).
Schema Manager ile upsert() kullanarak idempotent CREATE yapar.

Motor tool:
  - SESSION_ARA:   FTS5 + trigram ile mesajlarda arama
  - SESSION_GETIR: Session detay + mesaj listesi
  - SESSION_LISTE: Tum session'lari listele
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Sabitler ─────────────────────────────────────────────────────────
PROJE_KOKU = Path(__file__).resolve().parent.parent.parent  # reymen/core/ → projekt
DB_YOLU = PROJE_KOKU / ".ReYMeN" / "session.db"


# ═══════════════════════════════════════════════════════════════════════
#  Baglanti Yoneticisi
# ═══════════════════════════════════════════════════════════════════════

def _baglan(db_yol: Optional[Path] = None) -> sqlite3.Connection:
    """SQLite baglantisi ac — WAL modu + synchronous NORMAL."""
    yol = db_yol or DB_YOLU
    yol.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(yol), timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.row_factory = sqlite3.Row
    return con


def _idempotent_tablolar(con: sqlite3.Connection) -> None:
    """FTS5 + trigram virtual tablolarini idempotent olustur.

    Mevcut schema ile uyumlu: sessions, session_messages tablolari
    zaten varsa dokunma. Sadece FTS5 index'lerini kontrol et.
    """
    # External content FTS5 — session_messages uzerinde
    con.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS session_messages_fts
        USING fts5(
            session_id UNINDEXED,
            rol UNINDEXED,
            icerik,
            content='session_messages',
            content_rowid='id'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS session_messages_trigram
        USING fts5(
            icerik,
            tokenize='trigram'
        );
    """)
    con.commit()


def _sync_fts5(con: sqlite3.Connection) -> int:
    """External content FTS5 index'ini rebuild et (rebuild after bulk insert)."""
    try:
        con.execute("INSERT INTO session_messages_fts(session_messages_fts) VALUES('rebuild')")
        return 1
    except Exception as e:
        logger.warning("[SessionDB] FTS5 rebuild skipped: %s", e)
        return 0


# ═══════════════════════════════════════════════════════════════════════
#  CRUD — Session Islemleri
# ═══════════════════════════════════════════════════════════════════════

def session_olustur(
    source: str = "manual",
    user_id: Optional[str] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    title: Optional[str] = None,
    parent_session_id: Optional[str] = None,
    db_yol: Optional[Path] = None,
) -> dict[str, Any]:
    """Yeni session olustur (idempotent — ayni id ile tekrar cagrilirsa gunceller).

    Returns:
        Session bilgisi dict (id, source, user_id, ...)
    """
    con = _baglan(db_yol)
    try:
        _idempotent_tablolar(con)
        session_id = str(uuid.uuid4())
        now = time.time()

        con.execute(
            """INSERT OR IGNORE INTO sessions
               (id, source, user_id, model, system_prompt, title,
                parent_session_id, started_at, message_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (session_id, source, user_id, model, system_prompt, title,
             parent_session_id, now),
        )
        con.commit()

        satir = con.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(satir) if satir else {"id": session_id, "durum": "olusturuldu"}
    except Exception as e:
        logger.error("[SessionDB] session_olustur hatasi: %s", e)
        return {"hata": str(e)}
    finally:
        con.close()


def session_getir(
    session_id: str,
    mesaj_limit: int = 100,
    db_yol: Optional[Path] = None,
) -> dict[str, Any]:
    """Session ve mesajlarini getir.

    Args:
        session_id: Session ID
        mesaj_limit: Getirilecek maks mesaj sayisi

    Returns:
        {"session": {...}, "mesajlar": [...]}
    """
    con = _baglan(db_yol)
    try:
        satir = con.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not satir:
            return {"hata": f"Session bulunamadi: {session_id}"}

        mesajlar = con.execute(
            """SELECT id, session_id, rol, icerik, created_at
               FROM session_messages
               WHERE session_id = ?
               ORDER BY created_at ASC
               LIMIT ?""",
            (session_id, mesaj_limit),
        ).fetchall()

        return {
            "session": dict(satir),
            "mesajlar": [dict(m) for m in mesajlar],
            "mesaj_sayisi": len(mesajlar),
        }
    except Exception as e:
        logger.error("[SessionDB] session_getir hatasi: %s", e)
        return {"hata": str(e)}
    finally:
        con.close()


def session_listele(
    limit: int = 20,
    offset: int = 0,
    source: Optional[str] = None,
    db_yol: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """Session'lari listele (en yeni -> en eski).

    Args:
        limit: Maks session sayisi
        offset: Atlanacak kayit sayisi (sayfalama)
        source: Filtre (opsiyonel)

    Returns:
        Session listesi
    """
    con = _baglan(db_yol)
    try:
        if source:
            satirlar = con.execute(
                """SELECT id, source, user_id, model, title,
                          started_at, ended_at, message_count
                   FROM sessions
                   WHERE source = ?
                   ORDER BY started_at DESC
                   LIMIT ? OFFSET ?""",
                (source, limit, offset),
            ).fetchall()
        else:
            satirlar = con.execute(
                """SELECT id, source, user_id, model, title,
                          started_at, ended_at, message_count
                   FROM sessions
                   ORDER BY started_at DESC
                   LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()

        return [dict(s) for s in satirlar]
    except Exception as e:
        logger.error("[SessionDB] session_listele hatasi: %s", e)
        return []
    finally:
        con.close()


# ═══════════════════════════════════════════════════════════════════════
#  CRUD — Mesaj Islemleri
# ═══════════════════════════════════════════════════════════════════════

def mesaj_ekle(
    session_id: str,
    rol: str,
    icerik: str,
    db_yol: Optional[Path] = None,
) -> dict[str, Any]:
    """Session'a mesaj ekle + FTS5 index'i otomatik guncelle.

    Not: External content FTS5 oldugu icin session_messages'a INSERT
    otomatik olarak session_messages_fts'de gorunur. Trigram tablosu
    ayri bir INSERT gerektirir.

    Args:
        session_id: Session ID
        rol: 'user', 'assistant', 'system'
        icerik: Mesaj icerigi

    Returns:
        {"id": mesaj_id, "basarili": True}
    """
    con = _baglan(db_yol)
    try:
        _idempotent_tablolar(con)
        now = time.time()

        # Session var mi kontrol et
        session_var = con.execute(
            "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not session_var:
            return {"hata": f"Session bulunamadi: {session_id}"}

        # Mesaj ekle
        cur = con.execute(
            """INSERT INTO session_messages (session_id, rol, icerik, created_at)
               VALUES (?, ?, ?, ?)""",
            (session_id, rol, icerik, now),
        )
        mesaj_id = cur.lastrowid

        # Trigram index'ine de ekle
        try:
            con.execute(
                """INSERT INTO session_messages_trigram (icerik)
                   VALUES (?)""",
                (icerik,),
            )
        except Exception as trig_err:
            logger.debug("[SessionDB] Trigram ekleme (opsiyonel) atlandi: %s", trig_err)

        # Session message_count guncelle
        con.execute(
            """UPDATE sessions SET message_count = message_count + 1
               WHERE id = ?""",
            (session_id,),
        )

        con.commit()
        return {"id": mesaj_id, "session_id": session_id, "basarili": True}
    except Exception as e:
        logger.error("[SessionDB] mesaj_ekle hatasi: %s", e)
        return {"hata": str(e)}
    finally:
        con.close()


def mesaj_ara(
    sorgu: str,
    limit: int = 10,
    session_id: Optional[str] = None,
    trigram_agirlik: float = 0.3,
    db_yol: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """FTS5 + trigram ile mesaj icinde ara.

    Iki ayri index'te arama yapar:
      1. session_messages_fts (standart FTS5 — kelime bazli)
      2. session_messages_trigram (trigram — karakter bazli, Turkce destegi)

    Sonuclari birlestirir, relevans skoru ile siralar.

    Args:
        sorgu: Arama sorgusu
        limit: Maks sonuc sayisi
        session_id: Opsiyonel session filtresi
        trigram_agirlik: Trigram skorunun agirligi (0-1 arasi)
        db_yol: Opsiyonel DB yolu

    Returns:
        [{"id": ..., "session_id": ..., "rol": ..., "icerik": ..., "skor": ...}]
    """
    con = _baglan(db_yol)
    try:
        # 1. FTS5 ile ara (standart)
        fts5_sonuclar = _fts5_ara(con, sorgu, limit, session_id)

        # 2. Trigram ile ara (Turkce karakter / yanlis yazim)
        trigram_sonuclar = _trigram_ara(con, sorgu, limit, session_id)

        # Birlestir — ayni id'leri birlestir, skor ortalamasi al
        skor_map: dict[int, dict] = {}
        for m in fts5_sonuclar:
            mid = m["id"]
            skor_map[mid] = m
            skor_map[mid]["skor"] = skor_map[mid].get("skor", 0)

        for m in trigram_sonuclar:
            mid = m["id"]
            if mid in skor_map:
                # Her iki index'te de var — skor ortalamasi
                onceki_skor = skor_map[mid].get("skor", 0)
                skor_map[mid]["skor"] = (
                    onceki_skor * (1 - trigram_agirlik)
                    + m.get("skor", 0) * trigram_agirlik
                )
            else:
                skor_map[mid] = m
                skor_map[mid]["skor"] = m.get("skor", 0) * trigram_agirlik

        # Skor'a gore sirala, limit uygula
        sonuc = sorted(skor_map.values(), key=lambda x: x.get("skor", 0), reverse=True)
        return sonuc[:limit]

    except Exception as e:
        logger.error("[SessionDB] mesaj_ara hatasi: %s", e)
        return []
    finally:
        con.close()


def _fts5_ara(
    con: sqlite3.Connection,
    sorgu: str,
    limit: int,
    session_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """FTS5 index'inde ara (standart tokenizer)."""
    try:
        # Sorguyu FTS5 uyumlu hale getir (ornek: "merhaba dunya" -> "merhaba* dunya*")
        fts_sorgu = " OR ".join(
            f'"{k}' for k in sorgu.split() if k.strip()
        ) or sorgu

        if session_id:
            satirlar = con.execute(
                """SELECT m.id, m.session_id, m.rol, m.icerik,
                          rank as skor
                   FROM session_messages_fts
                   JOIN session_messages m ON m.id = session_messages_fts.rowid
                   WHERE session_messages_fts MATCH ? AND m.session_id = ?
                   ORDER BY rank
                   LIMIT ?""",
                (fts_sorgu, session_id, limit),
            ).fetchall()
        else:
            satirlar = con.execute(
                """SELECT m.id, m.session_id, m.rol, m.icerik,
                          rank as skor
                   FROM session_messages_fts
                   JOIN session_messages m ON m.id = session_messages_fts.rowid
                   WHERE session_messages_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (fts_sorgu, limit),
            ).fetchall()

        return [dict(r) for r in satirlar]
    except Exception as e:
        logger.debug("[SessionDB] FTS5 arama (fallback): %s", e)
        # FTS5 hatasinda LIKE ile fallback
        return _like_fallback_ara(con, sorgu, limit, session_id)


def _trigram_ara(
    con: sqlite3.Connection,
    sorgu: str,
    limit: int,
    session_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Trigram FTS5 index'inde ara (karakter bazli, Turkce destegi)."""
    try:
        # Trigram icin sorguyu hazirla
        trigram_sorgu = f'"{sorgu}"'

        if session_id:
            satirlar = con.execute(
                """SELECT m.id, m.session_id, m.rol, m.icerik,
                          rank as skor
                   FROM session_messages_trigram
                   JOIN session_messages m ON m.id = session_messages_trigram.rowid
                   WHERE session_messages_trigram MATCH ? AND m.session_id = ?
                   ORDER BY rank
                   LIMIT ?""",
                (trigram_sorgu, session_id, limit),
            ).fetchall()
        else:
            satirlar = con.execute(
                """SELECT m.id, m.session_id, m.rol, m.icerik,
                          rank as skor
                   FROM session_messages_trigram
                   JOIN session_messages m ON m.id = session_messages_trigram.rowid
                   WHERE session_messages_trigram MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (trigram_sorgu, limit),
            ).fetchall()

        return [dict(r) for r in satirlar]
    except Exception as e:
        logger.debug("[SessionDB] Trigram arama (atlandi): %s", e)
        return []


def _like_fallback_ara(
    con: sqlite3.Connection,
    sorgu: str,
    limit: int,
    session_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """LIKE ile fallback arama (FTS5 hata verdiginde)."""
    like_pattern = f"%{sorgu}%"

    if session_id:
        satirlar = con.execute(
            """SELECT id, session_id, rol, icerik, 0.0 as skor
               FROM session_messages
               WHERE session_id = ? AND icerik LIKE ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (session_id, like_pattern, limit),
        ).fetchall()
    else:
        satirlar = con.execute(
            """SELECT id, session_id, rol, icerik, 0.0 as skor
               FROM session_messages
               WHERE icerik LIKE ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (like_pattern, limit),
        ).fetchall()

    return [dict(r) for r in satirlar]


# ═══════════════════════════════════════════════════════════════════════
#  Schema Manager uyumlulugu (upsert ile idempotent CREATE)
# ═══════════════════════════════════════════════════════════════════════

def tablolari_kaydet(schema_manager: Any) -> dict:
    """Schema Manager uzerinden tablolari kaydet (idempotent).

    Args:
        schema_manager: SchemaManager ornegi (reymen.core.schema_manager)

    Returns:
        {"durum": "ok", "tablolar": [...]}
    """
    from reymen.core.schema_manager import Migration

    tablo_sqls = [
        """CREATE TABLE IF NOT EXISTS sessions (
            id                TEXT PRIMARY KEY,
            source            TEXT NOT NULL,
            user_id           TEXT,
            model             TEXT,
            model_config      TEXT,
            system_prompt     TEXT,
            parent_session_id TEXT,
            started_at        REAL NOT NULL,
            ended_at          REAL,
            end_reason        TEXT,
            message_count     INTEGER DEFAULT 0,
            tool_call_count   INTEGER DEFAULT 0,
            input_tokens      INTEGER DEFAULT 0,
            output_tokens     INTEGER DEFAULT 0,
            cache_read_tokens  INTEGER DEFAULT 0,
            cache_write_tokens INTEGER DEFAULT 0,
            reasoning_tokens  INTEGER DEFAULT 0,
            billing_provider  TEXT,
            billing_base_url  TEXT,
            billing_mode      TEXT,
            estimated_cost_usd REAL,
            actual_cost_usd   REAL,
            cost_status       TEXT,
            cost_source       TEXT,
            pricing_version   TEXT,
            title             TEXT,
            api_call_count    INTEGER DEFAULT 0,
            FOREIGN KEY (parent_session_id) REFERENCES sessions(id)
        )""",
        """CREATE TABLE IF NOT EXISTS session_messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            rol        TEXT NOT NULL,
            icerik     TEXT,
            created_at REAL NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )""",
        """CREATE TABLE IF NOT EXISTS session_tool_calls (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            tool_name   TEXT NOT NULL,
            args        TEXT,
            result      TEXT,
            duration_ms INTEGER,
            created_at  REAL NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )""",
    ]

    return schema_manager.kaydet(
        db_yol=str(DB_YOLU),
        tablolar=tablo_sqls,
        version=1,
        migrations=[
            Migration(
                version=1,
                ad="session_db_initial",
                sql="""
                    CREATE VIRTUAL TABLE IF NOT EXISTS session_messages_fts
                    USING fts5(
                        session_id UNINDEXED,
                        rol UNINDEXED,
                        icerik,
                        content='session_messages',
                        content_rowid='id'
                    );
                    CREATE VIRTUAL TABLE IF NOT EXISTS session_messages_trigram
                    USING fts5(
                        icerik,
                        tokenize='trigram'
                    );
                """,
            ),
        ],
    )


# ═══════════════════════════════════════════════════════════════════════
#  Motor Tool'lari
# ═══════════════════════════════════════════════════════════════════════

def _session_ara(sorgu: str = "", session_id: str = "", limit: int = 10) -> str:
    """Motor tool: FTS5 + trigram ile session mesajlarinda ara.

    Kullanim:
        SESSION_ARA(sorgu="merhaba", limit=5)
        SESSION_ARA(sorgu="test", session_id="uuid", limit=10)

    Args:
        sorgu: Arama sorgusu (bos olursa ornek gosterir)
        session_id: Opsiyonel session filtresi
        limit: Maks sonuc sayisi

    Returns:
        JSON formatinda sonuc listesi
    """
    if not sorgu:
        return ("Kullanim: SESSION_ARA(sorgu=\"aranan metin\", "
                "session_id=\"opsiyonel-session-uuid\", limit=10)\n"
                "Ornek: SESSION_ARA(sorgu=\"hava\")")

    sid = session_id if session_id else None
    sonuclar = mesaj_ara(sorgu, limit=min(limit, 50), session_id=sid)

    if not sonuclar:
        return f'[] — "{sorgu}" icin sonuc bulunamadi'

    return json.dumps(sonuclar, indent=2, ensure_ascii=False, default=str)


def _session_getir(session_id: str = "") -> str:
    """Motor tool: Session detay + mesaj listesi getir.

    Kullanim:
        SESSION_GETIR(session_id="uuid")

    Args:
        session_id: Session ID

    Returns:
        JSON formatinda session + mesajlar
    """
    if not session_id:
        return ("Kullanim: SESSION_GETIR(session_id=\"session-uuid\")\n"
                "Ornek: SESSION_GETIR(session_id=\"81967189-fd1d-4c64-8877-af2986a1e0c9\")")

    sonuc = session_getir(session_id, mesaj_limit=50)
    return json.dumps(sonuc, indent=2, ensure_ascii=False, default=str)


def _session_liste(limit: int = 10, source: str = "") -> str:
    """Motor tool: Session'lari listele.

    Kullanim:
        SESSION_LISTE(limit=10)
        SESSION_LISTE(source="telegram", limit=5)

    Args:
        limit: Maks session sayisi
        source: Opsiyonel kaynak filtresi

    Returns:
        JSON formatinda session listesi
    """
    src = source if source else None
    sonuclar = session_listele(limit=min(limit, 50), source=src)

    if not sonuclar:
        return "[] — hic session bulunamadi"

    return json.dumps(sonuclar, indent=2, ensure_ascii=False, default=str)


# ── Motor Kayit ─────────────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    """Motor'a session DB araçlarını kaydeder."""
    motor._plugin_arac_kaydet(
        "SESSION_ARA",
        _session_ara,
        "FTS5 + trigram ile session mesajlarinda ara. "
        "Parametreler: sorgu (str), session_id (str, opsiyonel), limit (int). "
        "Turkce karakter ve yanlis yazim destegi ile arama yapar.",
    )
    motor._plugin_arac_kaydet(
        "SESSION_GETIR",
        _session_getir,
        "Session detay + mesaj listesi getir. "
        "Parametre: session_id (str, zorunlu).",
    )
    motor._plugin_arac_kaydet(
        "SESSION_LISTE",
        _session_liste,
        "Session'lari listele (en yeni -> en eski). "
        "Parametreler: limit (int, varsayilan 10), source (str, opsiyonel filtre).",
    )
    logger.info("[SessionDB] Motor araclari kaydedildi: SESSION_ARA, SESSION_GETIR, SESSION_LISTE")
