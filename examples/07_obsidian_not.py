#!/usr/bin/env python3
"""Ornek 7: Obsidian Not Okuma/Yazma — vault'ta notlari yonet."""

try:
    from reymen.tools.obsidian_tool import (
        _md_dosyalari_listele,
        _not_olustur,
        _md_oku,
        _vault_yolu_bul,
    )

    # 1. Vault yolunu bul
    basarili, vault_yolu = _vault_yolu_bul()
    if not basarili:
        print(f"Uyari: Obsidian vault bulunamadi. Sadece API gosterimi yapiliyor.\n")
        print("Obsidian Tool API:")
        print("  _md_dosyalari_listele(vault_yolu, alt_dizin='')")
        print("  _not_olustur(vault_yolu, dosya_yolu, icerik)")
        print("  _md_oku(vault_yolu, dosya_yolu)")
        print("  _vault_ara(vault_yolu, sorgu)")
        print()
        print("Kullanim icin ayarlari yapin:")
        print("  - config.yaml > obsidian.vault_path")
        print("  - veya vault yolunu parametre olarak verin")
    else:
        print(f"✅ Vault bulundu: {vault_yolu}")

        # 2. Notlari listele
        dosyalar = _md_dosyalari_listele(vault_yolu)
        print(f"\nVault'ta {len(dosyalar)} .md dosyasi var:")
        for d in dosyalar[:10]:
            print(f"  📄 {d['yol']} ({d['boyut']}B)")

        # 3. Yeni not olustur (guvenlik: gercekten yazmaz)
        test_not_yolu = "_reymen_test_notu.md"
        print(f"\nOrnek: '{test_not_yolu}' olusturuluyor...")
        basarili2, mesaj = _not_olustur(
            vault_yolu,
            test_not_yolu,
            icerik="# ReYMeN Test Notu\n\nBu not ReYMeN tarafindan olusturulmustur.",
        )
        print(f"  {'✅' if basarili2 else 'ℹ️'}  {mesaj}")

        # 4. Notu oku
        basarili3, icerik = _md_oku(vault_yolu, test_not_yolu)
        if basarili3:
            print(f"\nNot icerigi:\n{icerik[:200]}...")
        else:
            print(f"  ℹ️  {icerik}")

        # 5. Temizlik (test notunu sil)
        import os
        try:
            os.remove(os.path.join(vault_yolu, test_not_yolu))
            print(f"\n🧹 Test notu temizlendi.")
        except Exception:
            pass

except ImportError as e:
    print(f"[ATLA] Modul bulunamadi: {e}")
except Exception as e:
    print(f"[HATA] {type(e).__name__}: {e}")
