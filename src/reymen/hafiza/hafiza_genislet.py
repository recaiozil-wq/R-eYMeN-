# -*- coding: utf-8 -*-
"""
hafiza_genislet.py — ReYMeN Gelişmiş Hafıza Sistemi.

ReYMeN Agent'in SQLite FTS5 tabanlı session hafızasına benzer bir sistem.
Özellikler:
  - SQLite + FTS5 tam metin arama
  - Oturum (session) bazlı konuşma geçmişi
  - Kullanıcı tercihleri kalıcı kaydı
  - Cross-session arama (geçmiş oturumlarda ara)
  - Otomatik kayıt (her N mesajda bir checkpoint)

Kullanim:
    from hafiza_genislet import hafiza
    hafiza.initialize("oturum_123")
    hafiza.kaydet("Python decorator nedir?", "kullanici_sorusu")
    sonuc = hafiza.ara("decorator")
    tercih = hafiza.tercih_al("dil", default="Türkçe")
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# SQLite (standart kütüphane)
try:
    import sqlite3
    _SQLITE_AVAILABLE = True
except ImportError:
    _SQLITE_AVAILABLE = False

logger = logging.getLogger(__name__)

# ── Sabitler ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.resolve()
_DB_DIR = ROOT / "merkez_db"
_DB_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = str(_DB_DIR / "hafiza.db")

# Koleksiyon (tablo) adlari
_COLL_KONUSMA = "konusmalar"       # Kullanici-ajan konusmalari
_COLL_NOTLAR = "notlar"            # Kisa notlar / hatirlatmalar
_COLL_TERCIHLER = "kullanici_tercihleri"  # Kullanici tercihleri (key-value)
_COLL_SESSIONS = "session_ozetleri"       # Session ozetleri

_MAX_KAYIT_PER_SESSION = 500       # Session basina max kayit

# Turkce stop words (konu_cikar() icin)
_TURKCE_STOP_WORDS = frozenset({
    "acaba", "alti", "ama", "ancak", "bana", "bazi", "bazı", "belki",
    "bende", "beni", "benim", "beri", "bile", "bir", "biraz", "biri",
    "birkaç", "birsey", "birşey", "biz", "bize", "bizi", "bizim",
    "boyle", "bunca", "bunda", "bundan", "bunlar", "bunlari", "bunları",
    "bunlardan", "bunlarin", "bunların", "bunu", "bunun", "burada",
    "böyle", "bu", "buna",
    "da", "daha", "dahi", "de", "defa", "diye", "diğer", "diger",
    "dolayi", "dolayı", "dolayisiyla", "dolayısıyla",
    "eger", "elbette", "en", "evet", "eğer",
    "fakat", "falan", "filan",
    "gene", "gibi", "göre", "gore",
    "halen", "hangi", "hani", "hatta", "hem", "henuz", "henüz",
    "hep", "hepsi", "her", "herhalde", "herhangi", "herkes",
    "hic", "hicbir", "hâlâ", "hiç", "hiçbir",
    "icin", "ile", "ilgili", "ise", "ister",
    "itibaren", "itibariyle", "için", "içinde", "işte",
    "kadar", "karsi", "karsin", "karsı", "karşın", "kendine",
    "kendini", "kendi", "kendisi", "kez", "ki", "kim", "kime",
    "kimi", "kimin", "kimse",
    "madem", "mi", "milyon", "mu", "mü", "mı",
    "nasil", "nasıl", "ne", "neden", "nedenle", "nerde", "nerede",
    "nereli", "neyse", "nice", "niye", "niçin", "nu", "nun",
    "o", "olan", "olarak", "oldu", "oldugu", "olduğu", "olmadı",
    "olmak", "olsa", "olur", "ona", "ondan", "onlar", "onlari",
    "onlardan", "onlarin", "onları", "onların", "onu", "onun",
    "orada", "oysa", "oysaki",
    "pek", "rağmen",
    "sadece", "sanki", "sen", "siz", "sizin", "soyle", "söyle",
    "su", "suna", "sunda", "sundan", "sunu", "sunun",
    "seye", "sey", "şu", "şuna", "şunda", "şundan",
    "şunları", "şunu", "şey", "şeye", "şeyi",
    "tarafindan", "tarafından", "tum", "tüm",
    "uzere", "üzerinde", "üzere",
    "var", "ve", "veya", "veyahut",
    "ya", "yani", "yapacak", "yapilan", "yapılan", "yapmak",
    "yapti", "yaptı", "yeter", "yine", "yo", "yoksa", "zaten",
})

# Thread-safe yazma
_yazma_kilit = threading.Lock()


# ══════════════════════════════════════════════════════════════════════════
# GELISMIS HAFIZA SINIFI (SQLite + FTS5)
# ══════════════════════════════════════════════════════════════════════════

class GelismisHafiza:
    """ReYMeN session_search + memory sisteminin ReYMeN uyarlamasi.

    SQLite + FTS5 ile:
      - Konusmalari koleksiyon bazinda kaydetme
      - FTS5 tam metin arama (LIKE'den cok daha hizli ve dogru)
      - Kullanici tercihlerini key-value olarak saklama
      - Session bazinda izolasyon + cross-session arama
      - Otomatik eski kayit temizleme (TTL)
    """

    def __init__(self, db_yolu: str = _DB_PATH) -> None:
        self._db_yolu = db_yolu
        self._conn: Optional[sqlite3.Connection] = None
        self._aktif_session: str = ""
        self._mesaj_sayaci = 0
        self._otomatik_kayit_esigi = 10  # Her 10 mesajda checkpoint
        self._hazir = False

        if _SQLITE_AVAILABLE:
            self._baglan()
            self._tablolari_olustur()
            self._hazir = True
        else:
            print("[Hafiza] sqlite3 modulu bulunamadi! Hafiza devre disi.")

    # ── Dahili ──────────────────────────────────────────────────────────

    def _baglan(self) -> None:
        """SQLite baglantisi ac (WAL modu + Row factory)."""
        try:
            self._conn = sqlite3.connect(self._db_yolu, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        except sqlite3.Error as e:
            print(f"[Hafiza] Baglanti hatasi: {e}")
            raise

    def _tablolari_olustur(self) -> None:
        """Tablolari + FTS5 virtual table + index'leri olustur."""
        if not self._conn:
            return
        try:
            c = self._conn.cursor()

            # Ana kayit tablosu (tum koleksiyonlar icin)
            c.execute("""
                CREATE TABLE IF NOT EXISTS kayitlar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    koleksiyon TEXT NOT NULL,
                    anahtar TEXT DEFAULT '',
                    icerik TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    zaman REAL NOT NULL,
                    expire_zaman REAL DEFAULT 0
                )
            """)

            # Session tablosu
            c.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    baslik TEXT DEFAULT '',
                    baslangic REAL NOT NULL,
                    bitis REAL DEFAULT 0,
                    mesaj_sayisi INTEGER DEFAULT 0,
                    ozet TEXT DEFAULT ''
                )
            """)

            # Kullanici tercihleri tablosu (key-value)
            c.execute("""
                CREATE TABLE IF NOT EXISTS tercihler (
                    anahtar TEXT PRIMARY KEY,
                    deger TEXT NOT NULL,
                    guncelleme_zamani REAL NOT NULL
                )
            """)

            # FTS5 virtual table — tam metin arama
            # icerik + metadata + anahtar alanlarinda ara
            c.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS kayitlar_fts USING fts5(
                    icerik, metadata, anahtar,
                    content='kayitlar',
                    content_rowid='id',
                    tokenize='unicode61'
                )
            """)

            # Index'ler
            c.execute("CREATE INDEX IF NOT EXISTS idx_kayit_session ON kayitlar(session_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_kayit_koleksiyon ON kayitlar(koleksiyon)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_kayit_zaman ON kayitlar(zaman)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_kayit_expire ON kayitlar(expire_zaman)")

            # FTS5 content sync trigger'ları
            c.execute("""
                CREATE TRIGGER IF NOT EXISTS kayitlar_ai AFTER INSERT ON kayitlar BEGIN
                    INSERT INTO kayitlar_fts(rowid, icerik, metadata, anahtar)
                    VALUES (new.id, new.icerik, new.metadata, new.anahtar);
                END
            """)
            c.execute("""
                CREATE TRIGGER IF NOT EXISTS kayitlar_ad AFTER DELETE ON kayitlar BEGIN
                    INSERT INTO kayitlar_fts(kayitlar_fts, rowid, icerik, metadata, anahtar)
                    VALUES ('delete', old.id, old.icerik, old.metadata, old.anahtar);
                END
            """)
            c.execute("""
                CREATE TRIGGER IF NOT EXISTS kayitlar_au AFTER UPDATE ON kayitlar BEGIN
                    INSERT INTO kayitlar_fts(kayitlar_fts, rowid, icerik, metadata, anahtar)
                    VALUES ('delete', old.id, old.icerik, old.metadata, old.anahtar);
                    INSERT INTO kayitlar_fts(rowid, icerik, metadata, anahtar)
                    VALUES (new.id, new.icerik, new.metadata, new.anahtar);
                END
            """)

            self._conn.commit()
        except sqlite3.Error as e:
            print(f"[Hafiza] Tablo olusturma hatasi: {e}")

    def _koleksiyon_id(self, koleksiyon: str) -> int:
        """Koleksiyon adindan ID al (yoksa olustur). Artik gerekmiyor."""
        return 0

    # ── Session Yonetimi ────────────────────────────────────────────────

    def initialize(self, session_id: str, baslik: str = "") -> None:
        """Yeni bir oturum baslat. Her bot konusmasi bir session'dir."""
        if not self._hazir or not self._conn:
            return
        self._aktif_session = session_id
        self._mesaj_sayaci = 0

        try:
            c = self._conn.cursor()
            c.execute(
                "INSERT OR IGNORE INTO sessions (id, baslik, baslangic) VALUES (?, ?, ?)",
                (session_id, baslik, time.time())
            )
            self._conn.commit()
        except sqlite3.Error as _hafiza_g_e245:
            print(f"[UYARI] hafiza_genislet.py:246 - {_hafiza_g_e245}")

    def session_bitir(self, ozet: str = "") -> None:
        """Aktif session'i sonlandir."""
        if not self._aktif_session or not self._hazir or not self._conn:
            return
        try:
            c = self._conn.cursor()
            c.execute(
                "UPDATE sessions SET bitis=?, mesaj_sayisi=?, ozet=? WHERE id=?",
                (time.time(), self._mesaj_sayaci, ozet[:500], self._aktif_session)
            )
            self._conn.commit()
        except sqlite3.Error as _hafiza_g_e259:
            print(f"[UYARI] hafiza_genislet.py:260 - {_hafiza_g_e259}")
        self._aktif_session = ""

    # ── Kayit Islemleri ─────────────────────────────────────────────────

    def kaydet(self, icerik: str, koleksiyon: str = _COLL_KONUSMA,
               anahtar: str = "", metadata: dict = None,
               ttl_saat: float = 0) -> bool:
        """Hafizaya bir kayit ekle. FTS5 otomatik indexlenir.

        Args:
            icerik: Kaydedilecek metin
            koleksiyon: 'konusmalar', 'notlar', 'kullanici_tercihleri'
            anahtar: Opsiyonel anahtar kelime (arama icin)
            metadata: Opsiyonel ek bilgiler (JSON)
            ttl_saat: 0 = sonsuz, >0 = su kadar saat sonra expire

        Returns:
            bool: Basarili mi?
        """
        if not self._hazir or not self._conn:
            return False
        try:
            expire = (time.time() + ttl_saat * 3600) if ttl_saat > 0 else 0
            meta_json = json.dumps(metadata or {}, ensure_ascii=False)

            with _yazma_kilit:
                c = self._conn.cursor()
                c.execute(
                    """INSERT INTO kayitlar
                       (session_id, koleksiyon, anahtar, icerik, metadata, zaman, expire_zaman)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (self._aktif_session or "genel", koleksiyon,
                     anahtar[:200], icerik, meta_json, time.time(), expire)
                )
                self._conn.commit()
                self._mesaj_sayaci += 1

            # Otomatik checkpoint (her 10 mesajda)
            if self._mesaj_sayaci % self._otomatik_kayit_esigi == 0:
                self._checkpoint()

            return True
        except sqlite3.Error:
            return False

    def kayit_guncelle(self, kayit_id: int, yeni_icerik: str = "",
                       yeni_metadata: dict = None) -> bool:
        """Varolan bir kaydi guncelle (FTS5 trigger ile sync olur)."""
        if not self._hazir or not self._conn:
            return False
        try:
            with _yazma_kilit:
                c = self._conn.cursor()
                if yeni_icerik:
                    c.execute(
                        "UPDATE kayitlar SET icerik=?, zaman=? WHERE id=?",
                        (yeni_icerik, time.time(), kayit_id)
                    )
                if yeni_metadata is not None:
                    c.execute(
                        "UPDATE kayitlar SET metadata=?, zaman=? WHERE id=?",
                        (json.dumps(yeni_metadata), time.time(), kayit_id)
                    )
                self._conn.commit()
            return True
        except sqlite3.Error:
            return False

    # ── Arama ────────────────────────────────────────────────────────────

    def ara(self, sorgu: str, koleksiyon: str = "",
            limit: int = 10, session_id: str = "") -> List[Dict[str, Any]]:
        """FTS5 ile tam metin arama yap.

        Args:
            sorgu: FTS5 sorgusu (ornek: 'decorator AND python')
            koleksiyon: Bos = tum koleksiyonlarda ara
            limit: Maks sonuc sayisi
            session_id: Sadece belirli session'da ara (bos = tumu)

        Returns:
            Liste: [{"id", "session_id", "koleksiyon", "icerik", "zaman", "skor"}, ...]
        """
        if not self._hazir or not self._conn or not sorgu.strip():
            return []

        # FTS5 query escape — ozel karakterleri temizle
        fts_sorgu = self._fts_escape(sorgu.strip())

        try:
            c = self._conn.cursor()
            kosullar = []
            params = []

            if koleksiyon:
                kosullar.append("k.koleksiyon = ?")
                params.append(koleksiyon)
            if session_id:
                kosullar.append("k.session_id = ?")
                params.append(session_id)

            where = ("AND " + " AND ".join(kosullar)) if kosullar else ""

            sql = f"""
                SELECT k.id, k.session_id, k.koleksiyon, k.anahtar,
                       k.icerik, k.zaman, k.metadata,
                       fts.rank as skor
                FROM kayitlar_fts fts
                JOIN kayitlar k ON k.id = fts.rowid
                WHERE kayitlar_fts MATCH ?
                {where}
                AND (k.expire_zaman = 0 OR k.expire_zaman > ?)
                ORDER BY fts.rank
                LIMIT ?
            """
            params.insert(0, fts_sorgu)
            params.append(time.time())
            params.append(limit)

            c.execute(sql, params)
            sonuclar = []
            for row in c.fetchall():
                doc = {
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "koleksiyon": row["koleksiyon"],
                    "anahtar": row["anahtar"],
                    "icerik": row["icerik"][:500],
                    "zaman": row["zaman"],
                    "skor": round(row["skor"], 2),
                }
                try:
                    meta = json.loads(row["metadata"])
                    if meta:
                        doc.update(meta)
                except (json.JSONDecodeError, TypeError) as _hafiza_g_e396:
                    print(f"[UYARI] hafiza_genislet.py:397 - {_hafiza_g_e396}")
                sonuclar.append(doc)
            return sonuclar

        except sqlite3.Error as e:
            print(f"[Hafiza] Arama hatasi: {e}")
            # FTS5 hatasi olursa LIKE fallback
            return self._ara_like(sorgu, koleksiyon, limit, session_id)

    def _ara_like(self, sorgu: str, koleksiyon: str = "",
                  limit: int = 10, session_id: str = "") -> List[Dict[str, Any]]:
        """FTS5 calismazsa LIKE ile yedek arama."""
        if not self._conn:
            return []
        try:
            c = self._conn.cursor()
            kosullar = ["k.icerik LIKE ?"]
            params = [f"%{sorgu}%"]
            if koleksiyon:
                kosullar.append("k.koleksiyon = ?")
                params.append(koleksiyon)
            if session_id:
                kosullar.append("k.session_id = ?")
                params.append(session_id)
            kosullar.append("(k.expire_zaman = 0 OR k.expire_zaman > ?)")
            params.append(time.time())

            c.execute(
                f"SELECT k.* FROM kayitlar k WHERE {' AND '.join(kosullar)} ORDER BY k.zaman DESC LIMIT ?",
                params + [limit]
            )
            sonuclar = []
            for row in c.fetchall():
                d = dict(row)
                d["skor"] = 0.0  # LIKE'da skor yok
                sonuclar.append(d)
            return sonuclar
        except sqlite3.Error:
            return []

    def _fts_escape(self, sorgu: str) -> str:
        """FTS5 ozel karakterlerini temizle."""
        # FTS5 ozel karakterleri: ^ * " ( ) ~ + -
        # Basit sorgu icin fazla karakterleri temizle
        import re
        # Kelimeleri al, FTS5 AND ile birlestir
        kelimeler = re.findall(r'\w+', sorgu)
        if not kelimeler:
            return sorgu
        return " AND ".join(kelimeler[:10])  # max 10 kelime

    def arama_sirala(self, sorgu: str, koleksiyon: str = "",
                     limit: int = 10, session_id: str = "") -> List[Dict[str, Any]]:
        """FTS5 arama sonuclarini akilli sirala.

        Tam eslesme once, kismi eslesme sonra gelir.
        Son kullanilma tarihine gore bonus puan eklenir.

        Args:
            sorgu: Aranacak metin
            koleksiyon: Bos = tum koleksiyonlarda ara
            limit: Maks sonuc sayisi
            session_id: Sadece belirli session'da ara (bos = tumu)

        Returns:
            Liste: [{"id", "session_id", "koleksiyon", "icerik", "zaman",
                      "skor", "bonus_puan", "toplam_puan"}, ...]
        """
        if not self._hazir or not self._conn or not sorgu.strip():
            return []

        try:
            # 1. FTS5 ile ham sonuclari al
            fts_sorgu = self._fts_escape(sorgu.strip())
            c = self._conn.cursor()

            kosullar = []
            params = []

            if koleksiyon:
                kosullar.append("k.koleksiyon = ?")
                params.append(koleksiyon)
            if session_id:
                kosullar.append("k.session_id = ?")
                params.append(session_id)

            where = ("AND " + " AND ".join(kosullar)) if kosullar else ""

            sql = f"""
                SELECT k.id, k.session_id, k.koleksiyon, k.anahtar,
                       k.icerik, k.zaman, k.metadata,
                       fts.rank as skor
                FROM kayitlar_fts fts
                JOIN kayitlar k ON k.id = fts.rowid
                WHERE kayitlar_fts MATCH ?
                {where}
                AND (k.expire_zaman = 0 OR k.expire_zaman > ?)
                ORDER BY fts.rank
                LIMIT ?
            """
            params.insert(0, fts_sorgu)
            params.append(time.time())
            params.append(limit * 3)  # Filtreleme icin fazla al

            c.execute(sql, params)
            ham_sonuclar = c.fetchall()

            if not ham_sonuclar:
                # FTS5 sonuc vermezse LIKE fallback
                like_sql = f"""
                    SELECT k.id, k.session_id, k.koleksiyon, k.anahtar,
                           k.icerik, k.zaman, k.metadata, 0.0 as skor
                    FROM kayitlar k
                    WHERE k.icerik LIKE ?
                    {where.replace('k.koleksiyon', 'k.koleksiyon').replace('k.session_id', 'k.session_id') if kosullar else ''}
                    AND (k.expire_zaman = 0 OR k.expire_zaman > ?)
                    ORDER BY k.zaman DESC
                    LIMIT ?
                """
                like_params = [f"%{sorgu.strip()}%"]
                if koleksiyon:
                    like_params.append(koleksiyon)
                if session_id:
                    like_params.append(session_id)
                like_params.append(time.time())
                like_params.append(limit * 3)
                c.execute(like_sql, like_params)
                ham_sonuclar = c.fetchall()

            # 2. Skorlama ve siralam
            simdi = time.time()
            son_kelimeler = sorgu.strip().lower().split()

            puanlanmis = []
            for row in ham_sonuclar:
                try:
                    icerik_lower = row["icerik"].lower()
                    toplam_puan = 0.0
                    tam_eslesme_sayisi = 0
                    kismi_eslesme_sayisi = 0

                    for kelime in son_kelimeler:
                        # Tam eslesme kontrolu (kelime bazinda)
                        if f" {kelime} " in f" {icerik_lower} ":
                            tam_eslesme_sayisi += 1
                            toplam_puan += 3.0  # Tam eslesme bonusu
                        # Kismi eslesme
                        elif kelime in icerik_lower:
                            kismi_eslesme_sayisi += 1
                            toplam_puan += 1.0  # Kismi eslesme puani

                    # Anahtarda eslesme bonusu
                    anahtar_lower = row["anahtar"].lower() if row["anahtar"] else ""
                    for kelime in son_kelimeler:
                        if kelime in anahtar_lower:
                            toplam_puan += 2.0

                    # Zaman bonusu (son kullanilma = yuksek puan)
                    # Son 1 saat: +5, son 24 saat: +3, son 7 gun: +1
                    kayit_zamani = row["zaman"]
                    saat_farki = (simdi - kayit_zamani) / 3600
                    if saat_farki < 1:
                        toplam_puan += 5.0
                    elif saat_farki < 24:
                        toplam_puan += 3.0
                    elif saat_farki < 168:  # 7 gun
                        toplam_puan += 1.0

                    # FTS5 rank'ini de ekle (negatif -> pozitif)
                    fts_rank = row["skor"] if row["skor"] else 0.0
                    toplam_puan += max(0, -fts_rank) * 0.5

                    doc = {
                        "id": row["id"],
                        "session_id": row["session_id"],
                        "koleksiyon": row["koleksiyon"],
                        "anahtar": row["anahtar"],
                        "icerik": row["icerik"][:500],
                        "zaman": row["zaman"],
                        "skor": round(row["skor"], 2),
                        "bonus_puan": round(toplam_puan, 2),
                        "toplam_puan": round(tam_eslesme_sayisi * 3.0 + kismi_eslesme_sayisi * 1.0 + (toplam_puan - tam_eslesme_sayisi * 3.0 - kismi_eslesme_sayisi * 1.0), 2),
                        "tam_eslesme": tam_eslesme_sayisi,
                        "kismi_eslesme": kismi_eslesme_sayisi,
                    }
                    try:
                        meta = json.loads(row["metadata"])
                        if meta:
                            doc.update(meta)
                    except (json.JSONDecodeError, TypeError) as _hafiza_g_e586:
                        print(f"[UYARI] hafiza_genislet.py:587 - {_hafiza_g_e586}")
                    puanlanmis.append((toplam_puan, doc))
                except Exception:
                    continue

            # 3. Puana gore sirala (buyukten kucuge)
            puanlanmis.sort(key=lambda x: x[0], reverse=True)

            # Sonucu limit kadar kes
            sonuclar = [doc for _, doc in puanlanmis[:limit]]
            logger.info(f"arama_sirala: '{sorgu}' -> {len(sonuclar)} sonuc (ham: {len(ham_sonuclar)})")
            return sonuclar

        except sqlite3.Error as e:
            logger.error(f"arama_sirala FTS5 hatasi: {e}")
            return []
        except Exception as e:
            logger.error(f"arama_sirala beklenmeyen hata: {e}")
            return []

    # ── Kullanici Tercihleri ─────────────────────────────────────────────

    def tercih_kaydet(self, anahtar: str, deger: str) -> bool:
        """Kullanici tercihini kaydet (ornek: dil='Turkce')."""
        if not self._hazir or not self._conn:
            return False
        try:
            c = self._conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO tercihler (anahtar, deger, guncelleme_zamani) VALUES (?, ?, ?)",
                (anahtar.strip().lower(), deger, time.time())
            )
            self._conn.commit()
            return True
        except sqlite3.Error:
            return False

    def tercih_al(self, anahtar: str, default: str = "") -> str:
        """Kullanici tercihini oku."""
        if not self._hazir or not self._conn:
            return default
        try:
            c = self._conn.cursor()
            c.execute(
                "SELECT deger FROM tercihler WHERE anahtar = ?",
                (anahtar.strip().lower(),)
            )
            row = c.fetchone()
            return row["deger"] if row else default
        except sqlite3.Error:
            return default

    def tercih_listele(self) -> List[Dict[str, Any]]:
        """Tum kullanici tercihlerini listele."""
        if not self._hazir or not self._conn:
            return []
        try:
            c = self._conn.cursor()
            c.execute("SELECT * FROM tercihler ORDER BY guncelleme_zamani DESC")
            return [dict(row) for row in c.fetchall()]
        except sqlite3.Error:
            return []

    def tercih_sil(self, anahtar: str) -> bool:
        """Bir tercihi sil."""
        if not self._hazir or not self._conn:
            return False
        try:
            c = self._conn.cursor()
            c.execute("DELETE FROM tercihler WHERE anahtar = ?", (anahtar.strip().lower(),))
            self._conn.commit()
            return True
        except sqlite3.Error:
            return False

    # ── Session Gecmisi ──────────────────────────────────────────────────

    def session_ara(self, sorgu: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Gecmis session'larda (konusma icerigi + ozetler) FTS5 ara.

        ReYMeN session_search() benzeri:
          - Once konusma koleksiyonunda ara
          - Sonra session ozetlerinde ara
          - Sonuclari birlestirip sirala

        Args:
            sorgu: FTS5 sorgusu (ornek: 'decorator' veya 'python AND decorator')
            limit: Maks sonuc sayisi

        Returns:
            Liste: [{"session_id", "icerik", "zaman", "koleksiyon", "skor"}, ...]
        """
        if not self._hazir or not self._conn or not sorgu.strip():
            return []

        try:
            c = self._conn.cursor()
            fts_sorgu = self._fts_escape(sorgu.strip())

            # Once konusma koleksiyonunda ara (en alakali)
            # Sonra session ozetlerinde ara
            sql = """
                SELECT k.session_id, k.koleksiyon, k.anahtar,
                       substr(k.icerik, 1, 500) as icerik,
                       k.zaman, fts.rank as skor
                FROM kayitlar_fts fts
                JOIN kayitlar k ON k.id = fts.rowid
                WHERE kayitlar_fts MATCH ?
                  AND k.koleksiyon IN (?, ?)
                  AND (k.expire_zaman = 0 OR k.expire_zaman > ?)
                ORDER BY
                  CASE WHEN k.koleksiyon = ? THEN 0 ELSE 1 END,
                  fts.rank
                LIMIT ?
            """
            c.execute(sql, (
                fts_sorgu,
                _COLL_KONUSMA, _COLL_SESSIONS,
                time.time(),
                _COLL_KONUSMA,
                limit,
            ))
            sonuclar = []
            for row in c.fetchall():
                sonuclar.append({
                    "session_id": row["session_id"],
                    "koleksiyon": row["koleksiyon"],
                    "anahtar": row["anahtar"],
                    "icerik": row["icerik"],
                    "zaman": row["zaman"],
                    "skor": round(row["skor"], 2),
                })
            return sonuclar

        except sqlite3.Error as e:
            logger.error(f"session_ara FTS5 hatasi: {e}")
            # FTS5 calismazsa LIKE fallback
            return self._session_ara_like(sorgu, limit)

    def _session_ara_like(self, sorgu: str, limit: int = 5) -> List[Dict[str, Any]]:
        """FTS5 calismazsa LIKE ile yedek session arama."""
        if not self._conn:
            return []
        try:
            c = self._conn.cursor()
            c.execute("""
                SELECT session_id, koleksiyon, anahtar,
                       substr(icerik, 1, 500) as icerik,
                       zaman, 0.0 as skor
                FROM kayitlar
                WHERE koleksiyon IN (?, ?)
                  AND icerik LIKE ?
                  AND (expire_zaman = 0 OR expire_zaman > ?)
                ORDER BY zaman DESC
                LIMIT ?
            """, (_COLL_KONUSMA, _COLL_SESSIONS, f"%{sorgu}%", time.time(), limit))
            return [dict(row) for row in c.fetchall()]
        except sqlite3.Error:
            return []

    def session_listele(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Son session'lari listele."""
        if not self._hazir or not self._conn:
            return []
        try:
            c = self._conn.cursor()
            c.execute(
                "SELECT * FROM sessions ORDER BY baslangic DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in c.fetchall()]
        except sqlite3.Error:
            return []

    def session_kayitlari(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Bir session'daki tum kayitlari getir."""
        if not self._hazir or not self._conn:
            return []
        try:
            c = self._conn.cursor()
            c.execute(
                """SELECT id, koleksiyon, anahtar, substr(icerik, 1, 300) as icerik,
                          zaman, metadata
                   FROM kayitlar
                   WHERE session_id = ?
                   ORDER BY zaman ASC
                   LIMIT ?""",
                (session_id, limit)
            )
            return [dict(row) for row in c.fetchall()]
        except sqlite3.Error:
            return []

    def konu_cikar(self, session_id: str, limit: int = 5) -> List[str]:
        """Bir session'daki mesajlardan anahtar kelimeleri/konulari cikar.

        TF-IDF benzeri basit frekans analizi ile en cok gecen kelimeleri
        bulur. Turkce stop words haric tutulur.

        Args:
            session_id: Konu cikarilacak session ID'si
            limit: Kac tane konu dondurulecegi (default: 5)

        Returns:
            Liste: En cok gecen kelimeler (ornek: ["decorator", "python", "fonksiyon"])
        """
        if not self._hazir or not self._conn or not session_id:
            logger.warning(f"konu_cikar: gecersiz session_id='{session_id}'")
            return []

        try:
            c = self._conn.cursor()
            c.execute(
                """SELECT icerik FROM kayitlar
                   WHERE session_id = ? AND koleksiyon = ?
                   AND (expire_zaman = 0 OR expire_zaman > ?)""",
                (session_id, _COLL_KONUSMA, time.time())
            )
            satirlar = c.fetchall()

            if not satirlar:
                logger.info(f"konu_cikar: session '{session_id}' icin kayit bulunamadi")
                return []

            # 1. Tum metinleri birlestir ve tokenize et
            import re
            tum_metin = " ".join(row["icerik"] or "" for row in satirlar)
            kelimeler = re.findall(r'[a-zA-ZğüşıöçĞÜŞİÖÇ0-9]+', tum_metin.lower())

            # 2. Stop words + kisa kelimeleri filtrele
            filtrelenmis = [
                k for k in kelimeler
                if len(k) > 2 and k not in _TURKCE_STOP_WORDS
            ]

            if not filtrelenmis:
                logger.info(f"konu_cikar: session '{session_id}' icin anlamli kelime bulunamadi")
                return []

            # 3. Frekans sayimi
            frekans: Dict[str, int] = {}
            for kelime in filtrelenmis:
                frekans[kelime] = frekans.get(kelime, 0) + 1

            # 4. En cok gecen kelimeleri sirala
            sirali = sorted(frekans.items(), key=lambda x: x[1], reverse=True)

            # 5. TF-IDF benzeri: session icindeki goreli frekans
            #    varsa tum kayitlardaki genel frekans ile normalize et
            toplam_kelime = len(filtrelenmis)
            konular = []
            for kelime, sayi in sirali[:limit * 3]:  # Once fazla al, sonra TF-IDF ile kes
                # Goreli frekans (TF)
                tf = sayi / toplam_kelime if toplam_kelime > 0 else 0

                # Genel frekans (IDF benzeri) — tum kayitlarda kac satirda gecmis
                c.execute(
                    """SELECT COUNT(DISTINCT id) as n FROM kayitlar
                       WHERE icerik LIKE ? AND koleksiyon = ?
                       AND (expire_zaman = 0 OR expire_zaman > ?)""",
                    (f"%{kelime}%", _COLL_KONUSMA, time.time())
                )
                genel_sayi = c.fetchone()["n"] or 1
                idf_benzeri = max(0.1, 1.0 / genel_sayi)

                # TF-IDF skoru
                tfidf_skor = tf * idf_benzeri
                konular.append((kelime, round(tfidf_skor, 6)))

            # TF-IDF skoruna gore sirala
            konular.sort(key=lambda x: x[1], reverse=True)

            # Sadece kelimeleri dondur
            sonuc = [k[0] for k in konular[:limit]]
            logger.info(
                f"konu_cikar: session '{session_id}' -> "
                f"{len(sonuc)} konu: {', '.join(sonuc)} "
                f"(toplam {len(satirlar)} kayit, {toplam_kelime} kelime)"
            )
            return sonuc

        except sqlite3.Error as e:
            logger.error(f"konu_cikar SQL hatasi: {e}")
            return []
        except Exception as e:
            logger.error(f"konu_cikar beklenmeyen hata: {e}")
            return []

    def session_birlestir(self, hedef_session_id: str, kaynak_session_id: str) -> bool:
        """Iki session ID'sini birlestir.

        Kaynak session'daki tum kayitlari hedef session altina tasir,
        ardindan kaynak session'i siler.

        Args:
            hedef_session_id: Korunacak session (kayitlar buraya tasinir)
            kaynak_session_id: Silinecek session (kayitlari tasinir)

        Returns:
            bool: Basarili mi?
        """
        if not self._hazir or not self._conn:
            logger.warning("session_birlestir: hafiza hazir degil")
            return False

        if not hedef_session_id or not kaynak_session_id:
            logger.warning("session_birlestir: gecersiz session ID'leri")
            return False

        if hedef_session_id == kaynak_session_id:
            logger.info(f"session_birlestir: ayni session ID ({hedef_session_id}), birlestirme gerekmez")
            return True

        try:
            c = self._conn.cursor()

            with _yazma_kilit:
                # 1. Hedef session var mi kontrol et, yoksa olustur
                c.execute("SELECT id FROM sessions WHERE id = ?", (hedef_session_id,))
                if not c.fetchone():
                    c.execute(
                        "INSERT INTO sessions (id, baslik, baslangic) VALUES (?, ?, ?)",
                        (hedef_session_id, f"Birlestirilmis: {hedef_session_id}", time.time())
                    )
                    logger.info(f"session_birlestir: hedef session '{hedef_session_id}' olusturuldu")

                # 2. Kaynak session'daki kayitlari hedef session'a tasi
                c.execute(
                    "UPDATE kayitlar SET session_id = ? WHERE session_id = ?",
                    (hedef_session_id, kaynak_session_id)
                )
                tasinan_kayit = c.rowcount

                # 3. Kaynak session'i sil
                c.execute("DELETE FROM sessions WHERE id = ?", (kaynak_session_id,))
                session_silindi = c.rowcount > 0

                # 4. Hedef session ozetini guncelle
                c.execute("SELECT COUNT(*) as n FROM kayitlar WHERE session_id = ?",
                          (hedef_session_id,))
                toplam_kayit = c.fetchone()["n"]

                # Konulari cikar ve baslik olarak ekle
                try:
                    konular = self.konu_cikar(hedef_session_id, limit=3)
                    yeni_baslik = ", ".join(konular) if konular else f"Session: {hedef_session_id[:20]}"
                except Exception:
                    yeni_baslik = f"Session: {hedef_session_id[:20]}"

                c.execute(
                    "UPDATE sessions SET mesaj_sayisi=?, baslik=?, "
                    "bitis=COALESCE(NULLIF(bitis, 0), ?) WHERE id=?",
                    (toplam_kayit, yeni_baslik, time.time(), hedef_session_id)
                )

                self._conn.commit()

            logger.info(
                f"session_birlestir: '{kaynak_session_id}' -> '{hedef_session_id}' | "
                f"{tasinan_kayit} kayit tasindi, session silindi={session_silindi}"
            )
            return True

        except sqlite3.Error as e:
            logger.error(f"session_birlestir SQL hatasi: {e}")
            try:
                self._conn.rollback()
            except Exception as _hafiza_g_e954:
                print(f"[UYARI] hafiza_genislet.py:955 - {_hafiza_g_e954}")
            return False
        except Exception as e:
            logger.error(f"session_birlestir beklenmeyen hata: {e}")
            return False

    # ── Notlar (Kisa Hatirlatmalar) ──────────────────────────────────────

    def not_ekle(self, baslik: str, icerik: str = "",
                 ttl_saat: float = 0) -> bool:
        """Kisa bir not/hatirlatma ekle. _COLL_NOTLAR koleksiyonuna kaydeder."""
        return self.kaydet(
            icerik=icerik or baslik,
            koleksiyon=_COLL_NOTLAR,
            anahtar=baslik[:200],
            ttl_saat=ttl_saat
        )

    def notlari_listele(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Tum aktif notlari listele."""
        if not self._hazir or not self._conn:
            return []
        try:
            c = self._conn.cursor()
            c.execute(
                """SELECT * FROM kayitlar
                   WHERE koleksiyon = ?
                   AND (expire_zaman = 0 OR expire_zaman > ?)
                   ORDER BY zaman DESC LIMIT ?""",
                (_COLL_NOTLAR, time.time(), limit)
            )
            return [dict(row) for row in c.fetchall()]
        except sqlite3.Error:
            return []

    # ── Bakim ────────────────────────────────────────────────────────────

    def _checkpoint(self) -> None:
        """WAL checkpoint + eski kayit temizleme."""
        if not self._conn:
            return
        try:
            self._conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        except sqlite3.Error as _hafiza_g_e998:
            print(f"[UYARI] hafiza_genislet.py:999 - {_hafiza_g_e998}")

    def temizle(self, yas_saat: float = 72.0) -> int:
        """72 saatten eski expire kayitlari temizle."""
        if not self._hazir or not self._conn:
            return 0
        try:
            c = self._conn.cursor()
            esik = time.time() - yas_saat * 3600
            c.execute(
                "DELETE FROM kayitlar WHERE expire_zaman > 0 AND expire_zaman < ?",
                (esik,)
            )
            silinen = c.rowcount
            self._conn.commit()
            self._checkpoint()
            return silinen
        except sqlite3.Error:
            return 0

    def durum(self) -> dict:
        """Hafiza istatistikleri."""
        if not self._hazir or not self._conn:
            return {"aktif": False, "backend": "sqlite", "hata": "baglanti yok"}
        try:
            c = self._conn.cursor()
            c.execute("SELECT COUNT(*) as n FROM kayitlar")
            toplam = c.fetchone()["n"]
            c.execute("SELECT COUNT(*) as n FROM sessions")
            session_sayisi = c.fetchone()["n"]
            c.execute("SELECT COUNT(DISTINCT koleksiyon) as n FROM kayitlar")
            koleksiyon_sayisi = c.fetchone()["n"]
            c.execute("SELECT COUNT(*) as n FROM tercihler")
            tercih_sayisi = c.fetchone()["n"]

            # Son kayit zamani
            c.execute("SELECT MAX(zaman) as son FROM kayitlar")
            son_row = c.fetchone()
            son_zaman = son_row["son"] if son_row and son_row["son"] else 0

            # FTS5 boyutu
            fts_boyut = 0
            db_path = Path(self._db_yolu)
            if db_path.exists():
                fts_boyut = db_path.stat().st_size
                # WAL dosyasi
                wal_path = db_path.with_suffix(".db-wal")
                if wal_path.exists():
                    fts_boyut += wal_path.stat().st_size

            return {
                "aktif": True,
                "backend": "sqlite+fts5",
                "session": self._aktif_session or "(yok)",
                "toplam_kayit": toplam,
                "session_sayisi": session_sayisi,
                "koleksiyon_sayisi": koleksiyon_sayisi,
                "tercih_sayisi": tercih_sayisi,
                "son_kayit": datetime.fromtimestamp(son_zaman).isoformat() if son_zaman else "yok",
                "db_boyut": f"{fts_boyut / 1024:.1f} KB",
            }
        except sqlite3.Error as e:
            return {"aktif": True, "backend": "sqlite+fts5", "hata": str(e)}

    def kapat(self) -> None:
        """Baglantiyi kapat."""
        try:
            if self._conn:
                self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                self._conn.close()
                self._conn = None
        except Exception as _hafiza_g_e1070:
            print(f"[UYARI] hafiza_genislet.py:1071 - {_hafiza_g_e1070}")


# ── Otomatik Consolidation Thread (arka planda hafiza budama) ──

_AUTO_CONSOLIDATION_INTERVAL = 3600  # Her 1 saatte bir
_auto_consolidation_thread = None
_auto_consolidation_stop = threading.Event()


def _auto_consolidation_loop() -> None:
    """Arka planda periyodik hafiza budama yapar.

    Her _AUTO_CONSOLIDATION_INTERVAL saniyede bir:
      - expire olmus kayitlari temizle
      - session_db'de konsolide_et() cagir (varsa)
      - WAL checkpoint
    """
    while not _auto_consolidation_stop.is_set():
        try:
            # hafiza_genislet kayitlarini temizle
            silinen = hafiza.temizle(yas_saat=72.0)
            if silinen > 0:
                _log = logging.getLogger(__name__)  # type: ignore[union-attr]
                _log.info(f"[AutoConsolidation] {silinen} expire kayit temizlendi")

            # session_db'de de konsolidasyon yap (varsa)
            try:
                from reymen.hafiza.session_db import AdvancedSessionStorage
                ROOT = Path(__file__).parent.resolve()
                db_path = str(ROOT / "merkez_db" / "session.db")
                storage = AdvancedSessionStorage(db_path)
                sonuc = storage.konsolide_et(max_gun=30, max_session=1000, max_toplam_karakter=500000)
                if sonuc.get("silinen_session", 0) > 0 or sonuc.get("silinen_mesaj", 0) > 0:
                    logger.info(
                        f"[AutoConsolidation] session_db: {sonuc['silinen_session']} session, "
                        f"{sonuc['silinen_mesaj']} mesaj budandi"
                    )
            except Exception as _hafiza_g_e1109:
                print(f"[UYARI] hafiza_genislet.py:1110 - {_hafiza_g_e1109}")

        except Exception as _hafiza_g_e1112:
            print(f"[UYARI] hafiza_genislet.py:1113 - {_hafiza_g_e1112}")

        # Bir sonraki donguye kadar bekle (stop sinyali ile erken uyanma)
        _auto_consolidation_stop.wait(_AUTO_CONSOLIDATION_INTERVAL)


def auto_consolidation_baslat(interval_saniye: int = 3600) -> None:
    """Otomatik hafiza budama thread'ini baslat.

    Args:
        interval_saniye: Kac saniyede bir calissin (default 3600 = 1 saat)
    """
    global _AUTO_CONSOLIDATION_INTERVAL, _auto_consolidation_thread
    _AUTO_CONSOLIDATION_INTERVAL = interval_saniye
    if _auto_consolidation_thread and _auto_consolidation_thread.is_alive():
        return  # Zaten calisiyor
    _auto_consolidation_stop.clear()
    _auto_consolidation_thread = threading.Thread(
        target=_auto_consolidation_loop,
        daemon=True,
        name="hafiza-auto-consolidation",
    )
    _auto_consolidation_thread.start()


def auto_consolidation_durdur() -> None:
    """Otomatik hafiza budama thread'ini durdur."""
    _auto_consolidation_stop.set()
    global _auto_consolidation_thread
    if _auto_consolidation_thread:
        _auto_consolidation_thread = None


# ══════════════════════════════════════════════════════════════════════════
# MOTOR ENTEGRASYONU — araçları motor.py'ye kaydet
# ══════════════════════════════════════════════════════════════════════════

def motor_kaydet(motor: Any) -> None:
    """hafiza_genislet.py araçlarını Motor'a kaydet.

    Motor._plugin_moduller_yukle() tarafından otomatik keşfedilir.
    """
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return

    # HAFIZA_DURUM — hafıza istatistikleri
    motor._plugin_arac_kaydet(
        "HAFIZA_DURUM",
        lambda: json.dumps(hafiza.durum(), ensure_ascii=False, indent=2, default=str),
        "Gelismis hafiza sisteminin durumunu ve istatistiklerini gosterir",
    )

    # HAFIZA_ARA — FTS5 tam metin arama
    motor._plugin_arac_kaydet(
        "HAFIZA_ARA",
        lambda sorgu="", limit="10": json.dumps(
            hafiza.ara(sorgu, limit=int(limit)), ensure_ascii=False, indent=2, default=str
        ),
        "Hafizada FTS5 ile tam metin ara. Kullanim: HAFIZA_ARA(sorgu='decorator', limit='10')",
    )

    # HAFIZA_KAYDET — hafızaya kayıt ekle
    motor._plugin_arac_kaydet(
        "HAFIZA_KAYDET",
        lambda icerik="", koleksiyon="konusmalar", anahtar="", ttl_saat="0": json.dumps({
            "basarili": hafiza.kaydet(
                icerik=icerik,
                koleksiyon=koleksiyon,
                anahtar=anahtar,
                ttl_saat=float(ttl_saat) if ttl_saat else 0,
            ),
            "koleksiyon": koleksiyon,
        }, ensure_ascii=False),
        "Hafizaya kayit ekler. Kullanim: HAFIZA_KAYDET(icerik='...', koleksiyon='konusmalar', anahtar='...', ttl_saat='0')",
    )

    # HAFIZA_SESSION_ARA — geçmiş session'larda FTS5 arama (ReYMeN session_search benzeri)
    motor._plugin_arac_kaydet(
        "HAFIZA_SESSION_ARA",
        lambda sorgu="", limit="5": json.dumps(
            hafiza.session_ara(sorgu, limit=int(limit)),
            ensure_ascii=False, indent=2, default=str,
        ),
        "Gecmis oturumlarda FTS5 ile ara. Kullanim: HAFIZA_SESSION_ARA(sorgu='decorator', limit='5')",
    )

    # HAFIZA_SESSION_LISTE — son session'ları listele
    motor._plugin_arac_kaydet(
        "HAFIZA_SESSION_LISTE",
        lambda limit="10": json.dumps(
            hafiza.session_listele(limit=int(limit)),
            ensure_ascii=False, indent=2, default=str,
        ),
        "Son oturumlari listeler. Kullanim: HAFIZA_SESSION_LISTE(limit='10')",
    )

    # HAFIZA_NOT_EKLE — kısa not ekle
    motor._plugin_arac_kaydet(
        "HAFIZA_NOT_EKLE",
        lambda baslik="", icerik="", ttl_saat="0": json.dumps({
            "basarili": hafiza.not_ekle(
                baslik=baslik, icerik=icerik,
                ttl_saat=float(ttl_saat) if ttl_saat else 0,
            ),
        }, ensure_ascii=False),
        "Kisa not/hatirlatma ekler. Kullanim: HAFIZA_NOT_EKLE(baslik='ornek', icerik='...', ttl_saat='24')",
    )

    # HAFIZA_NOT_LISTE — notları listele
    motor._plugin_arac_kaydet(
        "HAFIZA_NOT_LISTE",
        lambda limit="20": json.dumps(
            hafiza.notlari_listele(limit=int(limit)),
            ensure_ascii=False, indent=2, default=str,
        ),
        "Tum aktif notlari listeler. Kullanim: HAFIZA_NOT_LISTE(limit='20')",
    )

    # HAFIZA_TERCIH_KAYDET — kullanıcı tercihi kaydet
    motor._plugin_arac_kaydet(
        "HAFIZA_TERCIH_KAYDET",
        lambda anahtar="", deger="": json.dumps({
            "basarili": hafiza.tercih_kaydet(anahtar=anahtar, deger=deger),
        }, ensure_ascii=False),
        "Kullanici tercihi kaydeder. Kullanim: HAFIZA_TERCIH_KAYDET(anahtar='dil', deger='Turkce')",
    )

    # HAFIZA_TERCIH_AL — kullanıcı tercihini oku
    motor._plugin_arac_kaydet(
        "HAFIZA_TERCIH_AL",
        lambda anahtar="", default="": json.dumps({
            "anahtar": anahtar,
            "deger": hafiza.tercih_al(anahtar=anahtar, default=default),
        }, ensure_ascii=False),
        "Kullanici tercihini okur. Kullanim: HAFIZA_TERCIH_AL(anahtar='dil', default='Turkce')",
    )

    # HAFIZA_TEMIZLE — eski kayıtları temizle (memory consolidation)
    motor._plugin_arac_kaydet(
        "HAFIZA_TEMIZLE",
        lambda yas_saat="72": json.dumps({
            "silinen_kayit": hafiza.temizle(yas_saat=float(yas_saat) if yas_saat else 72.0),
            "mesaj": f"{yas_saat} saatten eski expire kayitlar temizlendi",
        }, ensure_ascii=False),
        "Eski/expire kayitlari temizler. Kullanim: HAFIZA_TEMIZLE(yas_saat='72')",
    )


# ══════════════════════════════════════════════════════════════════════════
# SINGLETON — tum moduller ayni instance'i kullanir
# ══════════════════════════════════════════════════════════════════════════

hafiza = GelismisHafiza()
