#!/usr/bin/env python3
"""duplicate_module_detector.py — ReYMeN projesindeki ReYMeN kopyası modülleri tespit eder.

Kullanım:
    python reymen/scripts/duplicate_module_detector.py
        
Şunları raporlar:
    - ReYMeN mirror dizinleri ve boyutları
    - .py dosya sayıları / kopya tahmini
    - Önerilen temizlik aksiyonları
"""

import os
import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

HERMES_MIRROR_DIRS = [
    "agent",
    "acp",
    "acp_adapter",
    "skills",
    "ReYMeN_cli",
    "hermes-memory-backup",
    "ReYMeN-full-backup",
    "plugins",
    "tools",
    "providers",
    "processors",
    "proxy",
    "optional-skills",
    "hermes_legacy",
]

REYMEN_CORE_DIRS = [
    "reymen",
    "telegram_bot",
    "gateway",
    "tests",
    "cron",
    "dashboard",
    "desktop",
    "scripts",
]

def scan_mirror_dirs(proje_koku: Path):
    """ReYMeN mirror dizinlerini tara ve raporla."""
    sonuc = []
    toplam_mirror_py = 0
    toplam_mirror_bytes = 0
    
    for d in HERMES_MIRROR_DIRS:
        yol = proje_koku / d
        if yol.exists() and yol.is_dir():
            py_dosyalar = list(yol.rglob("*.py"))
            py_sayisi = len(py_dosyalar)
            toplam_boyut = sum(f.stat().st_size for f in py_dosyalar if f.is_file())
            toplam_mirror_py += py_sayisi
            toplam_mirror_bytes += toplam_boyut
            sonuc.append({
                "dizin": d,
                "py_sayisi": py_sayisi,
                "boyut_kb": round(toplam_boyut / 1024, 1),
            })
    
    # ReYMeN core dizinlerini de tara (referans için)
    core_py = 0
    for d in REYMEN_CORE_DIRS:
        yol = proje_koku / d
        if yol.exists() and yol.is_dir():
            core_py += len(list(yol.rglob("*.py")))
    
    return sonuc, toplam_mirror_py, toplam_mirror_bytes, core_py


def find_identical_files(proje_koku: Path):
    """ReYMeN mirror ile ReYMeN core arasında birebir aynı .py dosyalarını bul."""
    mirrors = {}
    for d in HERMES_MIRROR_DIRS:
        yol = proje_koku / d
        if yol.exists():
            for f in yol.rglob("*.py"):
                # normalize path
                rel = f.relative_to(yol)
                mirrors[rel] = mirrors.get(rel, []) + [str(f)]
    
    core_set = set()
    for d in REYMEN_CORE_DIRS:
        yol = proje_koku / d
        if yol.exists():
            for f in yol.rglob("*.py"):
                try:
                    core_set.add(str(f.relative_to(yol)))
                except ValueError as _e:
                    logger.warning("[DuplicateModuleDetector] Gecersiz deger (L93): %s", ValueError)
                    pass
    
    # Mirror'da olup core'da olmayan dosyalar
    only_in_mirror = set(mirrors.keys()) - core_set
    return only_in_mirror, mirrors


def main():
    proje_koku = Path.cwd()
    
    # .ReYMeN/ veya reymen/ varlığını kontrol et
    if not (proje_koku / "reymen").exists():
        print(f"HATA: Bu bir ReYMeN proje kökü değil: {proje_koku}")
        print("Lütfen ReYMeN-Ajan dizininde çalıştırın.")
        sys.exit(1)
    
    print(f"📁 ReYMeN-Ajan: {proje_koku}")
    print()
    
    # 1. Mirror dizinleri tara
    mirror_list, mirror_py, mirror_bytes, core_py = scan_mirror_dirs(proje_koku)
    
    print(f"{'='*60}")
    print(f"📊 ReYMeN MIRROR DURUMU")
    print(f"{'='*60}")
    print(f"{'Dizin':<25} {'PY':>6} {'Boyut':>10}")
    print(f"{'-'*45}")
    for m in sorted(mirror_list, key=lambda x: -x["py_sayisi"]):
        print(f"{m['dizin']:<25} {m['py_sayisi']:>6} {m['boyut_kb']:>8} KB")
    print(f"{'-'*45}")
    print(f"{'TOPLAM MIRROR':<25} {mirror_py:>6} {round(mirror_bytes/1024,1):>8} KB")
    print(f"{'REYMEN CORE':<25} {core_py:>6}")
    
    # 2. Oran hesapla
    toplam_py = mirror_py + core_py
    drift_orani = round((mirror_py / max(toplam_py, 1)) * 100, 1)
    print(f"\n📈 Drift Oranı: %{drift_orani} (mirror/toplam)")
    print(f"   Hedef: %5 altı")
    
    # 3. Aynı dosya tespiti
    only_mirror, _ = find_identical_files(proje_koku)
    print(f"\n🔍 Sadece Mirror'da Olan Benzersiz Dosyalar: {len(only_mirror)}")
    if only_mirror:
        print(f"   Örnekler:")
        for f in sorted(list(only_mirror))[:10]:
            print(f"   - {f}")
        if len(only_mirror) > 10:
            print(f"   ... ve {len(only_mirror)-10} daha")
    
    # 4. Öneriler
    print(f"\n{'='*60}")
    print(f"📋 ÖNERİLEN AKSİYONLAR")
    print(f"{'='*60}")
    
    oneriler = []
    for m in sorted(mirror_list, key=lambda x: -x["py_sayisi"]):
        if m["py_sayisi"] > 50:
            oneriler.append(f"🔴 {m['dizin']}: {m['py_sayisi']} dosya — silmeyi değerlendir")
        elif m["py_sayisi"] > 10:
            oneriler.append(f"🟡 {m['dizin']}: {m['py_sayisi']} dosya — gözden geçir")
    
    if not oneriler:
        print("✅ Mirror dizinleri temiz veya küçük.")
    else:
        for o in oneriler:
            print(f"   {o}")
    
    # 5. Özet
    print(f"\n{'='*60}")
    print(f"📋 ÖZET")
    print(f"{'='*60}")
    print(f"✅ Mevcut drift: %{drift_orani}")
    print(f"🎯 Hedef: %5 altı")
    if drift_orani > 5:
        print(f"⚠️  {mirror_py} mirror .py dosyası temizlenmeli")
    else:
        print(f"✅ Hedef tutturuldu!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
