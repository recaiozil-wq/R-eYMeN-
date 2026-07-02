# -*- coding: utf-8 -*-
"""
scan_skills_to_hafiza_v2.py — reymen/cereyan/skills/ klasöründeki .md dosyalarını
tara, skills_index.db'deki beceriler_meta tablosuyla karşılaştır.
  - Eksik olanları EKLE (yeni)
  - Hash değişmiş olanları GÜNCELLE (güncellenmiş)
  - Değişmeyenleri ATLA

Her 6 saatte bir çalışacak cron job.
v2: Önce sadece tarama & karşılaştırma yap, raporu göster.
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
SKILLS_DIR = ROOT / "cereyan" / "skills"  # taranacak klasör
SKILLS_DB = ROOT / "cereyan" / ".ReYMeN" / "skills_index.db"
OGRENME_DB = ROOT / "hafiza" / "ogrenme.db"  # OnceHafiza ogrenme DB


def dosya_hash(dosya_yolu: str) -> str:
    """Bir dosyanın SHA256 hash'ini döndür (ilk 16 karakter)."""
    h = hashlib.sha256()
    with open(dosya_yolu, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def kategori_ve_ad(dosya_yolu: str) -> tuple[str, str]:
    rel = os.path.relpath(dosya_yolu, str(SKILLS_DIR))
    rel = rel.replace("\\", "/")
    parts = rel.split("/")
    if len(parts) == 1:
        return "", parts[0]
    else:
        return "/".join(parts[:-1]), parts[-1]


def scan_only():
    """Sadece tara ve karşılaştır - veritabanına dokunma."""
    logger.info("=" * 60)
    logger.info("🔍 Skills tarama başlıyor (sadece analiz)...")
    logger.info("   Klasör: %s", SKILLS_DIR)

    # 1) Skills dizinindeki tüm .md dosyalarını bul
    md_dosyalari = sorted(SKILLS_DIR.rglob("*.md"))
    logger.info("📄 Skills klasöründe %d .md dosyası bulundu.", len(md_dosyalari))

    # 2) Skills DB'deki mevcut meta tablosunu yükle
    con = sqlite3.connect(str(SKILLS_DB))
    meta_cur = con.execute("SELECT ad, dosya_hash FROM beceriler_meta")
    meta_map = {}
    for row in meta_cur.fetchall():
        meta_map[row[0]] = row[1]
    con.close()
    logger.info("📚 Skills DB'de %d kayıtlı dosya var.", len(meta_map))

    # 3) Her dosyayı kontrol et
    yeni_liste = []
    guncel_liste = []
    atlanan_sayisi = 0

    for dosya in md_dosyalari:
        kategori, dosya_adi = kategori_ve_ad(str(dosya))
        meta_adi = f"{kategori}/{dosya_adi}" if kategori else dosya_adi

        try:
            guncel_hash = dosya_hash(str(dosya))
        except (OSError, IOError) as e:
            logger.warning("⚠️  Dosya okunamadı: %s — %s", dosya, e)
            continue

        eski_hash = meta_map.get(meta_adi)

        if eski_hash is None:
            yeni_liste.append(meta_adi)
        elif eski_hash != guncel_hash:
            guncel_liste.append((meta_adi, eski_hash, guncel_hash))
        else:
            atlanan_sayisi += 1

    return yeni_liste, guncel_liste, atlanan_sayisi


def apply_updates(yeni_liste, guncel_liste):
    """Bulunan farkları veritabanına uygula."""
    yeni_eklenen = 0
    guncellenen = 0

    if yeni_liste:
        logger.info("--- YENİ dosyalar ekleniyor (%d) ---", len(yeni_liste))
        for meta_adi in yeni_liste:
            dosya_yolu = str(SKILLS_DIR / meta_adi.replace("/", os.sep))
            try:
                with open(dosya_yolu, "r", encoding="utf-8", errors="replace") as f:
                    icerik = f.read()
            except Exception as e:
                logger.warning("⚠️  Okunamadı: %s — %s", dosya_yolu, e)
                continue

            guncel_hash = dosya_hash(dosya_yolu)
            baslik = ""
            for line in icerik.split("\n"):
                line = line.strip()
                if line.startswith("# "):
                    baslik = line[2:].strip()
                    break
            if not baslik:
                baslik = icerik[:200].strip()

            muhtemel_aciklama = baslik[:500]
            muhtemel_icerik = icerik[:10000]
            su_an = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            con = sqlite3.connect(str(SKILLS_DB))
            try:
                con.execute(
                    "INSERT OR IGNORE INTO beceriler (ad, aciklama, icerik, kaynak) VALUES (?, ?, ?, ?)",
                    (meta_adi, muhtemel_aciklama, muhtemel_icerik, dosya_yolu),
                )
                con.execute(
                    "INSERT OR IGNORE INTO beceriler_meta (ad, dosya_hash, guncelleme) VALUES (?, ?, ?)",
                    (meta_adi, guncel_hash, su_an),
                )
                con.commit()
                yeni_eklenen += 1
            except Exception as e:
                logger.warning("⚠️  DB ekleme hatası (%s): %s", meta_adi, e)
            finally:
                con.close()

            # ogrenme.db
            hedef = meta_adi.replace(".md", "").replace("/", "_")
            try:
                con2 = sqlite3.connect(str(OGRENME_DB))
                con2.execute(
                    """INSERT OR IGNORE INTO ogrenmeler
                       (hedef, cozum, kaynak, basari_sayisi, son_basari, son_kullanim,
                        guven_skoru, kategori, gecerlilik_tarihi)
                       VALUES (?, ?, 'skills_scan', 1, ?, ?, 0.5, ?, datetime('now', '+180 days'))""",
                    (hedef, icerik[:5000], su_an, su_an, "skills/" + meta_adi),
                )
                con2.commit()
                con2.close()
            except Exception as e:
                logger.warning("⚠️  ogrenme.db ekleme hatası: %s", e)

    if guncel_liste:
        logger.info("--- GÜNCELLENEN dosyalar işleniyor (%d) ---", len(guncel_liste))
        for meta_adi, old_hash, new_hash in guncel_liste:
            dosya_yolu = str(SKILLS_DIR / meta_adi.replace("/", os.sep))
            try:
                with open(dosya_yolu, "r", encoding="utf-8", errors="replace") as f:
                    icerik = f.read()
            except Exception as e:
                logger.warning("⚠️  Okunamadı: %s — %s", dosya_yolu, e)
                continue

            baslik = ""
            for line in icerik.split("\n"):
                line = line.strip()
                if line.startswith("# "):
                    baslik = line[2:].strip()
                    break
            if not baslik:
                baslik = icerik[:200].strip()

            muhtemel_aciklama = baslik[:500]
            muhtemel_icerik = icerik[:10000]
            su_an = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            con = sqlite3.connect(str(SKILLS_DB))
            try:
                con.execute(
                    "UPDATE beceriler SET aciklama=?, icerik=?, kaynak=? WHERE ad=?",
                    (muhtemel_aciklama, muhtemel_icerik, dosya_yolu, meta_adi),
                )
                con.execute(
                    "UPDATE beceriler_meta SET dosya_hash=?, guncelleme=? WHERE ad=?",
                    (new_hash, su_an, meta_adi),
                )
                con.commit()
                guncellenen += 1
            except Exception as e:
                logger.warning("⚠️  DB güncelleme hatası (%s): %s", meta_adi, e)
            finally:
                con.close()

            # ogrenme.db
            hedef = meta_adi.replace(".md", "").replace("/", "_")
            try:
                con2 = sqlite3.connect(str(OGRENME_DB))
                var = con2.execute(
                    "SELECT id FROM ogrenmeler WHERE hedef = ?", (hedef,)
                ).fetchone()
                if var:
                    con2.execute(
                        """UPDATE ogrenmeler SET
                            cozum = ?, son_basari = ?, son_kullanim = ?,
                            gecerlilik_tarihi = datetime('now', '+180 days')
                           WHERE hedef = ?""",
                        (icerik[:5000], su_an, su_an, hedef),
                    )
                else:
                    con2.execute(
                        """INSERT INTO ogrenmeler
                           (hedef, cozum, kaynak, basari_sayisi, son_basari, son_kullanim,
                            guven_skoru, kategori, gecerlilik_tarihi)
                           VALUES (?, ?, 'skills_scan', 1, ?, ?, 0.5, ?, datetime('now', '+180 days'))""",
                        (hedef, icerik[:5000], su_an, su_an, "skills/" + meta_adi),
                    )
                con2.commit()
                con2.close()
            except Exception as e:
                logger.warning("⚠️  ogrenme.db güncelleme hatası: %s", e)

    return yeni_eklenen, guncellenen


if __name__ == "__main__":
    print("=== Adım 1: Tarama ve Karşılaştırma ===")
    yeni_liste, guncel_liste, atlanan = scan_only()
    print(f"\nTARAMA SONUCU:")
    print(f"  Yeni (eklenecek):  {len(yeni_liste)}")
    print(f"  Güncellenecek:     {len(guncel_liste)}")
    print(f"  Atlanan (aynı):    {atlanan}")

    if yeni_liste:
        print(f"\n  Yeni dosyalar (ilk 10):")
        for ad in yeni_liste[:10]:
            print(f"    🆕 {ad}")
        if len(yeni_liste) > 10:
            print(f"    ... ve {len(yeni_liste) - 10} daha")

    if guncel_liste:
        print(f"\n  Güncellenen dosyalar (ilk 10):")
        for ad, old, new in guncel_liste[:10]:
            print(f"    🔄 {ad}")
        if len(guncel_liste) > 10:
            print(f"    ... ve {len(guncel_liste) - 10} daha")

    print(f"\n=== Adım 2: Veritabanı Güncellemesi ===")
    if yeni_liste or guncel_liste:
        yeni_eklenen, guncellenen = apply_updates(yeni_liste, guncel_liste)
        print(f"\n✅ GÜNCELLEME TAMAMLANDI:")
        print(f"   Yeni eklenen:  {yeni_eklenen}/{len(yeni_liste)}")
        print(f"   Güncellenen:   {guncellenen}/{len(guncel_liste)}")
    else:
        print("   Hiçbir değişiklik yok, güncelleme gerekmiyor.")

    print(f"\n{'='*60}")
    print(f"📊 ÖZET:")
    print(f"   Toplam .md dosyası:  {len(yeni_liste) + len(guncel_liste) + atlanan}")
    print(f"   Yeni eklenen:        {len(yeni_liste)}")
    print(f"   Güncellenen:         {len(guncel_liste)}")
    print(f"   Atlanan (değişmeyen): {atlanan}")

    # Makine formatı
    print(f"\nSONUC|new={len(yeni_liste)}|updated={len(guncel_liste)}|skipped={atlanan}")
