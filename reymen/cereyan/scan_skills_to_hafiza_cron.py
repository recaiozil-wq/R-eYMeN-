# -*- coding: utf-8 -*-
"""
scan_skills_to_hafiza_cron.py — Cron job: Skills → OnceHafiza DB senkronizasyonu.

Her 6 saatte bir çalışır.
reymen/cereyan/skills/ -> skills_index.db (meta) -> ogrenmeler.db (OnceHafiza)

Sadece gerçekten yeni dosyaları ekler ve gerçekten değişmiş dosyaları günceller.
Hash karşılaştırması tam SHA256 ile yapılır.
"""

import hashlib
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scan_skills_cron")

# ── Yollar ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.resolve()  # reymen/
SKILLS_DIR = ROOT / "cereyan" / "skills"       # taranacak klasör
SKILLS_DB = ROOT / "cereyan" / ".ReYMeN" / "skills_index.db"
OGRENME_DB = ROOT / "cereyan" / ".ReYMeN" / "ogrenmeler.db"


def dosya_hash_full(dosya_yolu: str) -> str:
    """Tam SHA256 hash (64 karakter)."""
    h = hashlib.sha256()
    with open(dosya_yolu, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def kategori_ve_ad(dosya_yolu: str) -> tuple[str, str]:
    """Göreli yoldan kategori ve dosya adını çıkar."""
    rel = os.path.relpath(dosya_yolu, str(SKILLS_DIR))
    rel = rel.replace("\\", "/")
    parts = rel.split("/")
    if len(parts) == 1:
        return "", parts[0]
    return "/".join(parts[:-1]), parts[-1]


def ogrenme_db_kur(con: sqlite3.Connection):
    con.executescript("""
        CREATE TABLE IF NOT EXISTS ogrenmeler (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            hedef             TEXT NOT NULL,
            kategori          TEXT NOT NULL DEFAULT 'genel',
            icerik            TEXT NOT NULL,
            guven_skoru       REAL NOT NULL DEFAULT 1.0,
            basari_sayisi     INTEGER NOT NULL DEFAULT 1,
            hata_sayisi       INTEGER NOT NULL DEFAULT 0,
            son_kullanim      TEXT NOT NULL DEFAULT (date('now')),
            gecerlilik_tarihi TEXT NOT NULL DEFAULT (date('now', '+180 days')),
            kaynak_url        TEXT DEFAULT NULL,
            olusturulma       TEXT NOT NULL DEFAULT (datetime('now')),
            guncelleme        TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_ogrenmeler_kategori ON ogrenmeler(kategori);
        CREATE INDEX IF NOT EXISTS idx_ogrenmeler_hedef   ON ogrenmeler(hedef);
        CREATE INDEX IF NOT EXISTS idx_ogrenmeler_gecerli ON ogrenmeler(gecerlilik_tarihi);
    """)


def _baglan(path: Path) -> sqlite3.Connection:
    """DB bağlantısı — WAL + busy_timeout=120s + retry."""
    for i in range(10):
        try:
            con = sqlite3.connect(str(path), timeout=120)
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA busy_timeout=120000")
            return con
        except sqlite3.OperationalError as e:
            if i < 9:
                logger.warning("⚠️  DB kilitli (%s), %ds bekleniyor...", e, 5)
                time.sleep(5)
            else:
                raise
    raise sqlite3.OperationalError(f"DB {path} bağlanamadı (10 deneme)")


def scan_and_sync() -> tuple[int, int]:
    """Skills → OnceHafiza senkronizasyonu.

    Returns:
        (yeni_sayisi, guncel_sayisi)
    """
    logger.info("=" * 60)
    logger.info("🔍 Skills → OnceHafiza DB cron taraması")
    logger.info("   Skills: %s", SKILLS_DIR)
    logger.info("   Meta:   %s", SKILLS_DB)
    logger.info("   Hafiza: %s", OGRENME_DB)

    # 1) Skills klasöründeki tüm .md dosyaları
    md_dosyalari = sorted(SKILLS_DIR.rglob("*.md"))
    logger.info("📄 Skills: %d .md dosyası", len(md_dosyalari))

    # 2) skills_index.db'den meta yükle (tam hash ile karşılaştırma)
    SKILLS_DB.parent.mkdir(parents=True, exist_ok=True)
    con_skills = _baglan(SKILLS_DB)
    meta_map = {}
    try:
        for row in con_skills.execute("SELECT ad, dosya_hash FROM beceriler_meta").fetchall():
            meta_map[row[0]] = row[1]  # ad -> full_hash (64 chars)
    except sqlite3.OperationalError:
        logger.warning("[fix_01_sessiz_except] OperationalError")
    con_skills.close()
    logger.info("📚 Skills DB meta: %d kayıt", len(meta_map))

    # 3) ogrenmeler.db'den mevcut kayıtları yükle
    OGRENME_DB.parent.mkdir(parents=True, exist_ok=True)
    con_ogren = _baglan(OGRENME_DB)
    ogrenme_db_kur(con_ogren)
    ogrenme_set = set()
    try:
        for row in con_ogren.execute("SELECT hedef FROM ogrenmeler").fetchall():
            ogrenme_set.add(row[0])
    except sqlite3.OperationalError:
        logger.warning("[fix_01_sessiz_except] OperationalError")
    con_ogren.close()
    logger.info("📚 OnceHafiza DB: %d kayıt", len(ogrenme_set))

    # 4) Her dosyayı tara, yeni/değişenleri belirle
    yeni_liste = []       # skills_index.db'de olmayan (yepyeni)
    guncel_liste = []     # skills_index.db'de var ama hash değişmiş
    oncehafiza_ekle = []  # skills_index.db'de var ama OnceHafiza'da yok
    atlanan = 0

    for dosya in md_dosyalari:
        kategori, dosya_adi = kategori_ve_ad(str(dosya))
        meta_adi = f"{kategori}/{dosya_adi}" if kategori else dosya_adi

        try:
            guncel_hash = dosya_hash_full(str(dosya))
        except (OSError, IOError):
            continue

        eski_hash = meta_map.get(meta_adi)

        if eski_hash is None:
            # Skills_index.db'de yok → yepyeni
            yeni_liste.append((meta_adi, str(dosya), guncel_hash, kategori, dosya_adi))
        elif eski_hash != guncel_hash:
            # Hash değişmiş → güncelle
            guncel_liste.append((meta_adi, str(dosya), guncel_hash, kategori, dosya_adi))
        else:
            atlanan += 1

        # OnceHafiza'da var mı kontrol et (hedef = dosya_adi .md'siz)
        hedef = dosya_adi.replace(".md", "")
        if hedef not in ogrenme_set:
            oncehafiza_ekle.append((meta_adi, str(dosya), guncel_hash, kategori, dosya_adi))

    logger.info("📊 Analiz: yeni=%d, guncel=%d, atlanan=%d, OnceHafiza'ya_ek=%d",
                len(yeni_liste), len(guncel_liste), atlanan, len(oncehafiza_ekle))

    # 5) skills_index.db'yi güncelle (yeni + güncellenen)
    con_s = _baglan(SKILLS_DB)
    skills_eklenen = 0
    skills_guncellenen = 0

    try:
        for meta_adi, dosya_yolu, guncel_hash, kategori, dosya_adi in yeni_liste:
            try:
                with open(dosya_yolu, "r", encoding="utf-8", errors="replace") as f:
                    icerik = f.read()
            except Exception:
                continue
            baslik = next((l.strip()[2:] for l in icerik.split("\n") if l.strip().startswith("# ")), icerik[:200].strip())
            su_an = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            con_s.execute("INSERT OR IGNORE INTO beceriler (ad, aciklama, icerik, kaynak) VALUES (?, ?, ?, ?)",
                          (meta_adi, baslik[:500], icerik[:10000], dosya_yolu))
            con_s.execute("INSERT OR IGNORE INTO beceriler_meta (ad, dosya_hash, guncelleme) VALUES (?, ?, ?)",
                          (meta_adi, guncel_hash, su_an))
            skills_eklenen += 1

        for meta_adi, dosya_yolu, guncel_hash, kategori, dosya_adi in guncel_liste:
            try:
                with open(dosya_yolu, "r", encoding="utf-8", errors="replace") as f:
                    icerik = f.read()
            except Exception:
                continue
            baslik = next((l.strip()[2:] for l in icerik.split("\n") if l.strip().startswith("# ")), icerik[:200].strip())
            su_an = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            con_s.execute("UPDATE beceriler SET aciklama=?, icerik=?, kaynak=? WHERE ad=?",
                          (baslik[:500], icerik[:10000], dosya_yolu, meta_adi))
            con_s.execute("UPDATE beceriler_meta SET dosya_hash=?, guncelleme=? WHERE ad=?",
                          (guncel_hash, su_an, meta_adi))
            skills_guncellenen += 1

        con_s.commit()
    finally:
        con_s.close()

    logger.info("✅ Skills DB: %d yeni + %d güncellendi", skills_eklenen, skills_guncellenen)

    # 6) OnceHafiza DB'sini güncelle (ogrenmeler.db)
    # Kullanılacak kaynak: birleştir (yeni + güncel + OnceHafiza'da olmayan)
    # Ama: bir dosya hem yeni hem oncehafiza_ekle'de olabilir → dedup
    ekle_set = set()
    oncehafiza_kaynak = []

    # Öncelik: güncellenenler içinden OnceHafiza'da olmayanları bul
    # Basitçe: oncehafiza_ekle listesini kullan, hepsi skills_index.db'de var olan ama ogrenmeler'de olmayanlar
    for item in oncehafiza_ekle:
        meta_adi, dosya_yolu, guncel_hash, kategori, dosya_adi = item
        if meta_adi not in ekle_set:
            ekle_set.add(meta_adi)
            oncehafiza_kaynak.append(item)

    con_o = _baglan(OGRENME_DB)
    ogrenme_eklenen = 0
    ogrenme_guncellenen = 0
    su_an = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Yeni eklemeler: OnceHafiza'da olmayan dosyalar
        for meta_adi, dosya_yolu, guncel_hash, kategori, dosya_adi in oncehafiza_kaynak:
            try:
                with open(dosya_yolu, "r", encoding="utf-8", errors="replace") as f:
                    icerik = f.read()
            except Exception:
                continue
            hedef = dosya_adi.replace(".md", "")
            kat = f"skills/{kategori}" if kategori else "skills/genel"
            con_o.execute(
                """INSERT OR IGNORE INTO ogrenmeler
                   (hedef, kategori, icerik, guven_skoru, basari_sayisi, hata_sayisi,
                    son_kullanim, gecerlilik_tarihi, kaynak_url, olusturulma, guncelleme)
                   VALUES (?, ?, ?, 0.5, 1, 0, date('now'), date('now', '+180 days'), ?, datetime('now'), ?)""",
                (hedef, kat, icerik[:5000], dosya_yolu, su_an),
            )
            ogrenme_eklenen += 1

        # Güncellemeler: hash değişmiş dosyalardan OnceHafiza'da olanları güncelle
        for meta_adi, dosya_yolu, guncel_hash, kategori, dosya_adi in guncel_liste:
            hedef = dosya_adi.replace(".md", "")
            if hedef not in ogrenme_set:
                continue  # OnceHafiza'da yoksa atla (yukarıda eklenmiş olabilir)
            try:
                with open(dosya_yolu, "r", encoding="utf-8", errors="replace") as f:
                    icerik = f.read()
            except Exception:
                continue
            kat = f"skills/{kategori}" if kategori else "skills/genel"
            con_o.execute(
                """UPDATE ogrenmeler SET
                    icerik = ?, kategori = ?, kaynak_url = ?,
                    guncelleme = ?, gecerlilik_tarihi = date('now', '+180 days')
                   WHERE hedef = ?""",
                (icerik[:5000], kat, dosya_yolu, su_an, hedef),
            )
            if con_o.execute("SELECT changes()").fetchone()[0] > 0:
                ogrenme_guncellenen += 1

        con_o.commit()
    finally:
        con_o.close()

    logger.info("✅ OnceHafiza DB: %d yeni eklendi + %d güncellendi", ogrenme_eklenen, ogrenme_guncellenen)
    logger.info("=" * 60)
    logger.info("📊 CRON RAPORU:")
    logger.info("   Skills DB  → yeni: %d, güncel: %d", skills_eklenen, skills_guncellenen)
    logger.info("   OnceHafiza → yeni: %d, güncel: %d", ogrenme_eklenen, ogrenme_guncellenen)
    logger.info("=" * 60)

    return ogrenme_eklenen, ogrenme_guncellenen


if __name__ == "__main__":
    yeni, guncel = scan_and_sync()
    print(f"\nSONUC|new={yeni}|updated={guncel}")
