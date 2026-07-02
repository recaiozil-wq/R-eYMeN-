"""disk_izleme.py — Günlük disk + DB boyut kontrolü."""
import shutil, json
from pathlib import Path

PROJE = Path(__file__).parent
DB_DIR = PROJE / "reymen" / "merkez_db"

# Disk kontrol
toplam, kullanilan, bos = shutil.disk_usage(PROJE)
orani = (kullanilan / toplam) * 100

rapor = []
if orani > 85:
    rapor.append(f"⚠️ Disk %{orani:.0f} dolu! ({bos//1024**3}GB boş)")
else:
    rapor.append(f"✅ Disk %{orani:.0f} ({bos//1024**3}GB boş)")

# skills_index.db boyut
si_db = DB_DIR / "skills_index.db"
if si_db.exists():
    mb = si_db.stat().st_size / 1024 / 1024
    if mb > 120:
        rapor.append(f"⚠️ skills_index.db: {mb:.0f}MB (limit: 120MB)")
    else:
        rapor.append(f"✅ skills_index.db: {mb:.0f}MB")

# .old yaş kontrolü
for f in sorted(PROJE.rglob("*.old")):
    yas = (__import__('datetime').datetime.now() - 
           __import__('datetime').datetime.fromtimestamp(f.stat().st_mtime)).days
    if yas > 7:
        rapor.append(f"⚠️ {f.name}: {yas} günlük .old — silinebilir")

print(" | ".join(rapor) if rapor else "✅ Her şey normal")
