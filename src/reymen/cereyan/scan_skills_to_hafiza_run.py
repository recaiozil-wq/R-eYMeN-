# -*- coding: utf-8 -*-
"""
scan_skills_to_hafiza_run.py — ReYMeN skills → OnceHafiza DB senkronizasyonu.

reymen/cereyan/skills/ klasöründeki .md dosyalarını tara,
- skills_index.db (beceriler_meta) ile hash karşılaştırması yap
- Eksik olanları EKLE
- Değişenleri GÜNCELLE
- OnceHafiza DB'sine (ogrenmeler.db) kaydet

Çıktı: kaç yeni, kaç güncellendi.
"""

import hashlib
import logging
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scan_skills")

# ── Yollar ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.resolve()  # reymen/
SKILLS_DIR = ROOT / "cereyan" / "skills"       # taranacak klasör
SKILLS_DB = ROOT / "merkez_db" / "skills_index.db"
OGRENME_DB = ROOT / "merkez_db" / "ogrenmeler.db"


def dosya_hash(dosya_yolu: str) -> str:
    """SHA256 hash (ilk 16 karakter)."""
    h = hashlib.sha256()
    with open(dosya_yolu, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def kategori_ve_ad(dosya_yolu: str) -> tuple[str, str]:
    """Göreli yoldan kategori ve dosya adını çıkar."""
    rel = os.path.relpath(dosya_yolu, str(SKILLS_DIR))
    rel = rel.replace("\\", "/")
    parts = rel.split("/")
    if len(parts) == 1:
        return "", parts[0]
    return "/".join(parts[:-1]), parts[-1]


def skills_db_kur(con: sqlite3.Connection):
    """skills_index.db tablolarını oluştur (yoksa)."""
    con.executescript("""
        CREATE TABLE IF NOT EXISTS beceriler (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ad      TEXT UNIQUE NOT NULL,
            aciklama TEXT NOT NULL DEFAULT '',
            icerik  TEXT NOT NULL DEFAULT '',
            kaynak  TEXT DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS beceriler_meta (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ad          TEXT UNIQUE NOT NULL,
            dosya_hash  TEXT NOT NULL,
            guncelleme  TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_meta_ad ON beceriler_meta(ad);
    """)


def ogrenme_db_kur(con: sqlite3.Connection):
    """ogrenmeler.db tablosunu oluştur (yoksa) — once_hafiza.py şeması."""
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


def beceriden_aciklama_ve_icerik(icerik: str) -> tuple[str, str]:
    """Markdown içeriğinden başlık ve tüm içerik."""
    lines = icerik.split("\n")
    baslik = ""
    for line in lines:
        line = line.strip()
        if line.startswith("# "):
            baslik = line[2:].strip()
            break
    if not baslik:
        baslik = icerik[:200].strip()
    return baslik, icerik


def scan_and_sync() -> tuple[int, int, int]:
    """Ana tarama + senkronizasyon.

    Returns:
        (yeni_sayisi, guncel_sayisi, atlanan_sayisi)
    """
    logger.info("=" * 60)
    logger.info("🔍 Skills → OnceHafiza DB taraması başlıyor...")
    logger.info("   Skills klasörü: %s", SKILLS_DIR)
    logger.info("   Skills DB:      %s", SKILLS_DB)
    logger.info("   OnceHafiza DB:  %s", OGRENME_DB)

    # 1) Skills dizinindeki tüm .md dosyalarını bul
    md_dosyalari = sorted(SKILLS_DIR.rglob("*.md"))
    logger.info("📄 Skills klasöründe %d .md dosyası bulundu.", len(md_dosyalari))

    # 2) Skills DB'deki mevcut meta tablosunu yükle
    SKILLS_DB.parent.mkdir(parents=True, exist_ok=True)
    con_skills = sqlite3.connect(str(SKILLS_DB))
    con_skills.execute("PRAGMA journal_mode=WAL")
    skills_db_kur(con_skills)

    meta_map = {}  # ad -> (dosya_hash, guncelleme)
    try:
        meta_cur = con_skills.execute("SELECT ad, dosya_hash, guncelleme FROM beceriler_meta")
        for row in meta_cur.fetchall():
            meta_map[row[0]] = (row[1], row[2] if len(row) > 2 else "")
    except sqlite3.OperationalError:
        pass  # tablo yoksa boş başla
    con_skills.close()

    logger.info("📚 Skills DB'de %d kayıtlı dosya var.", len(meta_map))

    # 3) OnceHafiza DB'deki mevcut kayıtları yükle (hedef bazında)
    OGRENME_DB.parent.mkdir(parents=True, exist_ok=True)
    con_ogren = sqlite3.connect(str(OGRENME_DB))
    con_ogren.execute("PRAGMA journal_mode=WAL")
    ogrenme_db_kur(con_ogren)
    ogrenme_map = {}  # hedef -> id
    try:
        ogr_cur = con_ogren.execute("SELECT hedef, id, guncelleme FROM ogrenmeler")
        for row in ogr_cur.fetchall():
            ogrenme_map[row[0]] = (row[1], row[2] if len(row) > 2 else "")
    except sqlite3.OperationalError:
        logger.warning("[fix_01_sessiz_except] OperationalError")
    con_ogren.close()

    logger.info("📚 OnceHafiza DB'de %d kayıtlı öğrenme var.", len(ogrenme_map))

    # 4) Her dosyayı kontrol et
    yeni_sayisi = 0
    guncel_sayisi = 0
    atlanan_sayisi = 0
    yeni_liste = []
    guncel_liste = []

    for dosya in md_dosyalari:
        kategori, dosya_adi = kategori_ve_ad(str(dosya))
        meta_adi = f"{kategori}/{dosya_adi}" if kategori else dosya_adi

        # Dosyanın hash'ini hesapla
        try:
            guncel_hash = dosya_hash(str(dosya))
        except (OSError, IOError) as e:
            logger.warning("⚠️  Dosya okunamadı: %s — %s", dosya, e)
            continue

        eski_kayit = meta_map.get(meta_adi)
        eski_hash = eski_kayit[0] if eski_kayit else None

        if eski_hash is None:
            yeni_sayisi += 1
            yeni_liste.append((meta_adi, str(dosya), guncel_hash, kategori, dosya_adi))
            logger.info("🆕 YENİ: %s", meta_adi)
        elif eski_hash != guncel_hash:
            guncel_sayisi += 1
            guncel_liste.append((meta_adi, str(dosya), guncel_hash, kategori, dosya_adi))
            logger.info("🔄 GÜNCELLENMİŞ: %s (hash değişmiş)", meta_adi)
        else:
            atlanan_sayisi += 1

    logger.info("=" * 60)
    logger.info("📊 KARŞILAŞTIRMA SONUCU:")
    logger.info("   Yeni: %d | Güncellenecek: %d | Atlanan: %d",
                yeni_sayisi, guncel_sayisi, atlanan_sayisi)

    # 5) Yeni dosyaları ekle
    if yeni_liste:
        logger.info("--- YENİ dosyalar ekleniyor (%d) ---", len(yeni_liste))
        con_s = sqlite3.connect(str(SKILLS_DB))
        con_o = sqlite3.connect(str(OGRENME_DB))
        try:
            for meta_adi, dosya_yolu, guncel_hash, kategori, dosya_adi in yeni_liste:
                try:
                    with open(dosya_yolu, "r", encoding="utf-8", errors="replace") as f:
                        icerik = f.read()
                except Exception as e:
                    logger.warning("⚠️  Okunamadı: %s — %s", dosya_yolu, e)
                    continue

                baslik, tam_icerik = beceriden_aciklama_ve_icerik(icerik)
                muhtemel_aciklama = baslik[:500]
                muhtemel_icerik = tam_icerik[:10000]
                su_an = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # skills_index.db ekle
                con_s.execute(
                    "INSERT OR IGNORE INTO beceriler (ad, aciklama, icerik, kaynak) VALUES (?, ?, ?, ?)",
                    (meta_adi, muhtemel_aciklama, muhtemel_icerik, dosya_yolu),
                )
                con_s.execute(
                    "INSERT OR IGNORE INTO beceriler_meta (ad, dosya_hash, guncelleme) VALUES (?, ?, ?)",
                    (meta_adi, guncel_hash, su_an),
                )

                # OnceHafiza DB'ye ekle (ogrenmeler — once_hafiza.kaydet() API şeması)
                hedef = dosya_adi.replace(".md", "")
                kat = f"skills/{kategori}" if kategori else "skills/genel"
                con_o.execute(
                    """INSERT OR IGNORE INTO ogrenmeler
                       (hedef, kategori, icerik, guven_skoru, basari_sayisi, hata_sayisi,
                        son_kullanim, gecerlilik_tarihi, kaynak_url, olusturulma, guncelleme)
                       VALUES (?, ?, ?, 0.5, 1, 0, date('now'), date('now', '+180 days'), ?, datetime('now'), ?)""",
                    (hedef, kat, icerik[:5000], dosya_yolu, su_an),
                )

            con_s.commit()
            con_o.commit()
        finally:
            con_s.close()
            con_o.close()

        logger.info("✅ %d yeni dosya eklendi.", len(yeni_liste))

    # 6) Güncellenen dosyaları güncelle
    if guncel_liste:
        logger.info("--- GÜNCELLENEN dosyalar işleniyor (%d) ---", len(guncel_liste))
        con_s = sqlite3.connect(str(SKILLS_DB))
        con_o = sqlite3.connect(str(OGRENME_DB))
        try:
            for meta_adi, dosya_yolu, guncel_hash, kategori, dosya_adi in guncel_liste:
                try:
                    with open(dosya_yolu, "r", encoding="utf-8", errors="replace") as f:
                        icerik = f.read()
                except Exception as e:
                    logger.warning("⚠️  Okunamadı: %s — %s", dosya_yolu, e)
                    continue

                baslik, tam_icerik = beceriden_aciklama_ve_icerik(icerik)
                muhtemel_aciklama = baslik[:500]
                muhtemel_icerik = tam_icerik[:10000]
                su_an = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # skills_index.db güncelle
                con_s.execute(
                    "UPDATE beceriler SET aciklama=?, icerik=?, kaynak=? WHERE ad=?",
                    (muhtemel_aciklama, muhtemel_icerik, dosya_yolu, meta_adi),
                )
                con_s.execute(
                    "UPDATE beceriler_meta SET dosya_hash=?, guncelleme=? WHERE ad=?",
                    (guncel_hash, su_an, meta_adi),
                )

                # OnceHafiza DB'ye güncelle
                hedef = dosya_adi.replace(".md", "")
                kat = f"skills/{kategori}" if kategori else "skills/genel"
                var = con_o.execute(
                    "SELECT id FROM ogrenmeler WHERE hedef = ?", (hedef,)
                ).fetchone()
                if var:
                    con_o.execute(
                        """UPDATE ogrenmeler SET
                            icerik = ?, kategori = ?, kaynak_url = ?,
                            guncelleme = ?, gecerlilik_tarihi = date('now', '+180 days')
                           WHERE hedef = ?""",
                        (icerik[:5000], kat, dosya_yolu, su_an, hedef),
                    )
                else:
                    con_o.execute(
                        """INSERT INTO ogrenmeler
                           (hedef, kategori, icerik, guven_skoru, basari_sayisi, hata_sayisi,
                            son_kullanim, gecerlilik_tarihi, kaynak_url, olusturulma, guncelleme)
                           VALUES (?, ?, ?, 0.5, 1, 0, date('now'), date('now', '+180 days'), ?, datetime('now'), ?)""",
                        (hedef, kat, icerik[:5000], dosya_yolu, su_an),
                    )

            con_s.commit()
            con_o.commit()
        finally:
            con_s.close()
            con_o.close()

        logger.info("✅ %d dosya güncellendi.", len(guncel_liste))

    logger.info("=" * 60)
    logger.info("✅ TARAMA VE SENKRONİZASYON TAMAMLANDI!")
    logger.info("   Yeni eklenen:  %d", yeni_sayisi)
    logger.info("   Güncellenen:   %d", guncel_sayisi)
    logger.info("   Atlanan (aynı): %d", atlanan_sayisi)
    logger.info("=" * 60)

    return yeni_sayisi, guncel_sayisi, atlanan_sayisi


if __name__ == "__main__":
    yeni, guncel, atlanan = scan_and_sync()
    print(f"\nSONUC|new={yeni}|updated={guncel}|skipped={atlanan}")
