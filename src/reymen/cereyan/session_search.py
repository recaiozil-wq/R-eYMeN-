# -*- coding: utf-8 -*-
"""session_search.py — FTS5 tabanli session mesaji arama motoru.

Her mesaji SQLite FTS5'e kaydeder, tam metin aramasi yapar.
Bagimsiz calisir (session_db.py'den ayri, hizli arama icin).

Kullanim:
    searcher = SessionSearch()
    searcher.save("session-001", "merhaba dunya", "user")
    sonuclar = searcher.search("merhaba")
"""

import logging
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Varsayilan DB yolu — reymen/hafiza/ altinda
_DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent / "hafiza"
_DEFAULT_DB_PATH = str(_DEFAULT_DB_DIR / "session_search.db")


class SessionSearch:
    """FTS5 tabanli session mesaji arama motoru.

    Attributes:
        db_yolu: SQLite dosya yolu.
        _lock: Thread guvenligi icin lock.
    """

    def __init__(self, db_yolo: Optional[str] = None):
        self.db_yolu = db_yolo or _DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_yolu) or ".", exist_ok=True)
        self._lock = threading.Lock()
        self._kur()

    # ── Baglanti ──────────────────────────────────────────────────────

    def _baglan(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_yolu, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    # ── Sema Kurulumu ─────────────────────────────────────────────────

    def _kur(self):
        """FTS5 tablosunu olustur (idempotent)."""
        with self._lock:
            conn = self._baglan()
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS session_messages_fts
                    USING fts5(
                        session_id UNINDEXED,
                        message,
                        role UNINDEXED,
                        timestamp UNINDEXED,
                        tokenize='porter unicode61'
                    )
                """)
                conn.commit()
                logger.info("SessionSearch FTS5 tablosu hazir: %s", self.db_yolu)
            except Exception as e:
                logger.error("SessionSearch _kur hatasi: %s", e)
            finally:
                conn.close()

    # ── Kaydet (Save) ─────────────────────────────────────────────────

    def save(self, session_id: str, message: str, role: str = "user") -> bool:
        """Bir mesaji FTS5 tablosuna kaydet.

        Args:
            session_id: Oturum ID.
            message: Mesaj icerigi.
            role: Mesaj rolu (user/assistant/tool/system).

        Returns:
            Basarili ise True.
        """
        if not message or not message.strip():
            return False

        timestamp = time.time()
        with self._lock:
            conn = self._baglan()
            try:
                conn.execute(
                    "INSERT INTO session_messages_fts (session_id, message, role, timestamp) "
                    "VALUES (?, ?, ?, ?)",
                    (session_id, message.strip(), role, timestamp),
                )
                conn.commit()
                logger.debug("SessionSearch kaydedildi: session=%s role=%s msg=%.40s",
                             session_id, role, message)
                return True
            except Exception as e:
                logger.error("SessionSearch save hatasi: %s", e)
                return False
            finally:
                conn.close()

    # ── Ara (Search) ──────────────────────────────────────────────────

    def search(self, query: str, limit: int = 10, session_id: Optional[str] = None) -> List[Dict]:
        """FTS5 ile tam metin aramasi yap.

        Args:
            query: Aranacak kelime/ifade. FTS5 sorgu syntax'i desteklenir:
                   "kelime1 kelime2" -> AND, "kelime1 OR kelime2" -> OR,
                   "kelime*" -> prefix, "\"tam ifade\"" -> exact.
            limit: Maks sonuc sayisi.
            session_id: Opsiyonel — sadece belirli bir oturumda ara.

        Returns:
            [{"session_id", "message", "role", "timestamp", "rank"}, ...]
        """
        if not query or not query.strip():
            return []

        with self._lock:
            conn = self._baglan()
            try:
                # FTS5 sorgu guvenligi: kullanici girdisini temizle
                temiz_sorgu = self._sorgu_temizle(query)

                if session_id:
                    rows = conn.execute(
                        "SELECT session_id, message, role, timestamp, rank "
                        "FROM session_messages_fts "
                        "WHERE session_messages_fts MATCH ? AND session_id = ? "
                        "ORDER BY rank "
                        "LIMIT ?",
                        (temiz_sorgu, session_id, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT session_id, message, role, timestamp, rank "
                        "FROM session_messages_fts "
                        "WHERE session_messages_fts MATCH ? "
                        "ORDER BY rank "
                        "LIMIT ?",
                        (temiz_sorgu, limit),
                    ).fetchall()

                sonuclar = []
                for r in rows:
                    sonuclar.append({
                        "session_id": r["session_id"],
                        "message": r["message"],
                        "role": r["role"],
                        "timestamp": r["timestamp"],
                        "rank": r["rank"],
                    })
                logger.debug("SessionSearch: '%s' -> %d sonuc", query, len(sonuclar))
                return sonuclar
            except Exception as e:
                logger.error("SessionSearch search hatasi: %s", e)
                return []
            finally:
                conn.close()

    # ── Session Mesajlarini Listele ───────────────────────────────────

    def session_mesajlari(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Belirli bir session'in tum mesajlarini getir.

        Args:
            session_id: Oturum ID.
            limit: Maks sonuc sayisi.

        Returns:
            [{"session_id", "message", "role", "timestamp"}, ...]
        """
        with self._lock:
            conn = self._baglan()
            try:
                rows = conn.execute(
                    "SELECT session_id, message, role, timestamp "
                    "FROM session_messages_fts "
                    "WHERE session_id = ? "
                    "ORDER BY timestamp ASC "
                    "LIMIT ?",
                    (session_id, limit),
                ).fetchall()
                return [dict(r) for r in rows]
            except Exception as e:
                logger.error("SessionSearch session_mesajlari hatasi: %s", e)
                return []
            finally:
                conn.close()

    # ── Istatistik ────────────────────────────────────────────────────

    def istatistik(self) -> Dict:
        """Toplam kayit sayisi ve diger istatistikler."""
        with self._lock:
            conn = self._baglan()
            try:
                satir = conn.execute(
                    "SELECT COUNT(*) as toplam FROM session_messages_fts"
                ).fetchone()
                session_sayisi = conn.execute(
                    "SELECT COUNT(DISTINCT session_id) as sayi FROM session_messages_fts"
                ).fetchone()
                return {
                    "toplam_mesaj": satir["toplam"] if satir else 0,
                    "toplam_session": session_sayisi["sayi"] if session_sayisi else 0,
                    "db_yolu": self.db_yolu,
                }
            except Exception as e:
                logger.error("SessionSearch istatistik hatasi: %s", e)
                return {"hata": str(e)}
            finally:
                conn.close()

    # ── Yardimci ──────────────────────────────────────────────────────

    @staticmethod
    def _sorgu_temizle(sorgu: str) -> str:
        """FTS5 sorgusunu temizle: tehlikeli karakterleri kaldir."""
        # FTS5 ozel karakterleri: ^ * " ( ) ~ + - AND OR NEAR NOT
        # Basit guvenlik: cift tirnak icinde olmayan ozel karakterleri kaldir
        import re as _re
        # Cift tirnak icindeki ifadeleri koru
        # Geri kalan ozel karakterleri temizle
        temiz = _re.sub(r'[^\w\s"*()~+\-]', ' ', sorgu)
        # Birden fazla boslugu tek bosluk yap
        temiz = _re.sub(r'\s+', ' ', temiz).strip()
        return temiz if temiz else sorgu


# ── Singleton / Module-level instance ────────────────────────────────

_session_search_instance: Optional[SessionSearch] = None
_session_search_lock = threading.Lock()


def session_search_al(db_yolu: Optional[str] = None) -> SessionSearch:
    """Singleton SessionSearch instance'i al (thread-safe)."""
    global _session_search_instance
    if _session_search_instance is None:
        with _session_search_lock:
            if _session_search_instance is None:
                _session_search_instance = SessionSearch(db_yolu)
    return _session_search_instance


# ── Kolay Kullanim Fonksiyonlari (dogrudan import icin) ─────────────

def save(session_id: str, message: str, role: str = "user") -> bool:
    """Kolay kaydet — singleton uzerinden."""
    return session_search_al().save(session_id, message, role)


def search(query: str, limit: int = 10, session_id: Optional[str] = None) -> List[Dict]:
    """Kolay ara — singleton uzerinden."""
    return session_search_al().search(query, limit=limit, session_id=session_id)
