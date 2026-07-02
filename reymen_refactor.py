#!/usr/bin/env python3
"""reymen_refactor.py — ReYMeN projesini src/ yapısına taşı.

1. Yeni dizin yapısını oluştur
2. Dosyaları taşı (kopyala)
3. Import'ları güncelle
4. Eski dizini temizle
"""

import os
import shutil
import re
import sys
from pathlib import Path

PROJE = Path(__file__).resolve().parent
REYMEN_ESKI = PROJE / "reymen"

# Yeni yapi
SRC = PROJE / "src"
SRC_REYMEN = SRC / "reymen"
SRC_GATEWAYS = SRC / "gateways"
SRC_CORE = SRC / "core"
EXAMPLES = PROJE / "examples"
TESTS = PROJE / "tests"

# Eski -> Yeni dizin eslemeleri
DIZIN_MAP = {
    # src/reymen/ altina tasinacaklar (framework cekirdegi)
    "cereyan": SRC_REYMEN / "cereyan",
    "arac": SRC_REYMEN / "arac",
    "plugin": SRC_REYMEN / "plugin",
    "plugins": SRC_REYMEN / "plugins",
    "hafiza": SRC_REYMEN / "hafiza",
    "guvenlik": SRC_REYMEN / "guvenlik",
    "sistem": SRC_REYMEN / "sistem",
    "scripts": SRC_REYMEN / "scripts",
    "cli": SRC_REYMEN / "cli",
    "reymen_cli": SRC_REYMEN / "cli",
    "bin": SRC_REYMEN / "bin",
    "tools": SRC_REYMEN / "tools",
    "mcp": SRC_REYMEN / "mcp",
    "web_ui": SRC_REYMEN / "web_ui",
    "desktop": SRC_REYMEN / "desktop",
    "windows": SRC_REYMEN / "windows",
    "memory": SRC_REYMEN / "memory",
    "cron": SRC_REYMEN / "cron",
    "cron_data": SRC_REYMEN / "cron_data",
    "altin_kayitlar": SRC_REYMEN / "altin_kayitlar",
    "gecmis_konusmalar": SRC_REYMEN / "gecmis_konusmalar",
    "merkez_db": SRC_REYMEN / "merkez_db",
    "merkez_db_yedek": SRC_REYMEN / "merkez_db",
    "ses_orneklem": SRC_REYMEN / "ses_orneklem",
    "video_cache": SRC_REYMEN / "video_cache",
    "logs": SRC_REYMEN / "logs",
    
    # src/gateways/ altina tasinacaklar
    "ag": SRC_GATEWAYS,
    "gateway": SRC_GATEWAYS,
    "telegram_bot": SRC_GATEWAYS / "telegram_bot",
    
    # src/core/ altina tasinacaklar
    "core": SRC_CORE,
    
    # tests/
    "test": TESTS,
}

# Kok dizindeki reymen/*.py dosyalari (alt dizinde olmayanlar)
KOK_PY = [
    "__init__.py", "__main__.py", "api_server.py",
    "a2a.py", "a2a_distributed.py", "a2a_integration.py",
    "a2a_transport.py", "cost_tracker.py",
    "kanban.py", "platform_adapter.py",
    "self_improve.py", "tui.py", "video_tools.py",
    "web_search_provider.py", "web_search_registry.py",
    "web_ui.py", "console.py",
    "disk_izleme.py", "dusuk_oncelik_cli.py",
    "merkez_db_bakim.py", "old_temizle.py",
    "KAZANIMLAR.md",
]

# Import donusumleri
IMPORT_MAP = {
    "reymen.cereyan": "src.reymen.cereyan",
    "reymen.arac": "src.reymen.arac",
    "reymen.plugin": "src.reymen.plugin",
    "reymen.plugins": "src.reymen.plugins",
    "reymen.hafiza": "src.reymen.hafiza",
    "reymen.guvenlik": "src.reymen.guvenlik",
    "reymen.sistem": "src.reymen.sistem",
    "reymen.scripts": "src.reymen.scripts",
    "reymen.cli": "src.reymen.cli",
    "reymen.reymen_cli": "src.reymen.cli",
    "reymen.bin": "src.reymen.bin",
    "reymen.tools": "src.reymen.tools",
    "reymen.mcp": "src.reymen.mcp",
    "reymen.web_ui": "src.reymen.web_ui",
    "reymen.desktop": "src.reymen.desktop",
    "reymen.windows": "src.reymen.windows",
    "reymen.memory": "src.reymen.memory",
    "reymen.cron": "src.reymen.cron",
    "reymen.cron_data": "src.reymen.cron_data",
    "reymen.altin_kayitlar": "src.reymen.altin_kayitlar",
    "reymen.gecmis_konusmalar": "src.reymen.gecmis_konusmalar",
    "reymen.merkez_db": "src.reymen.merkez_db",
    "reymen.ses_orneklem": "src.reymen.ses_orneklem",
    "reymen.video_cache": "src.reymen.video_cache",
    "reymen.logs": "src.reymen.logs",
    "reymen.ag": "src.gateways",
    "reymen.gateway": "src.gateways",
    "reymen.telegram_bot": "src.gateways.telegram_bot",
    "reymen.core": "src.core",
    "reymen.test": "tests",
    "reymen.api_server": "src.reymen.api_server",
}

# Kok dizindeki reymen/__init__.py gibi dosyalar
KOK_SRC_REYMEN = [
    "__init__.py", "__main__.py", "api_server.py",
    "a2a.py", "a2a_distributed.py", "a2a_integration.py",
    "a2a_transport.py", "cost_tracker.py",
    "kanban.py", "platform_adapter.py",
    "self_improve.py", "tui.py", "video_tools.py",
    "web_search_provider.py", "web_search_registry.py",
    "web_ui.py", "console.py",
    "disk_izleme.py", "dusuk_oncelik_cli.py",
    "merkez_db_bakim.py", "old_temizle.py",
]


def import_guncelle(icerik: str) -> str:
    """Import satirlarini guncelle."""
    # from reymen.X → from src.reymen.X veya src.gateways.X vs
    for eski, yeni in IMPORT_MAP.items():
        # from reymen.X.Y
        icerik = re.sub(
            rf'^from\s+{re.escape(eski)}(\.?\w*)',
            lambda m: f'from {yeni}{m.group(1)}',
            icerik,
            flags=re.MULTILINE
        )
        # import reymen.X
        icerik = re.sub(
            rf'^import\s+{re.escape(eski)}(\.?\w*)',
            lambda m: f'import {yeni}{m.group(1)}',
            icerik,
            flags=re.MULTILINE
        )
    return icerik


def dizin_tasi(kaynak: Path, hedef: Path):
    """Dizini kopyala ve import'lari guncelle."""
    if not kaynak.exists():
        return 0
    
    hedef.mkdir(parents=True, exist_ok=True)
    sayac = 0
    
    for dosya in kaynak.rglob("*.py"):
        if "__pycache__" in str(dosya) or "*,cover" in str(dosya):
            continue
        
        # Hedef yolu hesapla (goreceli yolu koru)
        rel_path = dosya.relative_to(kaynak)
        hedef_dosya = hedef / rel_path
        hedef_dosya.parent.mkdir(parents=True, exist_ok=True)
        
        # Icerigi oku ve import'lari guncelle
        try:
            icerik = dosya.read_text(encoding="utf-8", errors="ignore")
            yeni_icerik = import_guncelle(icerik)
            hedef_dosya.write_text(yeni_icerik, encoding="utf-8")
            sayac += 1
        except Exception as e:
            print(f"  HATA: {dosya}: {e}")
    
    return sayac


def main():
    print("=" * 60)
    print("ReYMeN Refactor — src/ yapisina tasima")
    print("=" * 60)
    
    # 1. src/ dizinini olustur
    print("\n1. Dizin yapisi olusturuluyor...")
    for hedef in set(DIZIN_MAP.values()):
        hedef.mkdir(parents=True, exist_ok=True)
    SRC_REYMEN.mkdir(parents=True, exist_ok=True)
    EXAMPLES.mkdir(exist_ok=True)
    TESTS.mkdir(exist_ok=True)
    
    # 2. reymen/ kokundeki .py dosyalarini src/reymen/ altina tasi
    print("\n2. Kok .py dosyalari tasiniyor...")
    for dosya_adi in KOK_SRC_REYMEN:
        kaynak = REYMEN_ESKI / dosya_adi
        if kaynak.exists():
            hedef = SRC_REYMEN / dosya_adi
            icerik = kaynak.read_text(encoding="utf-8", errors="ignore")
            yeni_icerik = import_guncelle(icerik)
            hedef.write_text(yeni_icerik, encoding="utf-8")
    
    # 3. Alt dizinleri tasi
    print("\n3. Alt dizinler tasiniyor...")
    toplam = 0
    for eski_ad, hedef in DIZIN_MAP.items():
        kaynak = REYMEN_ESKI / eski_ad
        adet = dizin_tasi(kaynak, hedef)
        if adet > 0:
            print(f"  {eski_ad}/ → {hedef.relative_to(PROJE)}/ ({adet} dosya)")
            toplam += adet
    print(f"  Toplam: {toplam} dosya tasindi")
    
    # 4. examples/ olustur
    print("\n4. Ornek senaryolar...")
    # ornekler sonra eklenecek
    
    # 5. degisiklikleri goster
    print("\n" + "=" * 60)
    print("✅ Refactor tamam. Yeni yapi:")
    print(f"  src/reymen/  — Framework cekirdegi ({toplam} dosya)")
    print(f"  src/gateways/ — Platform entegrasyonlari")
    print(f"  src/core/    — Reasoning Core, Ornith")
    print(f"  examples/   — Kullanim senaryolari")
    print(f"  tests/      — Test dosyalari")
    print("=" * 60)
    print("\nNOT: Eski reymen/ dizini hala duruyor.")
    print("Her sey calisiyorsa 'rm -rf reymen' ile silebilirsin.")
    print("Ayrica config.yaml, .env ve script'lerdeki yollari guncellemeyi unutma.")
    print("pyproject.toml'da packages = ['src.reymen', 'src.gateways', 'src.core']")


if __name__ == "__main__":
    main()
