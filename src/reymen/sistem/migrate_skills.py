# -*- coding: utf-8 -*-
"""
migrate_skills.py — Tek seferlik veri taşıma betiği.

Mevcut skills/ dizinindeki frontmatter içermeyen .md dosyalarına
standart YAML frontmatter ekler. Önce skills_backup/ yedeği alır.

Kullanim:
    python migrate_skills.py
"""
import os
import sys
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
import logging
logger = logging.getLogger(__name__)


ROOT = Path(__file__).parent.resolve()
SKILLS_DIR = ROOT / "skills"
BACKUP_DIR = ROOT / "skills_backup"


def _skill_id_uret(ad: str) -> str:
    """Dosya adindan benzersiz skill_id (MD5 hash, ilk 12 karakter)."""
    temiz = ad.lower().strip().replace(" ", "_")
    temiz = "".join(c for c in temiz if c.isalnum() or c in "_-")
    return hashlib.md5(temiz.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]


def _frontmatter_iceriyor(icerik: str) -> bool:
    """Dosyanin basinda YAML frontmatter (---) var mi? (CRLF/LF uyumlu)"""
    norm = icerik.replace("\r\n", "\n")
    return norm.startswith("---\n")


def _fts5_index_guncelle(dosya_yolu: str, icerik: str) -> None:
    """FTS5 index'indeki ilgili kaydin icerik alanini guncelle.

    closed_learning_loop.py'deki FTS5 veritabanina yazar.
    Bagimsiz calistigi icin hata sessizce loglanir, betik durmaz.
    """
    import sqlite3
    ROOT = Path(__file__).parent.resolve()
    db_yolu = str(ROOT / ".ReYMeN" / "skills_index.db")
    if not os.path.isfile(db_yolu):
        return  # Henuz index yoksa sorun degil
    try:
        con = sqlite3.connect(db_yolu, timeout=5)
        # Adi dosya yolundan cikar (tum_becerileri_indeksle mantigi ile ayni)
        # skills/ altindaki goreli yol
        dizin = ROOT / "skills"
        try:
            goreli = Path(dosya_yolu).relative_to(dizin)
            anahtar = str(goreli.with_suffix("")).replace("\\", "/")
        except Exception:
            anahtar = Path(dosya_yolu).stem
        con.execute(
            "UPDATE beceriler SET icerik=? WHERE kaynak=?",
            (icerik, str(dosya_yolu)),
        )
        con.commit()
        con.close()
    except sqlite3.Error as e:
        print(f"[Migration] FTS5 index uyarisi: {e}")


def _frontmatter_olustur(ad: str) -> str:
    """Standart YAML frontmatter bloku."""
    skill_id = _skill_id_uret(ad)
    bugun = datetime.now().strftime("%Y-%m-%d")
    return (
        "---\n"
        f"skill_id: {skill_id}\n"
        f"usage_count: 1\n"
        f"last_used: {bugun}\n"
        "---\n"
    )


def yedek_al() -> bool:
    """skills/ dizinini skills_backup/ olarak kopyala.
    Eski yedek varsa once silmeyi dener, olmazsa zaman damgali yedek alir.
    """
    if not SKILLS_DIR.exists():
        print("[Migration] skills/ dizini bulunamadi.")
        return False

    # Eski yedek varsa silmeyi dene
    if BACKUP_DIR.exists():
        try:
            shutil.rmtree(BACKUP_DIR)
            print("[Migration] Eski skills_backup/ silindi.")
        except OSError as e:
            print(f"[Migration] Eski yedek silinemedi: {e}")
            print("[Migration] Zaman damgali yedek aliniyor...")
            # Alternatif: zaman damgali yedek
            zaman_damgali = BACKUP_DIR.parent / f"skills_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copytree(SKILLS_DIR, zaman_damgali)
            print(f"[Migration] Yedek alindi: {zaman_damgali}")
            return True

    try:
        shutil.copytree(SKILLS_DIR, BACKUP_DIR)
        print(f"[Migration] Yedek alindi: {BACKUP_DIR}")
        return True
    except OSError as e:
        print(f"[Migration] Yedek alma hatasi: {e}")
        return False


def migration_yap() -> int:
    """Frontmatter'siz .md dosyalarina YAML frontmatter ekle.

    Returns:
        int: Guncellenen dosya sayisi
    """
    if not SKILLS_DIR.exists():
        print(f"[Migration] skills/ dizini bulunamadi: {SKILLS_DIR}")
        return 0

    guncellenen = 0
    hata_sayisi = 0

    for dosya in sorted(SKILLS_DIR.rglob("*.md")):
        try:
            icerik = dosya.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"[Migration] Okuma hatasi ({dosya}): {e}")
            hata_sayisi += 1
            continue

        # Frontmatter zaten varsa atla
        if _frontmatter_iceriyor(icerik):
            continue

        # Frontmatter olustur ve ekle
        ad = dosya.stem
        frontmatter = _frontmatter_olustur(ad)
        yeni_icerik = frontmatter + icerik.lstrip("\n")

        try:
            dosya.write_text(yeni_icerik, encoding="utf-8")
            # FTS5 index'i de guncelle
            _fts5_index_guncelle(str(dosya), yeni_icerik)
            print(f"  + {dosya.relative_to(ROOT)}")
            guncellenen += 1
        except OSError as e:
            print(f"[Migration] Yazma hatasi ({dosya}): {e}")
            hata_sayisi += 1

    if hata_sayisi:
        print(f"[Migration] {hata_sayisi} dosyada hata olustu.")

    return guncellenen


def main():
    print("=" * 50)
    print("  migrate_skills.py — Veri Taşıma Betiği")
    print(f"  Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    print()

    # 1. Yedek al
    print("[1/3] Yedek aliniyor...")
    if not yedek_al():
        print("[Migration] Yedek alinamadi. Devam ediliyor mu? (Ctr+C ile iptal)")
    print()

    # 2. Frontmatter'siz dosyalari tara
    print("[2/3] Frontmatter'siz dosyalar taranıyor...")
    toplam_md = sum(1 for _ in SKILLS_DIR.rglob("*.md"))
    frontmatterli = 0
    frontmattersiz = 0

    for dosya in SKILLS_DIR.rglob("*.md"):
        try:
            icerik = dosya.read_text(encoding="utf-8", errors="replace")
            if _frontmatter_iceriyor(icerik):
                frontmatterli += 1
            else:
                frontmattersiz += 1
        except OSError:
            frontmattersiz += 1

    print(f"  Toplam .md: {toplam_md}")
    print(f"  Frontmatter'li: {frontmatterli}")
    print(f"  Frontmatter'siz: {frontmattersiz}")
    print()

    if frontmattersiz == 0:
        print("[Migration] Guncellenecek dosya yok. Tüm dosyalar frontmatter içeriyor.")
        print("[Migration] Migration tamamlandi: 0 dosya guncellendi.")
        return

    # 3. Migration uygula
    print(f"[3/3] {frontmattersiz} dosyaya frontmatter ekleniyor...")
    guncellenen = migration_yap()

    print()
    print(f"[Migration] Migration tamamlandi: {guncellenen} dosya guncellendi.")
    print(f"[Migration] Yedek: {BACKUP_DIR}")


if __name__ == "__main__":
    main()
