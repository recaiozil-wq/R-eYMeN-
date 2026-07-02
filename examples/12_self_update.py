#!/usr/bin/env python3
"""Ornek 12: Kendi Kendini Guncelleme — GitHub release kontrolu ve update."""

try:
    from reymen.sistem.self_update import (
        check_for_updates,
        _mevcut_versiyon,
        _versiyon_karsilastir,
        _git_remote_parse,
        auto_update_check,
    )
    from pathlib import Path
    import os

    print("=== ReYMeN Self-Update Sistemi ===\n")

    # 1. Mevcut versiyonu goster
    versiyon = _mevcut_versiyon()
    print(f"1. Mevcut surum: v{versiyon}")

    # 2. Git remote bilgisini goster
    owner, repo = _git_remote_parse()
    print(f"2. GitHub: {owner}/{repo}")

    # 3. Versiyon karsilastirma testi
    print(f"\n3. Versiyon Karsilastirma Testleri:")
    testler = [
        ("2026.07.01", "2026.07.02", "yeni surum var"),
        ("2026.07.02", "2026.07.01", "ayni veya eski"),
        ("2026.07.01", "2026.07.01", "esit"),
        ("1.0.0", "2.0.0", "yeni surum var"),
    ]
    for v1, v2, beklenti in testler:
        karsilastirma = _versiyon_karsilastir(v1, v2)
        if karsilastirma < 0:
            durum = f"v{v1} < v{v2} -> {beklenti}"
        elif karsilastirma == 0:
            durum = f"v{v1} == v{v2} -> esit"
        else:
            durum = f"v{v1} > v{v2} -> {beklenti}"
        print(f"   {durum}")

    # 4. GitHub'dan guncelleme kontrolu (gercek API cagrisi)
    print(f"\n4. GitHub Guncelleme Kontrolu (API cagrisi):")
    print(f"   Baglaniyor: https://api.github.com/repos/{owner}/{repo}/releases/latest")
    print(f"   (Bu islem internet baglantisi gerektirir)")

    # Zaman asimi kisa tut, hata durumunda sorunsuz gec
    import socket
    socket.setdefaulttimeout(5)

    try:
        kontrol = check_for_updates()
        if kontrol.get("basarili"):
            if kontrol.get("guncel_var"):
                print(f"   ✅ Yeni surum mevcut!")
                print(f"   Mevcut: v{kontrol['mevcut_versiyon']}")
                print(f"   Yeni:   {kontrol['son_tag']}")
                print(f"   URL:    {kontrol.get('release_url', 'N/A')}")
                if kontrol.get("release_body"):
                    print(f"   Notlar: {kontrol['release_body'][:200]}...")
            else:
                print(f"   ✅ En son surum kullaniliyor: v{kontrol['mevcut_versiyon']}")
        else:
            print(f"   ℹ️  Kontrol yapilamadi: {kontrol.get('hata', 'Bilinmeyen')}")
    except Exception as e:
        print(f"   ℹ️  API cagrisi basarisiz: {e}")
        print(f"   (Internet baglantisi olmayabilir veya API limiti asilmis olabilir)")

    # 5. Otomatik guncelleme
    print(f"\n5. Otomatik Guncelleme (auto_update_check):")
    try:
        otomatik = auto_update_check(force=True)
        if otomatik.get("atlandi"):
            print(f"   ℹ️  Atlandi: {otomatik.get('aciklama', '')}")
        elif otomatik.get("basarili"):
            if otomatik.get("guncel_var"):
                print(f"   ✅ Guncelleme bulundu ve uygulandi")
                guncel = otomatik.get("guncelleme", {})
                print(f"   Once: v{guncel.get('once', '?')} -> Sonra: v{guncel.get('sonra', '?')}")
            else:
                print(f"   ✅ Guncel: {otomatik.get('aciklama', '')}")
        else:
            print(f"   ℹ️  {'Atlandi: ' + otomatik.get('aciklama', '') if otomatik.get('aciklama') else 'Kontrol yapilamadi'}")
    except Exception as e:
        print(f"   ℹ️  Otomatik guncelleme kontrolu: {e}")

    print(f"\nNot: Gercek guncelleme icin:")
    print("  perform_update()  # git pull + pip install -e .")
    print("  auto_update_baslat()  # arkaplanda haftalik kontrol")

except ImportError as e:
    print(f"[ATLA] Modul bulunamadi: {e}")
except Exception as e:
    print(f"[HATA] {type(e).__name__}: {e}")
