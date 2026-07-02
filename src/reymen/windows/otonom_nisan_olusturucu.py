# -*- coding: utf-8 -*-
"""
otonom_nisan_olusturucu.py — DOM uzerinden tam otonom sablon cikarma araci.

Insan etkilesimi gerektirmez. Tor Browser acilir, belirtilen URL'ye gidilir,
XPATH ile hedef elementler bulunur, element screenshot'i .png olarak kaydedilir.

Kullanim:
    python otonom_nisan_olusturucu.py
    -> .ReYMeN/nisanlar/ klasorune sablonlari kaydeder

Degisiklik (nisan_yakala.py yerine):
    - Manuel fare/isim girisi yok
    - DOM'dan direk element screenshot'i
    - Case-insensitive XPath ile bulma
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

PROJE_KOKU = Path(__file__).parent.resolve()
NISAN_DIZINI = PROJE_KOKU / ".ReYMeN" / "nisanlar"

# Selenium (opsiyonel)
try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    _SELENIUM_VAR = True
except ImportError:
    _SELENIUM_VAR = False


# Varsayilan XPath hedefleri (case-insensitive)
_SABLON_HEDEFLERI: Dict[str, str] = {
    "giris_buton": (
        "//button[contains(translate(text(), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'giri') "
        "or contains(translate(text(), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login')]"
    ),
    "kayit_buton": (
        "//button[contains(translate(text(), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'kay') "
        "or contains(translate(text(), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'register')]"
    ),
    "captcha_kutu": (
        "//div[contains(@class, 'captcha') or contains(@id, 'captcha')]"
        " | //iframe[contains(@src, 'recaptcha') or contains(@src, 'captcha')]"
    ),
    "onay_kutusu": "//input[@type='checkbox']",
    "ad_alani": (
        "//input[@name='ad' or @name='firstname' or @name='first_name' "
        "or @name='name' or @id='ad']"
    ),
    "soyad_alani": (
        "//input[@name='soyad' or @name='lastname' "
        "or @name='last_name' or @name='surname']"
    ),
    "eposta_alani": (
        "//input[@type='email' or @name='email' "
        "or @name='e-posta' or @name='eposta']"
    ),
    "sifre_alani": "//input[@type='password']",
    "siparis_buton": (
        "//button[contains(translate(text(), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sat') "
        "or contains(translate(text(), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'order')"
        " or contains(translate(text(), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'buy')]"
    ),
    "telefon_alani": (
        "//input[@type='tel' or @name='phone' "
        "or @name='telefon' or @name='mobile']"
    ),
}


def otonom_sablon_olustur(hedef_url: str,
                          hedefler: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Tor uzerinden hedef siteye baglan, elementleri bul, screenshot al.

    Args:
        hedef_url: Hedef web sitesi URL'si.
        hedefler: {dosya_adi: xpath} sozlugu. None = varsayilanlar.

    Returns:
        {"basarili": [dosya_adi, ...], "basarisiz": [dosya_adi, ...], "hata": str}
    """
    sonuc: Dict[str, str] = {"basarili": [], "basarisiz": [], "hata": ""}

    if not _SELENIUM_VAR:
        return {"basarili": [], "basarisiz": list((hedefler or _SABLON_HEDEFLERI).keys()),
                "hata": "Selenium yuklu degil"}

    hedefler = hedefler or _SABLON_HEDEFLERI
    NISAN_DIZINI.mkdir(parents=True, exist_ok=True)

    try:
        from reymen.windows.tor_otomasyonu import TorBrowserKontrol
        tor = TorBrowserKontrol()
        tor.baslat()
    except Exception as e:
        return {"basarili": [], "basarisiz": list(hedefler.keys()),
                "hata": f"Tor baslatilamadi: {e}"}

    try:
        tor.driver.get(hedef_url)
        logger.info("[Nisan] Sayfa yukleniyor: %s", hedef_url)
        time.sleep(15)  # Tor + sayfa yuklemesi

        for dosya_adi, xpath in hedefler.items():
            try:
                element = WebDriverWait(tor.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                # Elementi gorunur alana kaydir
                tor.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", element
                )
                time.sleep(1)

                kayit_yolu = NISAN_DIZINI / f"{dosya_adi}.png"
                element.screenshot(str(kayit_yolu))
                sonuc["basarili"].append(dosya_adi)
                logger.info("[Nisan] Kaydedildi: %s", kayit_yolu)

            except Exception as e:
                sonuc["basarisiz"].append(dosya_adi)
                logger.warning("[Nisan] Bulunamadi: %s (%s)", dosya_adi, e)

    except Exception as e:
        sonuc["hata"] = str(e)
        logger.error("[Nisan] Sayfa hatasi: %s", e)
    finally:
        tor.kapat()

    return sonuc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    print("=" * 50)
    print("[SISTEM] Otonom Nisan Olusturucu")
    print("=" * 50)
    print(f"Hedef dizin: {NISAN_DIZINI}")
    print(f"Hedef sayisi: {len(_SABLON_HEDEFLERI)}")
    print()

    # HEDEF URL'YI BURAYA GIR
    HEDEF_SITE = input("[?] Hedef site URL'si (ornek: https://site.com): ").strip()
    if not HEDEF_SITE:
        HEDEF_SITE = "https://example.com"
        print("[!] Varsayilan URL kullaniliyor.")

    print(f"\n[SISTEM] {HEDEF_SITE} taranıyor...")
    sonuc = otonom_sablon_olustur(HEDEF_SITE)

    print(f"\n=== RAPOR ===")
    print(f"Basarili: {sonuc['basarili']}")
    print(f"Basarisiz: {sonuc['basarisiz']}")
    if sonuc['hata']:
        print(f"Hata: {sonuc['hata']}")
    print(f"\nToplam: {len(sonuc['basarili'])} kaydedildi, "
          f"{len(sonuc['basarisiz'])} bulunamadi")
