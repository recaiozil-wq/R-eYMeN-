#!/usr/bin/env python3
"""Ornek 6: HyperFrames Video Olusturma — metin animasyonu, grafik, gecis."""

try:
    from reymen.tools.hyperframes_tool import (
        hyperframes_hizli_metin,
        hyperframes_hizli_grafik,
        hyperframes_hizli_gecis,
    )

    # 1. Metin animasyonu (fade-in efektiyle)
    print("1/3: Metin animasyonu olusturuluyor...")
    sonuc = hyperframes_hizli_metin(
        metin="Merhaba ReYMeN!",
        alt_metin="HyperFrames ile video",
        efekt="scale",
        sure=4.0,
        arkaplan="#1a1a2e",
        yazi_rengi="#e94560",
    )
    if sonuc["basarili"]:
        print(f"  ✅ Video: {sonuc['cikti']} ({sonuc['frame_sayisi']} frame)")
    else:
        print(f"  ❌ Hata: {sonuc['hata']}")

    # 2. Grafik animasyonu
    print("\n2/3: Grafik animasyonu olusturuluyor...")
    veri = [
        {"etiket": "Ocak", "deger": 85},
        {"etiket": "Subat", "deger": 62},
        {"etiket": "Mart", "deger": 93},
        {"etiket": "Nisan", "deger": 48},
        {"etiket": "Mayis", "deger": 76},
    ]
    sonuc2 = hyperframes_hizli_grafik(
        baslik="Aylik Performans",
        veri=veri,
        grafik_tipi="bar",
        sure=5.0,
    )
    if sonuc2["basarili"]:
        print(f"  ✅ Video: {sonuc2['cikti']} ({sonuc2['frame_sayisi']} frame)")
    else:
        print(f"  ❌ Hata: {sonuc2['hata']}")

    # 3. Gecis efekti
    print("\n3/3: Gecis efekti olusturuluyor...")
    sonuc3 = hyperframes_hizli_gecis(
        onceki_metin="Onceki Konu",
        sonraki_metin="Yeni Konu",
        gecis_tipi="slide-left",
        sure=3.0,
    )
    if sonuc3["basarili"]:
        print(f"  ✅ Video: {sonuc3['cikti']} ({sonuc3['frame_sayisi']} frame)")
    else:
        print(f"  ❌ Hata: {sonuc3['hata']}")

    print("\nNot: Videolar icin Playwright (chromium) ve FFmpeg gerekir.")
    print("Kurulum: playwright install chromium && ffmpeg")

except ImportError as e:
    print(f"[ATLA] Modul bulunamadi: {e}")
except Exception as e:
    print(f"[HATA] {type(e).__name__}: {e}")
