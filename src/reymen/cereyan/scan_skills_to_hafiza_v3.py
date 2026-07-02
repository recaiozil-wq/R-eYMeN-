# -*- coding: utf-8 -*-
"""
scan_skills_to_hafiza_v3.py — SADECE TARA VE RAPORLA, veritabanına dokunma.
"""

import hashlib
import logging
import os
import sqlite3
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scan_skills")

ROOT = Path(__file__).parent.parent.resolve()
SKILLS_DIR = ROOT / "cereyan" / "skills"
SKILLS_DB = ROOT / "cereyan" / ".ReYMeN" / "skills_index.db"
OGRENME_DB = ROOT / "hafiza" / "ogrenme.db"


def dosya_hash(dosya_yolu):
    h = hashlib.sha256()
    with open(dosya_yolu, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def kategori_ve_ad(dosya_yolu):
    rel = os.path.relpath(dosya_yolu, str(SKILLS_DIR))
    rel = rel.replace("\\", "/")
    parts = rel.split("/")
    if len(parts) == 1:
        return "", parts[0]
    return "/".join(parts[:-1]), parts[-1]


# 1) Skills dizinindeki tüm .md dosyalarını bul
md_dosyalari = sorted(SKILLS_DIR.rglob("*.md"))
print(f"📄 Skills klasöründe {len(md_dosyalari)} .md dosyası bulundu.", flush=True)

# 2) Skills DB meta tablosu
con = sqlite3.connect(str(SKILLS_DB))
meta_cur = con.execute("SELECT ad, dosya_hash FROM beceriler_meta")
meta_map = {}
for row in meta_cur.fetchall():
    meta_map[row[0]] = row[1]
con.close()
print(f"📚 Skills DB'de {len(meta_map)} kayıtlı dosya var.", flush=True)

# 3) Her dosyayı kontrol et
yeni_liste = []
guncel_liste = []
atlanan = 0

for i, dosya in enumerate(md_dosyalari):
    if i > 0 and i % 250 == 0:
        print(f"  ... {i}/{len(md_dosyalari)} dosya taranıyor...", flush=True)
    
    kategori, dosya_adi = kategori_ve_ad(str(dosya))
    meta_adi = f"{kategori}/{dosya_adi}" if kategori else dosya_adi

    try:
        guncel_hash = dosya_hash(str(dosya))
    except (OSError, IOError):
        continue

    eski_hash = meta_map.get(meta_adi)
    if eski_hash is None:
        yeni_liste.append(meta_adi)
    elif eski_hash != guncel_hash:
        guncel_liste.append(meta_adi)
    else:
        atlanan += 1

print(f"\n{'='*60}")
print(f"📊 SCAN RAPORU")
print(f"{'='*60}")
print(f"  Toplam .md dosyası:           {len(md_dosyalari)}")
print(f"  DB'de kayıtlı:                {len(meta_map)}")
print(f"  🆕 Yeni (eklenecek):          {len(yeni_liste)}")
print(f"  🔄 Güncellenecek:             {len(guncel_liste)}")
print(f"  ⏭  Atlanan (değişmeyen):      {atlanan}")
print(f"{'='*60}")

if yeni_liste:
    print(f"\n🆕 Yeni dosyalar ({len(yeni_liste)}):")
    for ad in yeni_liste[:15]:
        print(f"    + {ad}")
    if len(yeni_liste) > 15:
        print(f"    ... ve {len(yeni_liste) - 15} daha")

if guncel_liste:
    print(f"\n🔄 Güncellenen dosyalar ({len(guncel_liste)}):")
    for ad in guncel_liste[:15]:
        print(f"    ~ {ad}")
    if len(guncel_liste) > 15:
        print(f"    ... ve {len(guncel_liste) - 15} daha")

# Makine formatı
print(f"\nSONUC|new={len(yeni_liste)}|updated={len(guncel_liste)}|skipped={atlanan}")
