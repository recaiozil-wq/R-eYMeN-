#!/usr/bin/env python3
"""Ornek 11: Setup Sihirbazi — ReYMeN kurulumunu kontrol et ve yapilandir."""

try:
    from reymen.sistem.setup_wizard import (
        python_kontrol,
        git_kontrol,
        ffmpeg_kontrol,
        config_kontrol,
        soul_kontrol,
        skills_kontrol,
        api_key_yapilandir,
        kurulum_durumu_guncelle,
        kurulum_tamamlandi_mi,
    )
    from pathlib import Path
    import tempfile
    import os

    print("=== ReYMeN Setup Sihirbazi (Salt Okunur Mod) ===\n")
    print("Not: Bu ornek mevcut sistemi kontrol eder, degisiklik yapmaz.\n")

    # Gecici proje dizini olustur (test icin)
    gecici_proje = Path(tempfile.mkdtemp())

    # 1. Python kontrolu
    print("1. Python Versiyon:")
    python_ok = python_kontrol()
    print(f"   -> {'✅ Uygun' if python_ok else '❌ 3.11+ gerekli'}")

    # 2. Git kontrolu
    print("\n2. Git:")
    git_ok = git_kontrol()
    print(f"   -> {'✅ Var' if git_ok else '❌ Yok'}")

    # 3. FFmpeg kontrolu
    print("\n3. FFmpeg:")
    ffmpeg_ok = ffmpeg_kontrol()
    print(f"   -> {'✅ Var' if ffmpeg_ok else '⚠️  Yok (video icin gerekli)'}")

    # 4. config.yaml (gecici)
    print("\n4. config.yaml:")
    # Gecici config olustur
    config_path = gecici_proje / "config.yaml"
    config_path.write_text("model:\n  provider: deepseek\n  default: deepseek-v4-flash\n", encoding="utf-8")
    config_ok = config_kontrol(gecici_proje)
    print(f"   -> {'✅ Var' if config_ok else '❌ Yok'}")

    # 5. SOUL.md (gecici)
    print("\n5. SOUL.md:")
    soul_ok = soul_kontrol(gecici_proje)
    print(f"   -> {'✅ Var' if soul_ok else '❌ Yok'}")

    # 6. skills/ dizini (gecici)
    print("\n6. Skills dizini:")
    (gecici_proje / "skills").mkdir(parents=True, exist_ok=True)
    skills_ok = skills_kontrol(gecici_proje)
    print(f"   -> {'✅ Var' if skills_ok else '❌ Yok'}")

    # 7. Kurulum durumu
    print("\n7. Kurulum Durumu:")
    tamam_mi = kurulum_tamamlandi_mi(gecici_proje)
    print(f"   -> {'✅ Tamamlandi' if tamam_mi else '❌ Tamamlanmamis'}")

    # Eger tamamlanmamissa guncelle
    if not tamam_mi:
        kurulum_durumu_guncelle(gecici_proje, tamamlandi=True)
        tamam_mi2 = kurulum_tamamlandi_mi(gecici_proje)
        print(f"   -> Guncellendi: {'✅ Tamamlandi' if tamam_mi2 else '❌ Hata'}")

    # Ozet
    print(f"\n=== Ozet ===")
    print(f"  Python: {'✅' if python_ok else '❌'}")
    print(f"  Git:    {'✅' if git_ok else '❌'}")
    print(f"  FFmpeg: {'✅' if ffmpeg_ok else '⚠️'}")
    print(f"  Config: {'✅' if config_ok else '❌'}")
    print(f"  SOUL:   {'✅' if soul_ok else '❌'}")
    print(f"  Skills: {'✅' if skills_ok else '❌'}")

    import shutil
    shutil.rmtree(str(gecici_proje), ignore_errors=True)

except ImportError as e:
    print(f"[ATLA] Modul bulunamadi: {e}")
except Exception as e:
    print(f"[HATA] {type(e).__name__}: {e}")
