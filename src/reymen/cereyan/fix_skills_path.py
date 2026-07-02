# -*- coding: utf-8 -*-
"""fix_skills_path.py — Skills dizin karmasasini temizle.

TUM skills dizinlerini tek bir merkezi dizine yonlendirir:
  MERKEZ: reymen/cereyan/skills/ (kategorize edilmis yapi)

Akis:
  1. Katalogdaki tum skills dizinlerini tara
  2. Merkezi dizine symlink/redirect ekle
  3. SkillLibrary.sync() ile merkezi dizini kutuphaneye isle
"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Proje koku
PROJE_KOK = Path(__file__).resolve().parent.parent.parent  # ReYMeN-Ajan/

# Merkezi skills dizini (kategorize edilmis yapi)
MERKEZI_SKILLS = Path(__file__).resolve().parent / "skills"  # cereyan/skills/

# Tum skills dizinleri (__pycache__, node_modules, .git, .venv haric)
TUM_SKILLS_DIZINLERI = [
    PROJE_KOK / "skills",                            # root skills/ (duz .md)
    PROJE_KOK / ".ReYMeN" / "skills",                # .ReYMeN/skills/
    PROJE_KOK / "reymen" / "cereyan" / "skills",     # cereyan/skills/ (MERKEZ)
    PROJE_KOK / "reymen" / "cereyan" / ".ReYMeN" / "skills",  # cereyan/.ReYMeN/skills/
    PROJE_KOK / "reymen" / "hafiza" / ".ReYMeN" / "skills",  # hafiza/.ReYMeN/skills/
    PROJE_KOK / "hermes_legacy" / "skills",          # hermes_legacy/skills/
]


def _skills_ozet() -> dict[str, int]:
    """Her skills dizinindeki .md dosya sayisini dondur."""
    ozet = {}
    for dizin in TUM_SKILLS_DIZINLERI:
        if dizin.exists():
            sayi = len(list(dizin.rglob("*.md")))
            ozet[str(dizin.relative_to(PROJE_KOK) if dizin.is_relative_to(PROJE_KOK) else dizin)] = sayi
    return ozet


def _merkezi_tara() -> list[Path]:
    """Merkezi skills dizinindeki tum .md dosyalarini listele."""
    if not MERKEZI_SKILLS.exists():
        return []
    return sorted(MERKEZI_SKILLS.rglob("*.md"))


def _root_skills_tara() -> list[Path]:
    """Root skills/ dizinindeki .md dosyalarini listele (yeni eklenen, kategorize edilmemis)."""
    root_skills = PROJE_KOK / "skills"
    if not root_skills.exists():
        return []
    return sorted(root_skills.rglob("*.md"))


def _yeni_skill_tasi() -> int:
    """Root skills/'e yeni eklenmis .md dosyalarini merkezi dizine tasi.

    Eger root skills/'deki bir .md dosyasi merkezi dizinde yoksa,
    kullaniciya bildir (otomatik tasima yapilmaz — kategorizasyon gerekebilir).
    """
    root_md = _root_skills_tara()
    if not root_md:
        return 0

    merkez_md = {p.name for p in _merkezi_tara()}
    yeni = [p for p in root_md if p.name not in merkez_md]
    if yeni:
        print(f"  [!] Root skills/ dizininde {len(yeni)} yeni/yedek .md dosyasi bulundu:")
        for p in yeni:
            print(f"      - {p.name}")
        print(f"  [!) Bunlari manuel olarak reymen/cereyan/skills/<kategori>/ altina tasiyin.")
    return len(yeni)


def sync_all(target_dir: str | Path | None = None) -> dict:
    """Butun skills dizinlerini SkillLibrary ile senkronize et.

    Args:
        target_dir: Senkronize edilecek dizin (None = merkezi dizin).

    Returns:
        Sync sonucu.
    """
    from reymen.cereyan.skill_library import SkillLibrary

    lib = SkillLibrary()
    kaynak = Path(target_dir) if target_dir else MERKEZI_SKILLS

    print(f"\n  [Skills Path] Merkezi dizin senkronize ediliyor: {kaynak}")
    print(f"  [Skills Path] DB yolu: {lib._db_yolu}")

    # Merkezi dizini sync et
    sonuc = lib.sync(kaynak)

    # Root skills/'i de sync et (flat yapi, ek ozellikler)
    root_skills = PROJE_KOK / "skills"
    if root_skills.exists():
        print(f"  [Skills Path] Root skills/ de senkronize ediliyor: {root_skills}")
        root_sonuc = lib.sync(root_skills)
        for k, v in root_sonuc.items():
            sonuc[k] = sonuc.get(k, 0) + v

    print(f"  [Skills Path] Sync tamam: {sonuc}")
    return sonuc


def durum_bildir():
    """Mevcut skills durumunu bildir."""
    print(f"\n{'=' * 60}")
    print(f"  Skills Dizin Durumu")
    print(f"{'=' * 60}")
    print(f"  Merkezi dizin: {MERKEZI_SKILLS}")
    print(f"  Proje koku:    {PROJE_KOK}")
    print()

    ozet = _skills_ozet()
    if ozet:
        print(f"  Mevcut skills dizinleri:")
        for dizin, sayi in sorted(ozet.items()):
            is_merkez = " [MERKEZ]" if (PROJE_KOK / dizin).resolve() == MERKEZI_SKILLS.resolve() else ""
            print(f"    {dizin:<50} {sayi:>4} .md{is_merkez}")
    else:
        print(f"  Skills dizini bulunamadi.")

    merkez_sayisi = len(_merkezi_tara())
    print(f"\n  Merkezi dizindeki skill sayisi: {merkez_sayisi}")

    yeni_sayisi = _yeni_skill_tasi()

    print(f"\n  Oneri:")
    print(f"    Kullan:  python -c 'from reymen.cereyan.fix_skills_path import *; sync_all()'")
    print(f"    Durum:   python -c 'from reymen.cereyan.fix_skills_path import *; durum_bildir()'")


if __name__ == "__main__":
    durum_bildir()
    if "--sync" in sys.argv:
        sync_all()
