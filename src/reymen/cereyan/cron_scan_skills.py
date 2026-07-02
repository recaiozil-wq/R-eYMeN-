#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cron_scan_skills.py — ReYMeN OnceHafiza skills tarama cron job.
Her 6 saatte bir çalışır.

Kullanım:
    python reymen/cereyan/cron_scan_skills.py

Çıktı:
    - Normal rapor (okunabilir)
    - SONUC|new=X|updated=Y|skipped=Z (makine formatı)
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
logger = logging.getLogger("cron_scan_skills")

ROOT = Path(__file__).parent.parent.resolve()
SKILLS_DIR = ROOT / "cereyan" / "skills"
SKILLS_DB = ROOT / "cereyan" / ".ReYMeN" / "skills_index.db"
OGRENME_DB = ROOT / "hafiza" / "ogrenme.db"


def dosya_hash(dosya_yolu: str) -> str:
    """SHA256 hash (ilk 16 karakter)."""
    h = hashlib.sha256()
    with open(dosya_yolu, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def kategori_ve_ad(dosya_yolu: str) -> tuple[str, str]:
    """Göreli yoldan kategori ve dosya adı."""
    rel = os.path.relpath(dosya_yolu, str(SKILLS_DIR)).replace("\\", "/")
    parts = rel.split("/")
    return ("", parts[0]) if len(parts) == 1 else ("/".join(parts[:-1]), parts[-1])


def beceriden_baslik(icerik: str) -> str:
    """Markdown'dan ilk # başlığını bul."""
    for line in icerik.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return icerik[:200].strip()


def skills_db_guncelle(meta_adi: str, dosya_yolu: str, icerik: str, new_hash: str) -> None:
    """skills_index.db'de FTS5 + meta güncelle."""
    baslik = beceriden_baslik(icerik)
    su_an = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con = sqlite3.connect(str(SKILLS_DB))
    try:
        con.execute(
            "UPDATE beceriler SET aciklama=?, icerik=?, kaynak=? WHERE ad=?",
            (baslik[:500], icerik[:10000], dosya_yolu, meta_adi),
        )
        con.execute(
            "UPDATE beceriler_meta SET dosya_hash=?, guncelleme=? WHERE ad=?",
            (new_hash, su_an, meta_adi),
        )
        con.commit()
    except Exception as e:
        logger.warning("skills_db güncelleme hatası (%s): %s", meta_adi, e)
    finally:
        con.close()


def skills_db_ekle(meta_adi: str, dosya_yolu: str, icerik: str, new_hash: str) -> None:
    """skills_index.db'ye yeni kayıt ekle."""
    baslik = beceriden_baslik(icerik)
    su_an = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con = sqlite3.connect(str(SKILLS_DB))
    try:
        con.execute(
            "INSERT OR IGNORE INTO beceriler (ad, aciklama, icerik, kaynak) VALUES (?, ?, ?, ?)",
            (meta_adi, baslik[:500], icerik[:10000], dosya_yolu),
        )
        con.execute(
            "INSERT OR IGNORE INTO beceriler_meta (ad, dosya_hash, guncelleme) VALUES (?, ?, ?)",
            (meta_adi, new_hash, su_an),
        )
        con.commit()
    except Exception as e:
        logger.warning("skills_db ekleme hatası (%s): %s", meta_adi, e)
    finally:
        con.close()


def ogrenme_db_guncelle(meta_adi: str, icerik: str) -> None:
    """OnceHafiza ogrenme.db'yi güncelle."""
    hedef = meta_adi.replace(".md", "").replace("/", "_")
    su_an = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con = sqlite3.connect(str(OGRENME_DB))
    try:
        var = con.execute("SELECT id FROM ogrenmeler WHERE hedef = ?", (hedef,)).fetchone()
        if var:
            con.execute(
                """UPDATE ogrenmeler SET cozum=?, son_basari=?, son_kullanim=?,
                   gecerlilik_tarihi=datetime('now','+180 days') WHERE hedef=?""",
                (icerik[:5000], su_an, su_an, hedef),
            )
        else:
            con.execute(
                """INSERT INTO ogrenmeler (hedef, cozum, kaynak, basari_sayisi, son_basari,
                   son_kullanim, guven_skoru, kategori, gecerlilik_tarihi)
                   VALUES (?, ?, 'skills_scan', 1, ?, ?, 0.5, ?, datetime('now','+180 days'))""",
                (hedef, icerik[:5000], su_an, su_an, "skills/" + meta_adi),
            )
        con.commit()
    except Exception as e:
        logger.warning("ogrenme.db hatası (%s): %s", hedef, e)
    finally:
        con.close()


def main() -> None:
    logger.info("=" * 60)
    logger.info("🔍 CRON: Skills → OnceHafiza taraması başlıyor")
    logger.info("   Klasör:   %s", SKILLS_DIR)
    logger.info("   Skills DB: %s", SKILLS_DB)
    logger.info("   Öğrenme DB: %s", OGRENME_DB)

    # 1) Skills dizinini tara
    md_dosyalari = sorted(SKILLS_DIR.rglob("*.md"))
    logger.info("📄 %d .md dosyası bulundu.", len(md_dosyalari))

    # 2) Mevcut meta tablosunu yükle
    con = sqlite3.connect(str(SKILLS_DB))
    meta_map = dict(con.execute("SELECT ad, dosya_hash FROM beceriler_meta").fetchall())
    con.close()
    logger.info("📚 DB'de %d kayıtlı dosya.", len(meta_map))

    # 3) Tarama + güncelleme
    yeni_say = 0
    guncel_say = 0
    atlanan_say = 0

    for dosya in md_dosyalari:
        kategori, dosya_adi = kategori_ve_ad(str(dosya))
        meta_adi = f"{kategori}/{dosya_adi}" if kategori else dosya_adi

        try:
            guncel_hash = dosya_hash(str(dosya))
        except (OSError, IOError) as e:
            logger.warning("⚠️  Okunamadı: %s — %s", dosya, e)
            continue

        eski_hash = meta_map.get(meta_adi)

        if eski_hash is None:
            # 🆕 YENİ
            try:
                with open(dosya, "r", encoding="utf-8", errors="replace") as f:
                    icerik = f.read()
            except Exception as e:
                logger.warning("⚠️  Okunamadı: %s — %s", dosya, e)
                continue
            skills_db_ekle(meta_adi, str(dosya), icerik, guncel_hash)
            ogrenme_db_guncelle(meta_adi, icerik)
            yeni_say += 1
            logger.info("  🆕 YENİ: %s", meta_adi)

        elif eski_hash != guncel_hash:
            # 🔄 GÜNCELLENMİŞ
            try:
                with open(dosya, "r", encoding="utf-8", errors="replace") as f:
                    icerik = f.read()
            except Exception as e:
                logger.warning("⚠️  Okunamadı: %s — %s", dosya, e)
                continue
            skills_db_guncelle(meta_adi, str(dosya), icerik, guncel_hash)
            ogrenme_db_guncelle(meta_adi, icerik)
            guncel_say += 1
            logger.info("  🔄 GÜNCELLENDİ: %s", meta_adi)
        else:
            atlanan_say += 1

    # 4) Rapor
    logger.info("=" * 60)
    logger.info("✅ CRON taraması tamamlandı!")
    logger.info("   🆕 Yeni eklenen:   %d", yeni_say)
    logger.info("   🔄 Güncellenen:    %d", guncel_say)
    logger.info("   ⏭  Atlanan:        %d", atlanan_say)
    logger.info("   📊 Toplam:         %d", len(md_dosyalari))
    logger.info("=" * 60)

    # Makine formatı
    print(f"\nSONUC|new={yeni_say}|updated={guncel_say}|skipped={atlanan_say}")


if __name__ == "__main__":
    main()
