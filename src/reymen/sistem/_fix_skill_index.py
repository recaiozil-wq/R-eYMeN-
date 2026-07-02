#!/usr/bin/env python3
"""Fix skill_index.db - only broken DB"""
import sqlite3, os, shutil
import logging
logger = logging.getLogger(__name__)

BROKEN = r'C:\Users\marko\Desktop\Reymen Proje\hermes_projesi\.ReYMeN\skill_index.db'
GOOD = r'C:\Users\marko\Desktop\Reymen Proje\hermes_projesi\.ReYMeN\skills_index.db'

size = os.path.getsize(BROKEN)
print(f"BOZUK DB: skill_index.db ({size//1024}KB)")

# 1) Try to recover using SQLite recover
try:
    print("\n[1/3] Attempting SQLite recovery...")
    import subprocess
    # Use sqlite3 CLI to dump and recreate
    result = subprocess.run(
        ['sqlite3', BROKEN, '.recover', '|', 'sqlite3', BROKEN + '.recovered'],
        capture_output=True, text=True, timeout=30
    )
    recovered = BROKEN + '.recovered'
    if os.path.exists(recovered):
        rsize = os.path.getsize(recovered)
        print(f"  Recovered DB: {rsize}KB")
        # Check recovered integrity
        conn = sqlite3.connect(recovered)
        c = conn.cursor()
        c.execute("PRAGMA integrity_check")
        integrity = c.fetchone()[0]
        print(f"  Recovered integrity: {integrity}")
        conn.close()
        
        if integrity == 'ok' and rsize > 1000:
            # Replace broken with recovered
            os.replace(recovered, BROKEN)
            print("  ✅ Recovered DB replaced original")
        else:
            print(f"  Recovered DB invalid, trying alternative...")
            if os.path.exists(recovered):
                os.remove(recovered)
    else:
        print(f"  Recovery failed")
except Exception as e:
    print(f"  Recovery error: {e}")

# 2) If recovery failed, check if it's a copy of skills_index.db
print(f"\n[2/3] Checking if it's a copy of skills_index.db...")
try:
    # Try to open it as-is  
    conn = sqlite3.connect(BROKEN)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    print(f"  Tables accessible: {len(tables)}")
    conn.close()
except sqlite3.Error:
    
    # 3) Rebuild from scratch using skills_index.db data
    print(f"\n[3/3] Rebuilding from skills_index.db...")
    if os.path.exists(GOOD):
        conn_good = sqlite3.connect(GOOD)
        cg = conn_good.cursor()
        
        # Check what's in the good one
        try:
            cg.execute("SELECT COUNT(*) FROM beceriler")
            good_count = cg.fetchone()[0]
            print(f"  Source skills_index.db: {good_count} records")
            
            # Create a clean skill_index.db
            if os.path.exists(BROKEN):
                os.rename(BROKEN, BROKEN + '.corrupted')
            
            conn_new = sqlite3.connect(BROKEN)
            cn = conn_new.cursor()
            
            # Create the same structure as the good one
            cn.execute("CREATE VIRTUAL TABLE skill_fts USING fts5(ad, aciklama, icerik, kaynak, content='', tokenize='unicode61')")
            
            # Copy data
            cg.execute("SELECT ad, aciklama, icerik, kaynak FROM beceriler")
            rows = cg.fetchall()
            cn.execute("BEGIN TRANSACTION")
            for row in rows:
                cn.execute("INSERT INTO skill_fts (ad, aciklama, icerik, kaynak) VALUES (?, ?, ?, ?)", row)
            conn_new.commit()
            
            # Verify
            cn.execute("SELECT COUNT(*) FROM skill_fts")
            new_count = cn.fetchone()[0]
            print(f"  New skill_index.db: {new_count} records")
            print(f"  ✅ Rebuilt successfully!" if new_count == good_count else f"  ⚠️ Count mismatch: {new_count} vs {good_count}")
            
            conn_new.close()
            conn_good.close()
            
        except Exception as e:
            print(f"  Error rebuilding: {e}")
    else:
        print(f"  Source skills_index.db not found at: {GOOD}")
