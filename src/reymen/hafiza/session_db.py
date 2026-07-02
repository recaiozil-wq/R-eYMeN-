# -*- coding: utf-8 -*-
"""
session_db.py — AdvancedSessionStorage. SQLite WAL + FTS5 ajan günlüğü
+ ReYMeN Agent seviyesi sessions tablosu (~30 sutun).

Geriye uyumluluk: FTS5 ajan_gunlugu tablosu korunur.
Yeni: sessions tablosu, token/maliyet/parent-session takibi.
"""
import json
import logging
import os
import re
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
import logging
logger = logging.getLogger(__name__)

log = logging.getLogger(__name__)


class AdvancedSessionStorage:
    """SQLite tabanli session ve ajan günlüğü deposu.

    Kullanim:
        storage = AdvancedSessionStorage("merkez_db/session.db")
        sid = storage.session_baslat(source="cli", model="deepseek")
        storage.token_guncelle(sid, input_tokens=450, output_tokens=120)
        storage.session_bitir(sid, end_reason="completed")
    """

    def __init__(self, db_yolu="merkez_db/session.db"):
        self.db_yolu = db_yolu
        os.makedirs(os.path.dirname(db_yolu) or ".", exist_ok=True)
        self._lock = threading.Lock()
        self._kur()

    # ── Bağlantı ──────────────────────────────────────────────────────

    def _baglan(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_yolu, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    # ── Şema kurulumu ─────────────────────────────────────────────────

    def _kur(self):
        with self._lock:
            conn = self._baglan()
            try:
                # ReYMeN Agent seviyesi sessions tablosu
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
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
                    )
                """)

                # İndeksler
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sessions_source "
                    "ON sessions(source)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sessions_parent "
                    "ON sessions(parent_session_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sessions_started "
                    "ON sessions(started_at DESC)"
                )
                conn.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_title_unique "
                    "ON sessions(title) WHERE title IS NOT NULL"
                )

                # Mesaj geçmişi tablosu
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS session_messages (
                        id         INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        rol        TEXT NOT NULL,
                        icerik     TEXT,
                        created_at REAL NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES sessions(id)
                    )
                """)

                # Tool call geçmişi tablosu
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS session_tool_calls (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id  TEXT NOT NULL,
                        tool_name   TEXT NOT NULL,
                        args        TEXT,
                        result      TEXT,
                        duration_ms INTEGER,
                        created_at  REAL NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES sessions(id)
                    )
                """)

                # Geriye uyumluluk: FTS5 ajan_gunlugu (standart tokenizer)
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS ajan_gunlugu USING fts5(
                        hedef,
                        eylem,
                        sonuc
                    )
                """)

                # FTS5 trigram: kismi kelime / substring arama (SQLite >= 3.34)
                try:
                    conn.execute("""
                        CREATE VIRTUAL TABLE IF NOT EXISTS ajan_gunlugu_trigram USING fts5(
                            hedef,
                            eylem,
                            sonuc,
                            tokenize='trigram'
                        )
                    """)
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )  # Eski SQLite versiyonlari trigram desteklemez

                # Session mesajlari FTS5 (icerik arama icin)
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS session_messages_fts USING fts5(
                        session_id UNINDEXED,
                        rol UNINDEXED,
                        icerik,
                        content='session_messages',
                        content_rowid='id'
                    )
                """)

                # Trigram variant (partial search)
                try:
                    conn.execute("""
                        CREATE VIRTUAL TABLE IF NOT EXISTS session_messages_trigram USING fts5(
                            icerik,
                            tokenize='trigram'
                        )
                    """)
                except Exception as _session__e170:
                    print(f"[UYARI] session_db.py:171 - {_session__e170}")

                conn.commit()
                log.info("session_db sema kuruldu: %s", self.db_yolu)
            except Exception as e:
                log.error("_kur hatasi: %s", e)
            finally:
                conn.close()

    # ── Session işlemleri ─────────────────────────────────────────────

    def session_baslat(
        self,
        source: str,
        user_id: str = None,
        model: str = None,
        model_config: dict = None,
        system_prompt: str = None,
        parent_session_id: str = None,
        title: str = None,
        billing_provider: str = None,
        billing_base_url: str = None,
        billing_mode: str = None,
    ) -> str:
        """Yeni session ac, session_id dondur."""
        sid = str(uuid.uuid4())
        now = time.time()
        mc_json = json.dumps(model_config, ensure_ascii=False) if model_config else None

        with self._lock:
            conn = self._baglan()
            try:
                conn.execute(
                    """
                    INSERT INTO sessions (
                        id, source, user_id, model, model_config, system_prompt,
                        parent_session_id, started_at, title,
                        billing_provider, billing_base_url, billing_mode
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        sid, source, user_id, model, mc_json, system_prompt,
                        parent_session_id, now, title,
                        billing_provider, billing_base_url, billing_mode,
                    ),
                )
                conn.commit()
                log.info("session_baslat: %s (source=%s, model=%s)", sid, source, model)
            except Exception as e:
                log.error("session_baslat hatasi: %s", e)
            finally:
                conn.close()
        return sid

    def session_bitir(self, session_id: str, end_reason: str = None):
        """Session'i kapat; ended_at ve end_reason ayarla."""
        with self._lock:
            conn = self._baglan()
            try:
                conn.execute(
                    "UPDATE sessions SET ended_at=?, end_reason=? WHERE id=?",
                    (time.time(), end_reason, session_id),
                )
                conn.commit()
                log.info("session_bitir: %s (neden=%s)", session_id, end_reason)
            except Exception as e:
                log.error("session_bitir hatasi: %s", e)
            finally:
                conn.close()

    def mesaj_ekle(self, session_id: str, rol: str, icerik: str):
        """Session'a mesaj ekle; message_count artir. FTS tablolarini da guncelle."""
        with self._lock:
            conn = self._baglan()
            try:
                cur = conn.execute(
                    "INSERT INTO session_messages (session_id, rol, icerik, created_at) "
                    "VALUES (?,?,?,?)",
                    (session_id, rol, icerik, time.time()),
                )
                rowid = cur.lastrowid
                conn.execute(
                    "UPDATE sessions SET message_count = message_count + 1 WHERE id=?",
                    (session_id,),
                )
                # FTS content table — rowid eslestirmesi ile
                try:
                    conn.execute(
                        "INSERT INTO session_messages_fts(rowid, session_id, rol, icerik) "
                        "VALUES (?,?,?,?)",
                        (rowid, session_id, rol, icerik),
                    )
                except Exception as _session__e263:
                    print(f"[UYARI] session_db.py:264 - {_session__e263}")
                # Trigram FTS
                try:
                    conn.execute(
                        "INSERT INTO session_messages_trigram(icerik) VALUES (?)",
                        (icerik,),
                    )
                except Exception as _session__e271:
                    print(f"[UYARI] session_db.py:272 - {_session__e271}")
                conn.commit()
                log.debug("mesaj_ekle: session=%s rol=%s", session_id, rol)
            except Exception as e:
                log.error("mesaj_ekle hatasi: %s", e)
            finally:
                conn.close()

    def tool_call_kaydet(
        self,
        session_id: str,
        tool_name: str,
        args: dict,
        result: str,
        duration_ms: int = 0,
    ):
        """Tool call'u kaydet; tool_call_count + api_call_count artir."""
        args_json = json.dumps(args, ensure_ascii=False) if isinstance(args, dict) else str(args)
        with self._lock:
            conn = self._baglan()
            try:
                conn.execute(
                    """
                    INSERT INTO session_tool_calls
                        (session_id, tool_name, args, result, duration_ms, created_at)
                    VALUES (?,?,?,?,?,?)
                    """,
                    (session_id, tool_name, args_json, result, duration_ms, time.time()),
                )
                conn.execute(
                    """
                    UPDATE sessions
                    SET tool_call_count = tool_call_count + 1,
                        api_call_count  = api_call_count  + 1
                    WHERE id=?
                    """,
                    (session_id,),
                )
                conn.commit()
                log.debug("tool_call_kaydet: session=%s tool=%s", session_id, tool_name)
            except Exception as e:
                log.error("tool_call_kaydet hatasi: %s", e)
            finally:
                conn.close()

    def token_guncelle(
        self,
        session_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        reasoning_tokens: int = 0,
    ):
        """Token sayaçlarını artır (kümülatif)."""
        with self._lock:
            conn = self._baglan()
            try:
                conn.execute(
                    """
                    UPDATE sessions SET
                        input_tokens        = input_tokens        + ?,
                        output_tokens       = output_tokens       + ?,
                        cache_read_tokens   = cache_read_tokens   + ?,
                        cache_write_tokens  = cache_write_tokens  + ?,
                        reasoning_tokens    = reasoning_tokens    + ?
                    WHERE id=?
                    """,
                    (
                        input_tokens, output_tokens,
                        cache_read_tokens, cache_write_tokens,
                        reasoning_tokens, session_id,
                    ),
                )
                conn.commit()
                log.debug(
                    "token_guncelle: session=%s in=%d out=%d",
                    session_id, input_tokens, output_tokens,
                )
            except Exception as e:
                log.error("token_guncelle hatasi: %s", e)
            finally:
                conn.close()

    def maliyet_guncelle(
        self,
        session_id: str,
        estimated_cost: float = None,
        actual_cost: float = None,
        cost_status: str = None,
        cost_source: str = None,
        pricing_version: str = None,
    ):
        """Maliyet bilgilerini güncelle."""
        with self._lock:
            conn = self._baglan()
            try:
                conn.execute(
                    """
                    UPDATE sessions SET
                        estimated_cost_usd = COALESCE(?, estimated_cost_usd),
                        actual_cost_usd    = COALESCE(?, actual_cost_usd),
                        cost_status        = COALESCE(?, cost_status),
                        cost_source        = COALESCE(?, cost_source),
                        pricing_version    = COALESCE(?, pricing_version)
                    WHERE id=?
                    """,
                    (
                        estimated_cost, actual_cost,
                        cost_status, cost_source,
                        pricing_version, session_id,
                    ),
                )
                conn.commit()
                log.debug("maliyet_guncelle: session=%s est=%.6f", session_id, estimated_cost or 0)
            except Exception as e:
                log.error("maliyet_guncelle hatasi: %s", e)
            finally:
                conn.close()

    # ── Sorgulama ─────────────────────────────────────────────────────

    def session_bul(self, session_id: str) -> dict:
        """Session'ı id ile bul; bulunamazsa {} döner."""
        with self._lock:
            conn = self._baglan()
            try:
                row = conn.execute(
                    "SELECT * FROM sessions WHERE id=?", (session_id,)
                ).fetchone()
                return dict(row) if row else {}
            except Exception as e:
                log.error("session_bul hatasi: %s", e)
                return {}
            finally:
                conn.close()

    def session_ara(self, sorgu: str, limit: int = 10) -> list:
        """Title veya system_prompt icinde arama yap (FTS5 + LIKE fallback)."""
        with self._lock:
            conn = self._baglan()
            try:
                # FTS5 ile mesaj icerigi ara
                fts_ids = set()
                try:
                    rows_fts = conn.execute(
                        "SELECT DISTINCT session_id FROM session_messages_fts "
                        "WHERE icerik MATCH ? LIMIT ?",
                        (sorgu, limit),
                    ).fetchall()
                    fts_ids = {r[0] for r in rows_fts}
                except Exception as _session__e423:
                    print(f"[UYARI] session_db.py:424 - {_session__e423}")

                if fts_ids:
                    placeholders = ",".join("?" * len(fts_ids))
                    rows = conn.execute(
                        f"SELECT * FROM sessions WHERE id IN ({placeholders}) "
                        f"ORDER BY started_at DESC LIMIT ?",
                        [*fts_ids, limit],
                    ).fetchall()
                else:
                    # Fallback: LIKE ile title/system_prompt
                    rows = conn.execute(
                        "SELECT * FROM sessions "
                        "WHERE title LIKE ? OR system_prompt LIKE ? "
                        "ORDER BY started_at DESC LIMIT ?",
                        (f"%{sorgu}%", f"%{sorgu}%", limit),
                    ).fetchall()
                return [dict(r) for r in rows]
            except Exception as e:
                log.error("session_ara hatasi: %s", e)
                return []
            finally:
                conn.close()

    def mesaj_ara(
        self,
        sorgu: str,
        limit: int = 10,
        kismi: bool = False,
        baslangic_ts: float = None,
        bitis_ts: float = None,
    ) -> list:
        """Session mesajlarinda tam metin veya trigram (kismi) arama.

        Args:
            sorgu:        Aranacak kelime/ifade.
            limit:        Maks sonuc sayisi.
            kismi:        True -> trigram (substring) arama; False -> tam kelime FTS5.
            baslangic_ts: (opsiyonel) Unix epoch — bu zamandan sonraki mesajlar.
            bitis_ts:     (opsiyonel) Unix epoch — bu zamandan once'ki mesajlar.

        Returns:
            [{session_id, rol, icerik, created_at}, ...]
        """
        zaman_kosul = ""
        zaman_args: list = []
        if baslangic_ts is not None:
            zaman_kosul += " AND sm.created_at >= ?"
            zaman_args.append(baslangic_ts)
        if bitis_ts is not None:
            zaman_kosul += " AND sm.created_at <= ?"
            zaman_args.append(bitis_ts)

        with self._lock:
            conn = self._baglan()
            try:
                if kismi:
                    # Trigram substring arama
                    rows = conn.execute(
                        "SELECT sm.session_id, sm.rol, sm.icerik, sm.created_at "
                        "FROM session_messages sm "
                        "JOIN session_messages_trigram t ON sm.rowid = t.rowid "
                        f"WHERE t.icerik MATCH ?{zaman_kosul} "
                        "ORDER BY sm.created_at DESC LIMIT ?",
                        (sorgu, *zaman_args, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT sm.session_id, sm.rol, sm.icerik, sm.created_at "
                        "FROM session_messages_fts fts "
                        "JOIN session_messages sm ON fts.rowid = sm.id "
                        f"WHERE fts.icerik MATCH ?{zaman_kosul} "
                        "ORDER BY sm.created_at DESC LIMIT ?",
                        (sorgu, *zaman_args, limit),
                    ).fetchall()
                return [dict(r) for r in rows]
            except sqlite3.OperationalError:
                # FTS tablosu yoksa LIKE fallback
                try:
                    rows = conn.execute(
                        "SELECT session_id, rol, icerik, created_at "
                        "FROM session_messages sm "
                        f"WHERE icerik LIKE ?{zaman_kosul} "
                        "ORDER BY created_at DESC LIMIT ?",
                        (f"%{sorgu}%", *zaman_args, limit),
                    ).fetchall()
                    return [dict(r) for r in rows]
                except Exception:
                    return []
            except Exception as e:
                log.error("mesaj_ara hatasi: %s", e)
                return []
            finally:
                conn.close()

    @staticmethod
    def _tarih_araligi_coz(tarih_araligi) -> Tuple[Optional[float], Optional[float]]:
        """'tarih_araligi' parametresini (baslangic_ts, bitis_ts) epoch ciftine cevir.

        Desteklenen formatlar:
            None / ""                     -> (None, None) filtre yok
            "7g" / "30g" / "24s"           -> son N gun / N saat (g=gun, s=saat)
            "bugun"                        -> bugunun basindan simdiye
            "YYYY-MM-DD..YYYY-MM-DD"       -> kapsayici tarih araligi
            (baslangic_ts, bitis_ts)       -> dogrudan epoch tuple/list
        """
        if not tarih_araligi:
            return None, None
        if isinstance(tarih_araligi, (tuple, list)) and len(tarih_araligi) == 2:
            return tarih_araligi[0], tarih_araligi[1]

        s = str(tarih_araligi).strip().lower()
        now = time.time()

        if s in ("bugun", "today"):
            import datetime as _dt
            gun_basi = _dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return gun_basi.timestamp(), now

        m = re.match(r"^(\d+)\s*([gs])$", s)
        if m:
            sayi, birim = int(m.group(1)), m.group(2)
            saniye = sayi * 86400 if birim == "g" else sayi * 3600
            return now - saniye, now

        if ".." in s:
            try:
                bas_s, bit_s = s.split("..", 1)
                import datetime as _dt
                bas = _dt.datetime.strptime(bas_s.strip(), "%Y-%m-%d").timestamp()
                bit = _dt.datetime.strptime(bit_s.strip(), "%Y-%m-%d").timestamp() + 86399
                return bas, bit
            except Exception:
                return None, None

        return None, None

    def session_search(self, sorgu: str, limit: int = 10, tarih_araligi=None) -> list:
        """ReYMeN'teki session_search benzeri: FTS5 ile arama yapip session bazinda grupla.

        Args:
            sorgu:        Aranacak kelime/ifade (FTS5 MATCH sozdizimi gecerlidir).
            limit:        Donecek maksimum session sayisi.
            tarih_araligi: bkz. _tarih_araligi_coz icin desteklenen formatlar.

        Returns:
            [{
                "session_id": str,
                "ozet": str,
                "model": str,
                "started_at": float,
                "eslesen_mesaj_sayisi": int,
                "ilgili_mesajlar": [{"rol": str, "icerik": str, "created_at": float}, ...]
            }, ...]
        """
        if not sorgu or not sorgu.strip():
            return []

        bas_ts, bit_ts = self._tarih_araligi_coz(tarih_araligi)

        # Genis cek: ayni sessiondan birden fazla eslesme gelebilecegi icin
        # limit'in birkac kati mesaj cek, sonra session'a gore grupla.
        mesajlar = self.mesaj_ara(
            sorgu, limit=max(limit * 8, 50), baslangic_ts=bas_ts, bitis_ts=bit_ts
        )
        if not mesajlar:
            return []

        gruplar: Dict[str, list] = {}
        sira: list = []
        for m in mesajlar:
            sid = m["session_id"]
            if sid not in gruplar:
                gruplar[sid] = []
                sira.append(sid)
            if len(gruplar[sid]) < 3:  # session basina en fazla 3 ornek mesaj
                icerik = m["icerik"] or ""
                if len(icerik) > 240:
                    icerik = icerik[:240] + "…"
                gruplar[sid].append(
                    {"rol": m["rol"], "icerik": icerik, "created_at": m["created_at"]}
                )

        sonuc = []
        for sid in sira[:limit]:
            session = self.session_bul(sid)
            eslesen_sayisi = sum(1 for m in mesajlar if m["session_id"] == sid)
            ozet = session.get("title") if session else None
            if not ozet:
                ilk = gruplar[sid][0]["icerik"] if gruplar[sid] else ""
                ozet = f"({session.get('model', '?') if session else '?'}) {ilk}"
            sonuc.append({
                "session_id": sid,
                "ozet": ozet,
                "model": session.get("model") if session else None,
                "started_at": session.get("started_at") if session else None,
                "eslesen_mesaj_sayisi": eslesen_sayisi,
                "ilgili_mesajlar": gruplar[sid],
            })
        return sonuc

    def son_sessionlar(self, source: str = None, limit: int = 10) -> list:
        """En son sessionları getir; source filtresi opsiyonel."""
        with self._lock:
            conn = self._baglan()
            try:
                if source:
                    rows = conn.execute(
                        "SELECT * FROM sessions WHERE source=? "
                        "ORDER BY started_at DESC LIMIT ?",
                        (source, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
                return [dict(r) for r in rows]
            except Exception as e:
                log.error("son_sessionlar hatasi: %s", e)
                return []
            finally:
                conn.close()

    def istatistik(self) -> dict:
        """Toplam session, token ve maliyet özetini döndür."""
        with self._lock:
            conn = self._baglan()
            try:
                row = conn.execute(
                    """
                    SELECT
                        COUNT(*)                    AS toplam_session,
                        SUM(input_tokens)           AS toplam_input_token,
                        SUM(output_tokens)          AS toplam_output_token,
                        SUM(estimated_cost_usd)     AS toplam_tahmini_maliyet,
                        SUM(actual_cost_usd)        AS toplam_gercek_maliyet,
                        SUM(tool_call_count)        AS toplam_tool_call
                    FROM sessions
                    """
                ).fetchone()
                return dict(row) if row else {}
            except Exception as e:
                log.error("istatistik hatasi: %s", e)
                return {}
            finally:
                conn.close()

    # ── Disa / Ice aktarma ────────────────────────────────────────────

    def session_export(self, session_id: str, format: str = "json") -> str:
        """Session'i JSON veya Markdown olarak disa aktar.

        Args:
            session_id:  Aktarilacak session'in ID'si.
            format:      'json' (varsayilan) veya 'markdown'.

        Returns:
            format'a gore JSON string veya Markdown metni.
            Session bulunamazsa / hata olursa bos string dondurur.
        """
        try:
            session = self.session_bul(session_id)
            if not session:
                log.warning("session_export: session bulunamadi — %s", session_id)
                return ""

            mesajlar = self._mesajlari_getir(session_id)

            if format == "markdown":
                return self._export_markdown(session, mesajlar)
            else:
                return self._export_json(session, mesajlar)
        except Exception as e:
            log.error("session_export hatasi (session=%s): %s", session_id, e)
            return ""

    def _mesajlari_getir(self, session_id: str) -> list:
        """Belirtilen session'a ait mesajlari getir (yardimci)."""
        try:
            conn = self._baglan()
            try:
                rows = conn.execute(
                    "SELECT rol, icerik, created_at FROM session_messages "
                    "WHERE session_id=? ORDER BY created_at ASC",
                    (session_id,),
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception as e:
            log.error("_mesajlari_getir hatasi (session=%s): %s", session_id, e)
            return []

    def _export_json(self, session: dict, mesajlar: list) -> str:
        """Session verisini JSON formatina cevir."""
        try:
            veri = {
                "version": "1.0",
                "exported_at": time.time(),
                "session": {
                    "id": session.get("id"),
                    "source": session.get("source"),
                    "user_id": session.get("user_id"),
                    "model": session.get("model"),
                    "system_prompt": session.get("system_prompt"),
                    "parent_session_id": session.get("parent_session_id"),
                    "started_at": session.get("started_at"),
                    "ended_at": session.get("ended_at"),
                    "end_reason": session.get("end_reason"),
                    "message_count": session.get("message_count"),
                    "tool_call_count": session.get("tool_call_count"),
                    "input_tokens": session.get("input_tokens"),
                    "output_tokens": session.get("output_tokens"),
                    "title": session.get("title"),
                    "model_config": (
                        json.loads(session["model_config"])
                        if session.get("model_config")
                        else None
                    ),
                },
                "messages": [
                    {
                        "role": m["rol"],
                        "content": m["icerik"],
                        "created_at": m["created_at"],
                    }
                    for m in mesajlar
                ],
            }
            return json.dumps(veri, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error("_export_json hatasi: %s", e)
            return ""

    def _export_markdown(self, session: dict, mesajlar: list) -> str:
        """Session verisini Markdown formatina cevir."""
        try:
            baslik = session.get("title") or f"Session {session.get('id', 'bilinmiyor')}"
            satirlar = [
                f"# {baslik}",
                "",
                "## Meta Bilgiler",
                "",
                "| Alan | Deger |",
                "|------|-------|",
            ]

            meta = [
                ("Session ID", session.get("id")),
                ("Kaynak", session.get("source")),
                ("Kullanici", session.get("user_id")),
                ("Model", session.get("model")),
                ("Sistem Prompt", session.get("system_prompt")),
                ("Baslangic", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(session.get("started_at", 0))) if session.get("started_at") else "-"),
                ("Bitis", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(session.get("ended_at", 0))) if session.get("ended_at") else "-"),
                ("Bitis Nedeni", session.get("end_reason")),
                ("Mesaj Sayisi", str(session.get("message_count", 0))),
                ("Giris Token", str(session.get("input_tokens", 0))),
                ("Cikis Token", str(session.get("output_tokens", 0))),
                ("Tahmini Maliyet ($)", f"{session.get('estimated_cost_usd', 0):.6f}" if session.get("estimated_cost_usd") else "-"),
            ]

            for alan, deger in meta:
                if deger and deger != "-":
                    satirlar.append(f"| {alan} | {deger} |")

            satirlar.extend(["", "## Mesajlar", ""])

            for m in mesajlar:
                rol = m.get("rol", "bilinmiyor")
                icerik = m.get("icerik", "")
                zaman = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(m.get("created_at", 0)),
                ) if m.get("created_at") else "-"
                satirlar.append(f"### {rol.upper()} ({zaman})")
                satirlar.append("")
                satirlar.append(icerik or "_bos_")
                satirlar.append("")

            return "\n".join(satirlar)
        except Exception as e:
            log.error("_export_markdown hatasi: %s", e)
            return ""

    def session_import(self, data: str) -> str:
        """JSON formatindaki session verisini ice aktar, yeni session_id ile kaydeder.

        Args:
            data:  session_export ile olusturulmus JSON string.

        Returns:
            Yeni olusturulan session_id; hata durumunda bos string.
        """
        try:
            veri = json.loads(data)
            if "session" not in veri or "messages" not in veri:
                log.warning("session_import: gecersiz veri formati")
                return ""

            eski = veri["session"]
            mesajlar = veri.get("messages", [])

            # Yeni session ac
            yeni_id = self.session_baslat(
                source=eski.get("source", "import"),
                user_id=eski.get("user_id"),
                model=eski.get("model"),
                model_config=(
                    json.loads(eski["model_config"])
                    if isinstance(eski.get("model_config"), str)
                    else eski.get("model_config")
                ),
                system_prompt=eski.get("system_prompt"),
                title=(
                    f"{eski.get('title', 'import')} (import)"
                    if eski.get("title")
                    else "import"
                ),
            )

            if not yeni_id:
                log.error("session_import: yeni session olusturulamadi")
                return ""

            # Mesajlari ekle
            for m in mesajlar:
                rol = m.get("role", m.get("rol", "user"))
                icerik = m.get("content", m.get("icerik", ""))
                if icerik:
                    self.mesaj_ekle(yeni_id, rol, icerik)

            # Token sayilarini aktar
            input_tokens = eski.get("input_tokens", 0) or 0
            output_tokens = eski.get("output_tokens", 0) or 0
            if input_tokens > 0 or output_tokens > 0:
                self.token_guncelle(
                    yeni_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

            # Maliyet bilgilerini aktar
            if eski.get("estimated_cost_usd"):
                self.maliyet_guncelle(
                    yeni_id,
                    estimated_cost=eski["estimated_cost_usd"],
                    cost_status="imported",
                )

            # Session'u kapat
            self.session_bitir(yeni_id, end_reason=eski.get("end_reason", "imported"))

            log.info(
                "session_import: %s -> %s (%d mesaj, %d token)",
                eski.get("id", "?"),
                yeni_id,
                len(mesajlar),
                input_tokens + output_tokens,
            )
            return yeni_id
        except (json.JSONDecodeError, KeyError) as e:
            log.error("session_import: veri cozulemedi — %s", e)
            return ""
        except Exception as e:
            log.error("session_import hatasi: %s", e)
            return ""

    # ── Temizlik / Budama ──────────────────────────────────────────────

    def session_temizle(self, days: int = 90) -> int:
        """Belirtilen gunden eski ve end_reason='completed' olan session'lari siler.

        Auto-budama ile uyumlu: session_messages, session_tool_calls,
        session_messages_fts, session_messages_trigram tablolarindaki
        ilgili kayitlari da temizler.

        Args:
            days:  Kac gun oncesinden eski session'lar silinecek (varsayilan: 90).

        Returns:
            Silinen session sayisi; hata durumunda 0.
        """
        try:
            sinir_zaman = time.time() - (days * 86400)
            with self._lock:
                conn = self._baglan()
                try:
                    # Silinecek session ID'lerini bul
                    silinecek = conn.execute(
                        "SELECT id FROM sessions "
                        "WHERE started_at < ? AND end_reason = 'completed'",
                        (sinir_zaman,),
                    ).fetchall()

                    if not silinecek:
                        log.info("session_temizle: temizlenecek session bulunamadi")
                        return 0

                    ids = [row[0] for row in silinecek]
                    adet = len(ids)
                    placeholders = ",".join("?" * adet)

                    # Bagimli kayitlari once sil
                    conn.execute(
                        f"DELETE FROM session_messages WHERE session_id IN ({placeholders})",
                        ids,
                    )
                    conn.execute(
                        f"DELETE FROM session_tool_calls WHERE session_id IN ({placeholders})",
                        ids,
                    )

                    # FTS tablolarini temizle (content sync icin)
                    try:
                        conn.execute(
                            f"DELETE FROM session_messages_fts WHERE session_id IN ({placeholders})",
                            ids,
                        )
                    except Exception as _session__e819:
                        print(f"[UYARI] session_db.py:820 - {_session__e819}")
                    try:
                        conn.execute(
                            "DELETE FROM session_messages_trigram WHERE rowid IN "
                            "(SELECT id FROM session_messages WHERE session_id IN ("
                            + ",".join("?" * adet) + "))",
                            ids,
                        )
                    except Exception as _session__e828:
                        print(f"[UYARI] session_db.py:829 - {_session__e828}")

                    # Session'lari sil
                    conn.execute(
                        f"DELETE FROM sessions WHERE id IN ({placeholders})",
                        ids,
                    )

                    conn.commit()
                    log.info(
                        "session_temizle: %d session temizlendi (%.0f gun oncesi)",
                        adet,
                        days,
                    )
                    return adet
                finally:
                    conn.close()
        except Exception as e:
            log.error("session_temizle hatasi: %s", e)
            return 0

    # ── Geriye uyumluluk: FTS5 ajan_gunlugu ───────────────────────────

    def gunluge_yaz(self, hedef: str, eylem: str, sonuc: str):
        """FTS5 ajan_gunlugu'na yaz (geriye uyumluluk)."""
        with self._lock:
            conn = self._baglan()
            try:
                conn.execute(
                    "INSERT INTO ajan_gunlugu (hedef, eylem, sonuc) VALUES (?,?,?)",
                    (hedef, eylem, sonuc),
                )
                # Trigram tablosuna da yaz (partial search destegi)
                try:
                    conn.execute(
                        "INSERT INTO ajan_gunlugu_trigram (hedef, eylem, sonuc) VALUES (?,?,?)",
                        (hedef, eylem, sonuc),
                    )
                except Exception as _session__e867:
                    print(f"[UYARI] session_db.py:868 - {_session__e867}")
                conn.commit()
                log.debug("gunluge_yaz: eylem=%s", eylem)
            except Exception as e:
                log.error("gunluge_yaz hatasi: %s", e)
            finally:
                conn.close()

    def ara(self, sorgu: str, adet: int = 5) -> list:
        """FTS5 ajan_gunlugu'nda tam metin arama (geriye uyumluluk)."""
        with self._lock:
            conn = self._baglan()
            try:
                cur = conn.execute(
                    "SELECT hedef, eylem, sonuc FROM ajan_gunlugu "
                    "WHERE ajan_gunlugu MATCH ? LIMIT ?",
                    (sorgu, adet),
                )
                return cur.fetchall()
            except sqlite3.OperationalError:
                return []
            finally:
                conn.close()

    def hata_ozeti_cek(self, son_n: int = 50) -> dict:
        """Son N adımdaki hata örüntülerini analiz et (FAZ 6 uyumlu)."""
        with self._lock:
            conn = self._baglan()
            try:
                satirlar = conn.execute(
                    "SELECT eylem, sonuc FROM ajan_gunlugu ORDER BY rowid DESC LIMIT ?",
                    (son_n,),
                ).fetchall()
            except sqlite3.OperationalError:
                satirlar = []
            finally:
                conn.close()

        if not satirlar:
            return {
                "toplam": 0, "hata_sayisi": 0, "hata_orani": 0.0,
                "en_cok_hata_veren_arac": "", "tekrarlayan_hatalar": [],
            }

        import re
        hata_sayaci: dict = {}
        hata_sayisi = 0

        for eylem, sonuc in satirlar:
            hata_var = bool(re.search(r"\[Hata\]|\[Hata:", sonuc or "", re.IGNORECASE))
            if not hata_var:
                continue
            hata_sayisi += 1
            arac = (eylem or "bilinmeyen").split("(")[0][:40]
            mesaj_m = re.search(r"\[Hata[:\]](.*?)(?:\.|$)", sonuc or "", re.IGNORECASE)
            mesaj = mesaj_m.group(1).strip()[:80] if mesaj_m else (sonuc or "")[:80]
            anahtar = f"{arac}|{mesaj}"
            if anahtar not in hata_sayaci:
                hata_sayaci[anahtar] = {"arac": arac, "mesaj": mesaj, "sayi": 0}
            hata_sayaci[anahtar]["sayi"] += 1

        tekrarlayan = sorted(
            hata_sayaci.values(), key=lambda x: x["sayi"], reverse=True
        )[:5]
        en_cok = tekrarlayan[0]["arac"] if tekrarlayan else ""

        return {
            "toplam": len(satirlar),
            "hata_sayisi": hata_sayisi,
            "hata_orani": round(hata_sayisi / len(satirlar), 3) if satirlar else 0.0,
            "en_cok_hata_veren_arac": en_cok,
            "tekrarlayan_hatalar": tekrarlayan,
        }


# Geriye dönük uyumluluk aliası
SessionDB = AdvancedSessionStorage


_storage_singleton: Optional["AdvancedSessionStorage"] = None
_storage_lock = threading.Lock()


def get_storage(db_yolu: str = "merkez_db/session.db") -> "AdvancedSessionStorage":
    """Process boyunca paylasilan tek AdvancedSessionStorage ornegini dondur.

    tools.session_search_tool gibi diger modullerin her cagrida yeni
    sqlite baglantisi acmasini engellemek icin kullanilir.
    """
    global _storage_singleton
    if _storage_singleton is None:
        with _storage_lock:
            if _storage_singleton is None:
                _storage_singleton = AdvancedSessionStorage(db_yolu)
    return _storage_singleton


if __name__ == "__main__":
    import tempfile

    print("=== AdvancedSessionStorage Test ===")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yol = f.name

    s = AdvancedSessionStorage(db_yolu=yol)

    # Session yaşam döngüsü
    sid = s.session_baslat(
        source="cli",
        model="deepseek-chat",
        user_id="kullanici1",
        title=None,
    )
    assert sid, "session_id bos olmamali"
    print(f"session_baslat OK: {sid}")

    s.mesaj_ekle(sid, "user", "Merhaba")
    s.mesaj_ekle(sid, "assistant", "Nasıl yardımcı olabilirim?")
    print("mesaj_ekle OK")

    s.tool_call_kaydet(sid, "dosya_yaz", {"path": "test.txt"}, "OK", 120)
    print("tool_call_kaydet OK")

    s.token_guncelle(sid, input_tokens=450, output_tokens=120)
    print("token_guncelle OK")

    s.maliyet_guncelle(sid, estimated_cost=0.00034, cost_status="estimated")
    print("maliyet_guncelle OK")

    s.session_bitir(sid, end_reason="completed")
    print("session_bitir OK")

    # Sorgulama
    row = s.session_bul(sid)
    assert row["id"] == sid
    assert row["message_count"] == 2
    assert row["tool_call_count"] == 1
    assert row["input_tokens"] == 450
    assert row["end_reason"] == "completed"
    print(f"session_bul OK: msg={row['message_count']}, token={row['input_tokens']}")

    stats = s.istatistik()
    assert stats["toplam_session"] >= 1
    print(f"istatistik OK: toplam={stats['toplam_session']}")

    son = s.son_sessionlar(limit=5)
    assert len(son) >= 1
    print(f"son_sessionlar OK: {len(son)} session")

    # Geriye uyumluluk
    s.gunluge_yaz("test hedefi", "DOSYA_YAZ", "TAMAMLANDI")
    sonuc = s.ara("test")
    print(f"FTS5 ara OK: {len(sonuc)} sonuc")

    print("\nTum testler gecti!")
