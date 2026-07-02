# -*- coding: utf-8 -*-
"""
scan_skills_apply.py — Kalan güncellemeleri uygula.
118 dosya güncellenecek.
"""

import hashlib
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scan_skills_apply")

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

# Find files that need updating
md_dosyalari = sorted(SKILLS_DIR.rglob("*.md"))

con = sqlite3.connect(str(SKILLS_DB))
meta_map = dict(con.execute("SELECT ad, dosya_hash FROM beceriler_meta").fetchall())
con.close()

guncellenecek = []
for dosya in md_dosyalari:
    kategori, dosya_adi = kategori_ve_ad(str(dosya))
    meta_adi = f"{kategori}/{dosya_adi}" if kategori else dosya_adi
    try:
        guncel_hash = dosya_hash(str(dosya))
    except:
        continue
    eski_hash = meta_map.get(meta_adi)
    if eski_hash and eski_hash != guncel_hash:
        guncellenecek.append((meta_adi, str(dosya), guncel_hash))

print(f"Güncellenecek dosya sayısı: {len(guncellenecek)}")

# Apply updates in batches
guncellenen = 0
for i, (meta_adi, dosya_yolu, new_hash) in enumerate(guncellenecek):
    if i > 0 and i % 50 == 0:
        print(f"  ... {i}/{len(guncellenecek)} işlendi...", flush=True)
    
    try:
        with open(dosya_yolu, "r", encoding="utf-8", errors="replace") as f:
            icerik = f.read()
    except:
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
    
    # Update skills_index.db
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
    except Exception as e:
        logger.warning("DB hatasi %s: %s", meta_adi, e)
    finally:
        con.close()
    
    # Update ogrenme.db
    hedef = meta_adi.replace(".md", "").replace("/", "_")
    try:
        con2 = sqlite3.connect(str(OGRENME_DB))
        var = con2.execute("SELECT id FROM ogrenmeler WHERE hedef = ?", (hedef,)).fetchone()
        if var:
            con2.execute(
                """UPDATE ogrenmeler SET cozum=?, son_basari=?, son_kullanim=?,
                   gecerlilik_tarihi=datetime('now','+180 days') WHERE hedef=?""",
                (icerik[:5000], su_an, su_an, hedef),
            )
        else:
            con2.execute(
                """INSERT INTO ogrenmeler (hedef, cozum, kaynak, basari_sayisi, son_basari,
                   son_kullanim, guven_skoru, kategori, gecerlilik_tarihi)
                   VALUES (?, ?, 'skills_scan', 1, ?, ?, 0.5, ?, datetime('now','+180 days'))""",
                (hedef, icerik[:5000], su_an, su_an, "skills/" + meta_adi),
            )
        con2.commit()
        con2.close()
        guncellenen += 1
    except Exception as e:
        logger.warning("ogrenme.db hatasi %s: %s", hedef, e)

print(f"\n✅ Güncelleme tamamlandı: {guncellenen}/{len(guncellenecek)} dosya güncellendi.")
print(f"SONUC|updated={guncellenen}")
