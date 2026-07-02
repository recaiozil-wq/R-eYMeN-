# -*- coding: utf-8 -*-
"""
continuous_learning.py — Session'lar Arası Sürekli Öğrenme Sistemi.

ReYMeN'teki "Session'lar arasi ogrenme" ozelliginin ReYMeN implementasyonu.

Ne yapar:
- Her session sonunda ogrenilenleri kaydeder (beceri, hata, cozum)
- Yeni session basinda gecmis ogrenmeleri yukler
- LLM context'ine "gecmiste ogrendiklerim" olarak enjekte eder
- closed_learning_loop + self_improvement + ogrenme modullerini tek cati

Entegrasyon:
    from reymen.cereyan.continuous_learning import (
        session_baslat, ogrenmeyi_kaydet,
        session_bitir, ogrenme_baglani_al
    )
    session_baslat(session_id)       # conversation_loop basinda
    ogrenmeyi_kaydet("beceri", ...)   # gorev sonrasi
    session_bitir(session_id)         # conversation_loop sonunda
    baglam = ogrenme_baglani_al()     # system prompt'a eklenecek
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.resolve()
DB_PATH = ROOT / ".ReYMeN" / "continuous_learning.db"
_MAX_OGRENME_BAGLAM = 3000
_MAX_GECMIS_SESSION = 20


def _su_an() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_baglan() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=15)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS ogrenmeler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL DEFAULT '',
            tip TEXT NOT NULL DEFAULT 'genel',
            icerik TEXT NOT NULL,
            kaynak TEXT DEFAULT '',
            basari BOOLEAN DEFAULT 1,
            etiketler TEXT DEFAULT '[]',
            olusturma TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS session_ozet (
            session_id TEXT PRIMARY KEY,
            baslangic TEXT, bitis TEXT,
            gorev_sayisi INTEGER DEFAULT 0,
            basari_sayisi INTEGER DEFAULT 0,
            hata_sayisi INTEGER DEFAULT 0,
            ogrenme_sayisi INTEGER DEFAULT 0,
            ozet TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS beceri_aktarimi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kaynak_session TEXT, beceri_adi TEXT,
            beceri_icerik TEXT, kullanim_sayisi INTEGER DEFAULT 1,
            son_kullanim TEXT, puan REAL DEFAULT 0.0
        );
    """)
    con.commit()
    return con


class ContinuousLearning:
    def __init__(self, db_yolu: Optional[Path] = None):
        self._db_yolu = db_yolu or DB_PATH
        self._aktif_session_id: Optional[str] = None
        self._session_baslangic: Optional[str] = None
        self._session_ogrenmeler: List[Dict[str, Any]] = []
        self._onceki_session_ozetleri: List[Dict[str, Any]] = []
        self._closed_loop = None
        self._closed_loop_yukle()
        self._onceki_sessionlari_yukle()

    def _closed_loop_yukle(self):
        try:
            from reymen.cereyan.closed_learning_loop import ClosedLearningLoop
            self._closed_loop = ClosedLearningLoop()
            logger.info("[CL] ClosedLearningLoop yuklendi")
        except ImportError:
            logger.warning("[fix_01_sessiz_except] ImportError")

    def _onceki_sessionlari_yukle(self, limit: int = _MAX_GECMIS_SESSION):
        try:
            con = _db_baglan()
            rows = con.execute(
                "SELECT session_id, baslangic, gorev_sayisi, basari_sayisi, "
                "hata_sayisi, ogrenme_sayisi, ozet FROM session_ozet "
                "ORDER BY baslangic DESC LIMIT ?", (limit,)
            ).fetchall()
            con.close()
            for r in rows:
                self._onceki_session_ozetleri.append({
                    "session_id": r[0], "baslangic": r[1],
                    "gorev_sayisi": r[2], "basari_sayisi": r[3],
                    "hata_sayisi": r[4], "ogrenme_sayisi": r[5],
                    "ozet": r[6] or "",
                })
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

    def session_baslat(self, session_id: str) -> None:
        self._aktif_session_id = session_id
        self._session_baslangic = _su_an()
        self._session_ogrenmeler = []
        try:
            con = _db_baglan()
            con.execute("INSERT OR REPLACE INTO session_ozet (session_id, baslangic) VALUES (?, ?)",
                       (session_id, self._session_baslangic))
            con.commit()
            con.close()
        except Exception as e:
            logger.warning("[CL] Session baslatma hatasi: %s", e)
        if self._closed_loop:
            try:
                self._closed_loop.tum_becerileri_indeksle()
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )
        logger.info("[CL] Session basladi: %s", session_id)

    def ogrenmeyi_kaydet(self, tip: str, icerik: str, kaynak: str = "",
                         basari: bool = True, etiketler: Optional[List[str]] = None) -> int:
        if not self._aktif_session_id:
            return -1
        try:
            con = _db_baglan()
            con.execute(
                "INSERT INTO ogrenmeler (session_id, tip, icerik, kaynak, basari, etiketler) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (self._aktif_session_id, tip, icerik[:5000], kaynak[:200],
                 int(basari), json.dumps(etiketler or [])))
            kayit_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
            con.execute("UPDATE session_ozet SET ogrenme_sayisi=ogrenme_sayisi+1 WHERE session_id=?",
                       (self._aktif_session_id,))
            if basari:
                con.execute("UPDATE session_ozet SET basari_sayisi=basari_sayisi+1, gorev_sayisi=gorev_sayisi+1 WHERE session_id=?",
                           (self._aktif_session_id,))
            else:
                con.execute("UPDATE session_ozet SET hata_sayisi=hata_sayisi+1, gorev_sayisi=gorev_sayisi+1 WHERE session_id=?",
                           (self._aktif_session_id,))
            con.commit()
            con.close()
            self._session_ogrenmeler.append({"id": kayit_id, "tip": tip, "icerik": icerik[:200], "basari": basari})
            if tip == "beceri" and self._closed_loop:
                try:
                    self._closed_loop.beceri_kristallestir(ad=f"cl_{kayit_id}", aciklama=icerik[:200], icerik=icerik)
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )
            return kayit_id
        except Exception as e:
            logger.warning("[CL] Kayit hatasi: %s", e)
            return -1

    def session_bitir(self, session_id: str) -> Dict[str, Any]:
        bitis = _su_an()
        ozet = {"session_id": session_id, "baslangic": self._session_baslangic, "bitis": bitis,
                "ogrenme_sayisi": len(self._session_ogrenmeler)}
        try:
            con = _db_baglan()
            con.execute("UPDATE session_ozet SET bitis=?, ozet=? WHERE session_id=?",
                       (bitis, json.dumps(ozet), session_id))
            con.commit()
            con.close()
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )
        self._aktif_session_id = None
        return ozet

    def ogrenme_baglani_al(self, max_char: int = _MAX_OGRENME_BAGLAM) -> str:
        parcalar: List[str] = []
        if self._onceki_session_ozetleri:
            parcalar.append("## Gecmis Session Ogrenmeleri")
            for s in self._onceki_session_ozetleri[:5]:
                basari_yuzde = int(s["basari_sayisi"] / max(s["gorev_sayisi"], 1) * 100) if s["gorev_sayisi"] > 0 else 0
                parcalar.append(f"- Session {s['session_id'][:12]}: {s['gorev_sayisi']} gorev, %{basari_yuzde} basari, {s['ogrenme_sayisi']} ogrenme")
        if self._session_ogrenmeler:
            parcalar.append(f"\n## Bu Session {len(self._session_ogrenmeler)} Ogrenme")
            for o in self._session_ogrenmeler[-5:]:
                ikon = "\u2705" if o.get("basari") else "\u274c"
                parcalar.append(f"- {ikon} [{o.get('tip','?')}] {o.get('icerik','')[:150]}")
        if self._closed_loop and self._aktif_session_id:
            try:
                b = self._closed_loop.beceri_baglani_al_yapisal(sorgu=self._aktif_session_id, limit=3)
                if b and "beceriler" in b:
                    parcalar.append(f"\n## Ilgili Beceriler ({len(b['beceriler'])})")
                    for bec in b["beceriler"][:3]:
                        parcalar.append(f"- {bec.get('ad','?')}: {bec.get('aciklama','')[:100]}")
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )
        metin = "\n".join(parcalar)
        if len(metin) > max_char:
            metin = metin[:max_char] + "\n...(kesildi)"
        return metin

    def gecmis_ogrenmeleri_getir(self, tip: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            con = _db_baglan()
            if tip:
                rows = con.execute("SELECT id, session_id, tip, icerik, basari, olusturma FROM ogrenmeler WHERE tip=? ORDER BY id DESC LIMIT ?", (tip, limit)).fetchall()
            else:
                rows = con.execute("SELECT id, session_id, tip, icerik, basari, olusturma FROM ogrenmeler ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            con.close()
            return [{"id": r[0], "session_id": r[1][:12], "tip": r[2], "icerik": r[3][:300], "basari": bool(r[4]), "tarih": r[5]} for r in rows]
        except Exception:
            return []

    def istatistik(self) -> Dict[str, Any]:
        try:
            con = _db_baglan()
            toplam = con.execute("SELECT COUNT(*) FROM ogrenmeler").fetchone()[0]
            tipler = con.execute("SELECT tip, COUNT(*) FROM ogrenmeler GROUP BY tip").fetchall()
            session_sayisi = con.execute("SELECT COUNT(*) FROM session_ozet").fetchone()[0]
            con.close()
            return {"toplam_ogrenme": toplam, "tipler": {r[0]: r[1] for r in tipler}, "toplam_session": session_sayisi}
        except Exception as e:
            return {"hata": str(e)}


_CL_INSTANCE: Optional[ContinuousLearning] = None


def continuous_learning_al() -> ContinuousLearning:
    global _CL_INSTANCE
    if _CL_INSTANCE is None:
        _CL_INSTANCE = ContinuousLearning()
    return _CL_INSTANCE


def session_baslat(session_id: str) -> None:
    continuous_learning_al().session_baslat(session_id)


def ogrenmeyi_kaydet(tip: str, icerik: str, kaynak: str = "", basari: bool = True):
    return continuous_learning_al().ogrenmeyi_kaydet(tip, icerik, kaynak, basari)


def session_bitir(session_id: str) -> Dict[str, Any]:
    return continuous_learning_al().session_bitir(session_id)


def ogrenme_baglani_al() -> str:
    return continuous_learning_al().ogrenme_baglani_al()
