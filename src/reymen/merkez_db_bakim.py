"""merkez_db_bakim.py — Haftalık WAL checkpoint + boyut raporu."""
import sqlite3, os, json
from pathlib import Path

DB_DIR = Path(__file__).parent / "merkez_db"
CIKTI = []

for db in sorted(DB_DIR.glob("*.db")):
    try:
        con = sqlite3.connect(str(db), timeout=10)
        cur = con.cursor()
        # WAL checkpoint
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        sonuc = cur.fetchone()
        # Boyut
        boyut = db.stat().st_size
        CIKTI.append(f"{db.name}: {boyut//1024}KB checkpoint={sonuc}")
        con.close()
    except Exception as e:
        CIKTI.append(f"{db.name}: HATA {e}")

print(f"Merkez DB Bakım — {len(CIKTI)} DB işlendi")
print("\n".join(CIKTI))
