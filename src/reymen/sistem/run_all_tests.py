# -*- coding: utf-8 -*-
"""run_all_tests.py — Tum Reymen testlerini topluca calistirir."""
import sys, os, time, traceback
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agent"))

# Kategori A: tests/test_*.py
KATEGORI_A = sorted(ROOT.glob("tests/test_*.py"))
# Kategori B: skills/*/tests/test_*.py
KATEGORI_B = sorted(ROOT.glob("skills/*/tests/test_*.py"))
# Kategori D: test_*.py (kok)
KATEGORI_D = sorted(ROOT.glob("test_*.py"))
# Haric: bilinen calisan testler
HARIC = {"test_suite.py", "test_learning_loop.py"}

gecti = []
gecemedi = []
zaman_asimi = []

for fn, kaynak in [(f, "A") for f in KATEGORI_A] + [(f, "B") for f in KATEGORI_B] + [(f, "D") for f in KATEGORI_D if f.name not in HARIC]:
    baslik = f"[{kaynak}] {fn.name}"
    print(f"\n  {'='*50}")
    print(f"  CALISIYOR: {baslik}")
    print(f"  {'='*50}")
    sys.stdout.flush()
    
    basla = time.time()
    try:
        import subprocess
        r = subprocess.run(
            [sys.executable, str(fn)],
            capture_output=True, text=True, timeout=120,
            cwd=str(ROOT)
        )
        sure = time.time() - basla
        cikti = r.stdout.strip() + "\n" + r.stderr.strip()
        
        if r.returncode == 0:
            gecti.append((fn.name, kaynak, sure))
            print(f"  GECTI ({sure:.1f}s)")
            # Son 3 satir
            for line in cikti.split("\n")[-3:]:
                if line.strip():
                    print(f"    {line.strip()}")
        else:
            gecemedi.append((fn.name, kaynak, sure, cikti[-500:]))
            print(f"  BASARISIZ ({sure:.1f}s)")
            # Hata mesaji
            for line in cikti.split("\n")[-5:]:
                if line.strip():
                    print(f"    {line.strip()}")
    except subprocess.TimeoutExpired:
        zaman_asimi.append((fn.name, kaynak))
        print(f"  ZAMAN ASIMI (120s)")
    except Exception as e:
        gecemedi.append((fn.name, kaynak, 0, str(e)[:200]))
        print(f"  HATA: {e}")
    
    sys.stdout.flush()

print("\n" + "="*55)
print(f"  SONUC RAPORU")
print("="*55)
print(f"  GECTI:      {len(gecti)}")
print(f"  BASARISIZ:  {len(gecemedi)}")
print(f"  ZAMAN ASIMI: {len(zaman_asimi)}")
print(f"  TOPLAM:     {len(gecti) + len(gecemedi) + len(zaman_asimi)}")
print()

if gecti:
    print("  Basarili:")
    for ad, kat, sure in gecti:
        print(f"    ✅ [{kat}] {ad} ({sure:.1f}s)")

if gecemedi:
    print("  Basarisiz:")
    for ad, kat, sure, hata in gecemedi:
        hata_kisa = hata.strip()[:120].replace("\n", " | ")
        print(f"    ❌ [{kat}] {ad} — {hata_kisa}")
        print(f"       ({sure:.1f}s)")

if zaman_asimi:
    print("  Zaman asimi:")
    for ad, kat in zaman_asimi:
        print(f"    ⏰ [{kat}] {ad}")
