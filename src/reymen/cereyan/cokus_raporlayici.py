# -*- coding: utf-8 -*-
"""
cokus_raporlayici.py — Otonom Sistem Cokus Raporlayicisi.

Ne yapar:
  Otonom cozum sinirlari tukendiginde devreye girer, insan-okunabilir
  bir "cokus raporu" (crash report) uretir ve gorevi kullaniciya devreder.

Kullanim (main.py / motor.py icinde):
    from cokus_raporlayici import cokus_raporu_uret
    rapor = cokus_raporu_uret(
        gorev="Web'den veri cek",
        deneme_sayisi=10,
        hata_gecmisi=[...],
        denenen_ajanlar=["genel_cozucu", "kod_uzmani"],
        tiklanma_nedeni="API rate limit asildi"
    )
    # rapor dosyaya yazilir ve string olarak doner
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).parent.resolve()
RAPOR_DIZINI = ROOT / ".ReYMeN" / "cokus_raporlari"


def cokus_raporu_uret(
    gorev: str,
    deneme_sayisi: int,
    hata_gecmisi: List[str],
    denenen_ajanlar: List[str],
    tiklanma_nedeni: Optional[str] = None,
) -> str:
    """Insan-okunabilir cokus raporu olustur ve diske kaydet.

    Args:
        gorev: Basarisiz olan gorev tanimi
        deneme_sayisi: Toplam denenen tur sayisi
        hata_gecmisi: Kronolojik hata mesajlari listesi
        denenen_ajanlar: Denenen ajan ID'leri
        tiklanma_nedeni: Son tiklanma nedeni (None = otomatik cikar)

    Returns:
        Rapor metni (dosyaya da yazilir)
    """
    RAPOR_DIZINI.mkdir(parents=True, exist_ok=True)

    # Zaman damgasi
    tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dosya_adi = f"cokus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    dosya_yolu = RAPOR_DIZINI / dosya_adi

    # Son tiklanma nedenini bul
    if not tiklanma_nedeni and hata_gecmisi:
        tiklanma_nedeni = hata_gecmisi[-1]
    elif not tiklanma_nedeni:
        tiklanma_nedeni = "Belirlenemeyen sistem kesintisi."

    # Hata gecmisini formatla
    hata_metni = "\n".join(f"  [{i+1}] {log}" for i, log in enumerate(hata_gecmisi))
    if not hata_metni:
        hata_metni = "  (Hata kaydi yok)"

    # Denenen ajanlari formatla
    ajan_metni = ", ".join(sorted(set(denenen_ajanlar))) if denenen_ajanlar else "Henuz ajan secilmemisti."

    # Rapor sablonu (ReYMeN stili)
    rapor = f"""
============================================================
🚨 [OTONOM SISTEM COKUS / TAHLIYE RAPORU] 🚨
============================================================
Kritik Zaman Dilimi    : {tarih}
Basarisiz Olunan Gorev : {gorev}
Toplam Tuketilen Dongu : {deneme_sayisi} Tur

Sistem, otonom problem cozme sinirlarina ulasmis ve
kritik kilitlenme yasamistir. Donem icinde devreye alinan
tum uzman yapay zeka personalari basarisiz olmustur.

------------------------------------------------------------
🔍 [KRONOLOJIK HATA VE ADAPTASYON GECMISI]
------------------------------------------------------------
{hata_metni}

------------------------------------------------------------
🧠 [GOREV SURESINCE DENENEN AJANLAR]
------------------------------------------------------------
{ajan_metni}

------------------------------------------------------------
⚠️  [OLUMCUL KILITLENME NOKTASI (KOK NEDEN)]
------------------------------------------------------------
{tiklanma_nedeni}

============================================================
🚨 KULLANICI ACIL MUDAHALE VE GOREV DEVRİ PROTOKOLU
============================================================
Otonom dongunun tiklanma noktasi yukarida teshis edilmistir.
Sistemin kendini guncelleyerek genisleyebilmesi adina:

  1. Yukaridaki verileri inceleyin
  2. Bir COZUM ONERISI hazirlayin
  3. Cozum onerisini sisteme YENI BIR GOREV olarak iletin
  4. Ornek: "Su adimlari izle, su bagimliligi duzelt ve tekrar dene"

Iletilen bu girdi, 'Yetenek Fabrikasi' tarafindan kalici bir
sablon beceriye donusturulecek ve gelecekte benzer hatalarla
karsilasildiginda otonom olarak kullanilacaktir.
============================================================
"""
    rapor = rapor.strip()

    # Dosyaya yaz
    with open(str(dosya_yolu), "w", encoding="utf-8") as f:
        f.write(rapor)

    return rapor


if __name__ == "__main__":
    # Test
    print("=== cokus_raporlayici.py Test ===\n")

    ornek_hata = [
        "[genel_cozucu] web_scraper calistirildi -> HTTP 403 Forbidden",
        "[kod_uzmani] html_parse calistirildi -> SyntaxError: unexpected EOF",
        "[sistem_mimari] api_gateway calistirildi -> TimeoutError: 5000ms",
    ]

    rapor = cokus_raporu_uret(
        gorev="Web'den veri cekme ve veritabanina yazma",
        deneme_sayisi=10,
        hata_gecmisi=ornek_hata,
        denenen_ajanlar=["genel_cozucu", "kod_uzmani", "sistem_mimari"],
        tiklanma_nedeni="API rate limit + SSL sertifikasi uyumsuzlugu."
    )

    # Son 500 karakteri goster
    print(f"Rapor ({len(rapor)} karakter):")
    print("..." + rapor[-500:])
    print(f"\n[Test] Tamamlandi. Kayit: .ReYMeN/cokus_raporlari/")
