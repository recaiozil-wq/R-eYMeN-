# -*- coding: utf-8 -*-
"""
steering_loop.py — ReYMeN 5 Katmanlı Steering Loop (SQLite FTS5)

ReYMeN Agent'in delegate_task/session_search/cron altyapısına eşdeğer,
ReYMeN'in kendi 5 katmanlı yönlendirme döngüsü.

Katmanlar:
  1. HAFIZA   — SQLite+FTS5 kalıcı görev/konuşma hafızası
  2. SANDBOX  — Motor üzerinden güvenli araç çalıştırma
  3. TALIMAT  — Sistem prompt'u + araç rehberi
  4. KANCA    — Tekrar koruması + kural denetimi (SQLite persist)
  5. GOZLEM   — LLM çağrı takibi + token/maliyet (SQLite persist)

Tüm katmanlar SQLite (hafiza_genislet.py) üzerinde birleşir.
"""

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── SQLite (standart kütüphane) ─────────────────────────────────────────────
import sqlite3
import logging
logger = logging.getLogger(__name__)
_SQLITE_AVAILABLE = True

# ── Circuit Breaker ──────────────────────────────────────────────────────────
try:
    from reymen.sistem.circuit_breaker import CircuitBreaker, CircuitBreakerState
except ImportError:
    CircuitBreaker = None  # type: ignore
    CircuitBreakerState = None  # type: ignore

ROOT = Path(__file__).parent.resolve()
_DB_DIR = ROOT / ".reymen_hafiza"
_DB_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = str(_DB_DIR / "steering.db")

_yazma_kilit = threading.Lock()

# ════════════════════════════════════════════════════════════════════════════
# KATMAN 1 — HAFIZA (SQLite + FTS5)
# ════════════════════════════════════════════════════════════════════════════

class Katman1Hafiza:
    """Görev ve konuşma hafızası — Kalıcı SQLite+FTS5.
    
    Her alt ajan adımı, görev sonucu, kullanıcı mesajı
    FTS5 ile indexlenir. Tam metin arama.
    """

    def __init__(self, db_path: str = _DB_PATH):
        self._db = db_path
        self._conn: Optional[sqlite3.Connection] = None
        if _SQLITE_AVAILABLE:
            self._baglan()
            self._tablolari_olustur()

    def _baglan(self):
        try:
            self._conn = sqlite3.connect(self._db, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error:
            self._conn = None

    def _tablolari_olustur(self):
        if not self._conn:
            return
        try:
            c = self._conn.cursor()
            # Ana kayit tablosu
            c.execute("""
                CREATE TABLE IF NOT EXISTS katman1_kayit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    tur TEXT NOT NULL,
                    icerik TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    zaman REAL NOT NULL
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_k1_task ON katman1_kayit(task_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_k1_tur ON katman1_kayit(tur)")
            # FTS5
            c.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS katman1_fts USING fts5(
                    icerik, metadata,
                    content='katman1_kayit',
                    content_rowid='id',
                    tokenize='unicode61'
                )
            """)
            # Trigger'lar
            c.execute("""
                CREATE TRIGGER IF NOT EXISTS k1_ai AFTER INSERT ON katman1_kayit BEGIN
                    INSERT INTO katman1_fts(rowid, icerik, metadata)
                    VALUES (new.id, new.icerik, new.metadata);
                END
            """)
            c.execute("""
                CREATE TRIGGER IF NOT EXISTS k1_ad AFTER DELETE ON katman1_kayit BEGIN
                    INSERT INTO katman1_fts(katman1_fts, rowid, icerik, metadata)
                    VALUES ('delete', old.id, old.icerik, old.metadata);
                END
            """)
            self._conn.commit()
        except sqlite3.Error as _steering_e108:
            print(f"[UYARI] steering_loop.py:109 - {_steering_e108}")

    def kaydet(self, task_id: str, tur: str, icerik: str, metadata: Optional[dict] = None):
        """Bir kayit ekle (adim, sonuc, hata, gozlem)."""
        if not self._conn:
            return False
        try:
            meta = json.dumps(metadata or {}, ensure_ascii=False)
            with _yazma_kilit:
                self._conn.execute(
                    "INSERT INTO katman1_kayit (task_id, tur, icerik, metadata, zaman) VALUES (?, ?, ?, ?, ?)",
                    (task_id, tur, icerik[:2000], meta, time.time())
                )
                self._conn.commit()
            return True
        except sqlite3.Error:
            return False

    def ara(self, sorgu: str, task_id: str = "", limit: int = 10) -> List[Dict]:
        """FTS5 ile hafizada ara."""
        if not self._conn or not sorgu.strip():
            return []
        import re
        kelimeler = re.findall(r'\w+', sorgu)
        if not kelimeler:
            return []
        fts_sorgu = " AND ".join(kelimeler[:10])
        try:
            c = self._conn.cursor()
            kosul = "AND k.task_id = ?" if task_id else ""
            params: list = [fts_sorgu]
            if task_id:
                params.append(task_id)
            params.append(limit)
            c.execute(f"""
                SELECT k.id, k.task_id, k.tur, k.icerik, k.zaman, fts.rank as skor
                FROM katman1_fts fts
                JOIN katman1_kayit k ON k.id = fts.rowid
                WHERE katman1_fts MATCH ? {kosul}
                ORDER BY fts.rank
                LIMIT ?
            """, params)
            return [dict(r) for r in c.fetchall()]
        except sqlite3.Error:
            return []

    def task_gecmis(self, task_id: str) -> List[Dict]:
        """Bir task'in tum kayitlarini getir."""
        if not self._conn:
            return []
        try:
            c = self._conn.cursor()
            c.execute(
                "SELECT * FROM katman1_kayit WHERE task_id = ? ORDER BY zaman ASC",
                (task_id,)
            )
            return [dict(r) for r in c.fetchall()]
        except sqlite3.Error:
            return []

    def durum(self) -> dict:
        if not self._conn:
            return {"aktif": False}
        try:
            c = self._conn.cursor()
            c.execute("SELECT COUNT(*) as n FROM katman1_kayit")
            toplam = c.fetchone()["n"]
            c.execute("SELECT COUNT(DISTINCT task_id) as n FROM katman1_kayit")
            task_say = c.fetchone()["n"]
            return {"aktif": True, "toplam_kayit": toplam, "aktif_task": task_say}
        except sqlite3.Error:
            return {"aktif": False}


# ════════════════════════════════════════════════════════════════════════════
# KATMAN 4 — KANCA (SQLite persist)
# ════════════════════════════════════════════════════════════════════════════

class Katman4Kanca:
    """Eylem öncesi kural denetimi — SQLite persist + in-memory cache.
    
    Kurallar:
    - Aynı eylem N kez art arda → DUR
    - Yasaklı araç → BLOKE
    - Toplam eylem limiti
    - Hızlı döngü koruması
    """

    ENGELLENEN = frozenset({"ALT_AJAN_GOREVLENDIR", "SIL_DOSYA", "BICAKLA"})
    MAKS_ART_ARDA = 4
    MAKS_EYLEM = 30
    MIN_ARALIK = 0.5

    def __init__(self, db_path: str = _DB_PATH):
        self._db = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._cache: Dict[str, dict] = {}  # task_id -> durum
        self._cb: Optional[Any] = CircuitBreaker() if CircuitBreaker is not None else None
        if _SQLITE_AVAILABLE:
            self._baglan()
            self._tablolari_olustur()
            self._cache_yukle()

    def _baglan(self):
        try:
            self._conn = sqlite3.connect(self._db, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        except sqlite3.Error:
            self._conn = None

    def _tablolari_olustur(self):
        if not self._conn:
            return
        try:
            c = self._conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS katman4_kanca (
                    task_id TEXT PRIMARY KEY,
                    son_eylem TEXT DEFAULT '',
                    art_arda_sayac INTEGER DEFAULT 0,
                    toplam_eylem INTEGER DEFAULT 0,
                    son_ts REAL DEFAULT 0,
                    bloke INTEGER DEFAULT 0,
                    bloke_nedeni TEXT DEFAULT '',
                    guncelleme_ts REAL NOT NULL
                )
            """)
            self._conn.commit()
        except sqlite3.Error as _steering_e237:
            print(f"[UYARI] steering_loop.py:238 - {_steering_e237}")

    def _cache_yukle(self):
        """DB'deki tum aktif kanca durumlarini cache'e yukle."""
        if not self._conn:
            return
        try:
            c = self._conn.cursor()
            c.execute("SELECT * FROM katman4_kanca WHERE bloke = 0")
            for r in c.fetchall():
                self._cache[r["task_id"]] = dict(r)
        except sqlite3.Error as _steering_e249:
            print(f"[UYARI] steering_loop.py:250 - {_steering_e249}")

    def _db_kaydet(self, task_id: str, durum: dict):
        """Cache'i DB'ye yaz."""
        if not self._conn:
            return
        try:
            with _yazma_kilit:
                self._conn.execute(
                    """INSERT OR REPLACE INTO katman4_kanca
                       (task_id, son_eylem, art_arda_sayac, toplam_eylem,
                        son_ts, bloke, bloke_nedeni, guncelleme_ts)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (task_id, durum.get("son_eylem", ""),
                     durum.get("art_arda_sayac", 0),
                     durum.get("toplam_eylem", 0),
                     durum.get("son_ts", 0),
                     1 if durum.get("bloke", False) else 0,
                     durum.get("bloke_nedeni", ""), time.time())
                )
                self._conn.commit()
        except sqlite3.Error as _steering_e271:
            print(f"[UYARI] steering_loop.py:272 - {_steering_e271}")

    def denetle(self, task_id: str, arac: str, derinlik: int = 1) -> Optional[str]:
        """Eylemi denetle. None = gecerli, str = hata."""
        # Circuit Breaker kontrolü — OPEN ise erken dön
        if self._cb is not None:
            cb_mesaj = self._cb.denetle()
            if cb_mesaj:
                return cb_mesaj

        if arac in self.ENGELLENEN:
            self._cache[task_id] = {"bloke": True, "bloke_nedeni": f"'{arac}' yasakli"}
            self._db_kaydet(task_id, self._cache[task_id])
            return f"[KANCA] '{arac}' yasakli araç — task bloke."

        durum = self._cache.get(task_id, {
            "son_eylem": "", "art_arda_sayac": 0,
            "toplam_eylem": 0, "son_ts": 0,
            "bloke": False, "bloke_nedeni": ""
        })

        if durum.get("bloke", False):
            return f"[KANCA] Task bloke: {durum.get('bloke_nedeni', '?')}"

        # Ayni eylem art arda
        if arac == durum.get("son_eylem", ""):
            durum["art_arda_sayac"] = durum.get("art_arda_sayac", 0) + 1
            if durum["art_arda_sayac"] >= self.MAKS_ART_ARDA:
                durum["bloke"] = True
                durum["bloke_nedeni"] = f"'{arac}' {self.MAKS_ART_ARDA}x art arda"
                self._cache[task_id] = durum
                self._db_kaydet(task_id, durum)
                return f"[KANCA] {durum['bloke_nedeni']} — task bloke."
        else:
            durum["art_arda_sayac"] = 1
        durum["son_eylem"] = arac
        durum["toplam_eylem"] = durum.get("toplam_eylem", 0) + 1

        # Toplam eylem limiti
        if durum["toplam_eylem"] > self.MAKS_EYLEM:
            durum["bloke"] = True
            durum["bloke_nedeni"] = f"{self.MAKS_EYLEM} eylem limiti asildi"
            self._cache[task_id] = durum
            self._db_kaydet(task_id, durum)
            return f"[KANCA] Task {task_id}: {durum['bloke_nedeni']}"

        # Hizli dongu
        simdi = time.time()
        if durum.get("son_ts", 0) > 0 and (simdi - durum["son_ts"]) < self.MIN_ARALIK:
            self._cache[task_id] = durum
            return f"[KANCA] Cok hizli: {(simdi - durum['son_ts']):.2f}s < {self.MIN_ARALIK}s"
        durum["son_ts"] = simdi

        self._cache[task_id] = durum
        self._db_kaydet(task_id, durum)
        return None  # Ihlal yok

    def bloke_coz(self, task_id: str) -> bool:
        if task_id in self._cache:
            self._cache[task_id] = {"bloke": False, "bloke_nedeni": "",
                                     "son_eylem": "", "art_arda_sayac": 0,
                                     "toplam_eylem": 0, "son_ts": 0}
            self._db_kaydet(task_id, self._cache[task_id])
            return True
        return False

    def task_temizle(self, task_id: str):
        self._cache.pop(task_id, None)
        if self._conn:
            try:
                self._conn.execute("DELETE FROM katman4_kanca WHERE task_id = ?", (task_id,))
                self._conn.commit()
            except sqlite3.Error as _steering_e344:
                print(f"[UYARI] steering_loop.py:345 - {_steering_e344}")

    def hata_bildir(self, task_id: str) -> Optional[str]:
        """Arac hatasi bildir. Circuit 5. hatada acilir, mesaj doner."""
        if self._cb is None:
            return None
        return self._cb.hata_kaydet()

    def basari_bildir(self, task_id: str) -> None:
        """Arac basarisi bildir. HALF_OPEN → CLOSED, sayac sifirlanir."""
        if self._cb is not None:
            self._cb.basari_kaydet()

    def circuit_breaker_sifirla(self) -> None:
        """Circuit breaker'i tamamen sifirla (test / manuel mudahale)."""
        if self._cb is not None:
            self._cb.sifirla()

    def istatistik(self) -> dict:
        aktif = len(self._cache)
        blokeli = sum(1 for d in self._cache.values() if d.get("bloke", False))
        cb_bilgi = self._cb.durum_bilgisi() if self._cb is not None else {}
        return {"aktif_task": aktif, "blokeli_task": blokeli, "circuit_breaker": cb_bilgi}


# ════════════════════════════════════════════════════════════════════════════
# KATMAN 5 — GOZLEM (SQLite persist)
# ════════════════════════════════════════════════════════════════════════════

class Katman5Gozlem:
    """LLM çağrı takibi — SQLite + token/maliyet analizi.
    
    Her LLM çağrısı: task_id, sure, token, maliyet, basarili/basarisiz.
    """

    TOKEN_BASINA_MALIYET = {
        "deepseek": (0.0005, 0.0020),
        "openai": (0.00015, 0.0006),
        "anthropic": (0.00025, 0.00125),
        "groq": (0.0001, 0.0001),
        "lmstudio": (0.0, 0.0),
        "ollama": (0.0, 0.0),
    }
    VARSAYILAN_MALIYET = (0.001, 0.003)

    def __init__(self, db_path: str = _DB_PATH):
        self._db = db_path
        self._conn: Optional[sqlite3.Connection] = None
        if _SQLITE_AVAILABLE:
            self._baglan()
            self._tablolari_olustur()

    def _baglan(self):
        try:
            self._conn = sqlite3.connect(self._db, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        except sqlite3.Error:
            self._conn = None

    def _tablolari_olustur(self):
        if not self._conn:
            return
        try:
            c = self._conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS katman5_gozlem (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    sure_sn REAL NOT NULL,
                    girdi_token INTEGER DEFAULT 0,
                    cikti_token INTEGER DEFAULT 0,
                    basarili INTEGER DEFAULT 1,
                    maliyet_usd REAL DEFAULT 0,
                    notlar TEXT DEFAULT '',
                    ts REAL NOT NULL
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_k5_task ON katman5_gozlem(task_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_k5_ts ON katman5_gozlem(ts)")
            self._conn.commit()
        except sqlite3.Error as _steering_e425:
            print(f"[UYARI] steering_loop.py:426 - {_steering_e425}")

    def _maliyet_hesapla(self, girdi: int, cikti: int) -> float:
        g_mal, c_mal = self.VARSAYILAN_MALIYET
        return round((girdi * g_mal + cikti * c_mal) / 1000, 6)

    def kaydet(self, task_id: str, sure_sn: float, cevap: str = "",
               basarili: bool = True, girdi_token: int = 0,
               cikti_token: int = 0, notlar: str = ""):
        if not self._conn:
            return
        if cikti_token == 0 and cevap:
            cikti_token = max(1, len(cevap) // 4)
        maliyet = self._maliyet_hesapla(girdi_token, cikti_token)
        try:
            with _yazma_kilit:
                self._conn.execute(
                    """INSERT INTO katman5_gozlem
                       (task_id, sure_sn, girdi_token, cikti_token, basarili,
                        maliyet_usd, notlar, ts)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (task_id, round(sure_sn, 3), girdi_token, cikti_token,
                     1 if basarili else 0, maliyet, notlar[:200], time.time())
                )
                self._conn.commit()
        except sqlite3.Error as _steering_e451:
            print(f"[UYARI] steering_loop.py:452 - {_steering_e451}")

    def task_ozet(self, task_id: str) -> dict:
        if not self._conn:
            return {"task_id": task_id, "cagri_sayisi": 0}
        try:
            c = self._conn.cursor()
            c.execute("SELECT COUNT(*) as n, SUM(sure_sn) as sure, "
                       "SUM(girdi_token) as gt, SUM(cikti_token) as ct, "
                       "SUM(maliyet_usd) as mal, SUM(basarili) as ok "
                       "FROM katman5_gozlem WHERE task_id = ?", (task_id,))
            r = c.fetchone()
            if not r or r["n"] == 0:
                return {"task_id": task_id, "cagri_sayisi": 0}
            return {
                "task_id": task_id,
                "cagri_sayisi": r["n"],
                "toplam_sure_sn": round(r["sure"] or 0, 2),
                "basarili": r["ok"] or 0,
                "basarisiz": r["n"] - (r["ok"] or 0),
                "toplam_girdi_token": r["gt"] or 0,
                "toplam_cikti_token": r["ct"] or 0,
                "tahmini_maliyet_usd": round(r["mal"] or 0, 6),
            }
        except sqlite3.Error:
            return {"task_id": task_id, "cagri_sayisi": 0}

    def genel_ozet(self) -> dict:
        if not self._conn:
            return {"toplam_cagri": 0, "aktif_task": 0}
        try:
            c = self._conn.cursor()
            c.execute("SELECT COUNT(*) as n, SUM(sure_sn) as sure, "
                       "SUM(maliyet_usd) as mal, SUM(basarili) as ok, "
                       "COUNT(DISTINCT task_id) as task "
                       "FROM katman5_gozlem")
            r = c.fetchone()
            if not r or r["n"] == 0:
                return {"toplam_cagri": 0}
            return {
                "toplam_cagri": r["n"],
                "aktif_task": r["task"],
                "toplam_sure_sn": round(r["sure"] or 0, 2),
                "basarili": r["ok"] or 0,
                "basarisiz": r["n"] - (r["ok"] or 0),
                "tahmini_maliyet_usd": round(r["mal"] or 0, 4),
            }
        except sqlite3.Error:
            return {"toplam_cagri": 0}

    def son_kayit(self) -> List[Dict]:
        if not self._conn:
            return []
        try:
            c = self._conn.cursor()
            c.execute(
                "SELECT * FROM katman5_gozlem ORDER BY ts DESC LIMIT 10"
            )
            return [dict(r) for r in c.fetchall()]
        except sqlite3.Error:
            return []

    def temizle(self):
        if not self._conn:
            return
        try:
            self._conn.execute("DELETE FROM katman5_gozlem")
            self._conn.commit()
        except sqlite3.Error as _steering_e520:
            print(f"[UYARI] steering_loop.py:521 - {_steering_e520}")


# ════════════════════════════════════════════════════════════════════════════
# 5 KATMAN BIRLESIK ORKESTRASYON
# ════════════════════════════════════════════════════════════════════════════

class SteeringLoop:
    """5 katmanı tek API altında birleştirir.
    
    Kullanim:
        from steering_loop import loop
        loop.hafiza_kaydet("task_01", "adim", "...")
        hata = loop.kanca_denetle("task_01", "KOMUT_CALISTIR")
        loop.gozlem_kaydet("task_01", 2.5, cevap="...")
    """

    def __init__(self, db_path: str = _DB_PATH):
        self.hafiza = Katman1Hafiza(db_path)
        self.kanca = Katman4Kanca(db_path)
        self.gozlem = Katman5Gozlem(db_path)

    # ── Katman 1: Hafiza ──
    def hafiza_kaydet(self, task_id: str, tur: str, icerik: str,
                      metadata: Optional[dict] = None) -> bool:
        return self.hafiza.kaydet(task_id, tur, icerik, metadata)

    def hafiza_ara(self, sorgu: str, task_id: str = "",
                   limit: int = 10) -> List[Dict]:
        return self.hafiza.ara(sorgu, task_id, limit)

    def task_gecmis(self, task_id: str) -> List[Dict]:
        return self.hafiza.task_gecmis(task_id)

    # ── Katman 4: Kanca ──
    def kanca_denetle(self, task_id: str, arac: str,
                      derinlik: int = 1) -> Optional[str]:
        return self.kanca.denetle(task_id, arac, derinlik)

    def kanca_coz(self, task_id: str) -> bool:
        return self.kanca.bloke_coz(task_id)

    def kanca_temizle(self, task_id: str):
        self.kanca.task_temizle(task_id)

    # ── Katman 5: Gozlem ──
    def gozlem_kaydet(self, task_id: str, sure_sn: float,
                      cevap: str = "", basarili: bool = True,
                      girdi_token: int = 0, cikti_token: int = 0,
                      notlar: str = ""):
        self.gozlem.kaydet(task_id, sure_sn, cevap, basarili,
                           girdi_token, cikti_token, notlar)

    def gozlem_ozet(self, task_id: str = "") -> dict:
        if task_id:
            return self.gozlem.task_ozet(task_id)
        return self.gozlem.genel_ozet()

    # ── Tüm katman durumu ──
    def durum(self) -> dict:
        h = self.hafiza.durum()
        k = self.kanca.istatistik()
        g = self.gozlem.genel_ozet()
        return {
            "katman1_hafiza": h,
            "katman4_kanca": k,
            "katman5_gozlem": {
                "toplam_cagri": g.get("toplam_cagri", 0),
                "aktif_task": g.get("aktif_task", 0),
                "maliyet_usd": g.get("tahmini_maliyet_usd", 0),
                "toplam_sure_sn": g.get("toplam_sure_sn", 0),
            },
        }


# ════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════════════

loop = SteeringLoop()


# ════════════════════════════════════════════════════════════════════════════
# TEST
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== 5 KATMAN STEERING LOOP TEST ===")
    
    # Her testten once DB'yi temizle
    import shutil
    _db_dir = Path(__file__).parent / ".reymen_hafiza"
    if _db_dir.exists():
        shutil.rmtree(str(_db_dir), ignore_errors=True)
    _db_dir.mkdir(parents=True, exist_ok=True)

    # Yeniden baslat
    loop = SteeringLoop()
    
    # Test 1: Hafiza kaydet + FTS5 ara
    loop.hafiza_kaydet("test_01", "adim", "Python decorator nasil calisir?")
    loop.hafiza_kaydet("test_01", "sonuc", "Decorator fonksiyon alir, ozellik ekler")
    loop.hafiza_kaydet("test_02", "adim", "Lambda tek satirlik fonksiyon")
    sonuc = loop.hafiza_ara("decorator")
    assert len(sonuc) > 0, "Decorator aranabilmeli"
    print(f"  ✅ FTS5 ara 'decorator': {len(sonuc)} sonuc")

    # Test 2: Kanca
    hata = loop.kanca_denetle("test_kanca", "DOSYA_OKU")
    assert hata is None, "Normal eylem ihlal vermemeli"
    for _ in range(5):
        hata = loop.kanca_denetle("test_kanca", "DOSYA_OKU")
    assert hata is not None, "5x ayni eylem bloke etmeli"
    print(f"  ✅ Kanca bloke: {hata[:40]}...")
    loop.kanca_coz("test_kanca")
    assert loop.kanca_denetle("test_kanca", "DOSYA_YAZ") is None
    print(f"  ✅ Kanca cozuldu, yeni eylem gecerli")
    hata2 = loop.kanca_denetle("test_kanca", "ALT_AJAN_GOREVLENDIR")
    assert hata2 is not None, "Yasakli arac bloke etmeli"
    print(f"  ✅ Yasakli arac engellendi")

    # Test 3: Gozlem
    import time as _t
    _uid = str(int(_t.time()))
    loop.gozlem_kaydet(f"test_gozlem_{_uid}", 2.5, "merhaba", basarili=True,
                        girdi_token=50, cikti_token=100)
    loop.gozlem_kaydet(f"test_gozlem_{_uid}", 1.2, "nasilsin", basarili=True)
    loop.gozlem_kaydet(f"test_hata_{_uid}", 0.5, "", basarili=False, notlar="TIMEOUT")
    ozet = loop.gozlem_ozet(f"test_gozlem_{_uid}")
    assert ozet["cagri_sayisi"] == 2, "2 cagri olmali"
    print(f"  ✅ Gozlem: {ozet['cagri_sayisi']} cagri, ${ozet['tahmini_maliyet_usd']:.6f}")

    # Test 4: Genel durum
    d = loop.durum()
    print(f"  ✅ Steering durum: {d['katman1_hafiza']['toplam_kayit']} kayit, "
          f"{d['katman5_gozlem']['toplam_cagri']} cagri, "
          f"{d['katman4_kanca']['aktif_task']} aktif")

    # Temizlik
    loop.kanca_temizle("test_kanca")
    print()
    print("✅ TUM KATMANLAR CALISIYOR")
