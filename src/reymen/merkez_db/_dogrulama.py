"""Adim 1: Restart dogrulama - Merkez DB yazma testi"""
import sqlite3, time, os

PROJE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. Merkez DB yazma testi
db = os.path.join(PROJE, "reymen", "merkez_db", "ogrenmeler.db")
print(f"=== YAZMA TESTI: {db} ===")
con = sqlite3.connect(db, timeout=10)
con.execute("CREATE TABLE IF NOT EXISTS test_merkez (id INTEGER PRIMARY KEY, t TEXT, v TEXT)")
con.execute("INSERT INTO test_merkez (t, v) VALUES ('restart_test', ?)", (str(time.time()),))
con.commit()
row = con.execute("SELECT * FROM test_merkez ORDER BY id DESC LIMIT 1").fetchone()
con.execute("DELETE FROM test_merkez")
con.commit()
con.close()
print(f"✅ Merkez DB yazma basarili: {row}")

# 2. Eski DB yollarina yazma kontrolu
import subprocess
r = subprocess.run(
    f'cd /d "{PROJE}" && dir /s /b *.old 2>nul | findstr /v __pycache__',
    shell=True, capture_output=True, text=True
)
print(f"\n=== ESKI DB (.old) KONTROLU ===")
print(f"Toplam .old dosyasi: {len(r.stdout.splitlines())}")

print("\n✅ Adim 1 tamam")
