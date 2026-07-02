# -*- coding: utf-8 -*-
"""
araclar_nisan.py — 3 asamali hiyerarsik ekran tarayici.

Asama 1: DOM (Selenium) — find_element ile lokator bul
Asama 2: Gorsel Sablon (OpenCV) — .ReYMeN/nisanlar/ dosyalari ile eslesme
Asama 3: Metin OCR (pytesseract) — ekranda yazi ara

Kullanim:
    bulucu = NisanBulucu()
    sonuc = bulucu.bul("giris_buton", driver=tor_driver)
    # -> {"asama": 2, "x": 100, "y": 200, "guven": 0.85, "metin": "Giris Yap"}
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

NISAN_DIZINI = Path(__file__).parent / ".ReYMeN" / "nisanlar"

# OpenCV (opsiyonel)
try:
    import cv2 as _cv2
    import numpy as _np
    _OPENCV_VAR = True
except ImportError:
    _OPENCV_VAR = False

# mss (opsiyonel)
try:
    import mss as _mss
    _MSS_VAR = True
except ImportError:
    _MSS_VAR = False

# PIL (opsiyonel)
try:
    from PIL import Image as _PIL_Image, ImageGrab as _PIL_Grab
    _PIL_VAR = True
except ImportError:
    _PIL_VAR = False

# pytesseract (opsiyonel)
try:
    import pytesseract as _pytesseract
    _TESSERACT_VAR = True
except ImportError:
    _TESSERACT_VAR = False

# Varsayilan guven esigi
_GUVEN_ESIGI = 0.75  # %75


class NisanBulucu:
    """3 asamali hiyerarsik ekran hedef bulucu.

    Asama 1: DOM (Selenium WebDriver) — find_element
    Asama 2: Gorsel sablon (OpenCV template matching)
    Asama 3: Metin OCR (pytesseract)
    """

    # Bilinen sablon -> DOM lokator donusumleri
    _SABLON_DOM = {
        "giris_buton": ["//button[@type='submit']", "//input[@type='submit']",
                        "//button[contains(text(), 'Giriş')]", "//button[contains(text(), 'Login')]",
                        "//a[contains(text(), 'Giriş')]", "//a[contains(text(), 'Login')]"],
        "kayit_buton": ["//a[contains(text(), 'Kayıt')]", "//a[contains(text(), 'Register')]",
                        "//button[contains(text(), 'Kaydol')]", "//button[contains(text(), 'Register')]"],
        "captcha_kutu": ["//iframe[contains(@src, 'recaptcha')]", "//div[@class='g-recaptcha']",
                         "//div[contains(@class, 'captcha')]", "//img[contains(@src, 'captcha')]"],
        "onay_kutusu":  ["//input[@type='checkbox']", "//*[@role='checkbox']",
                         "//label[contains(text(), 'onay')]", "//label[contains(text(), 'accept')]"],
        "ad_alani":     ["//input[@name='ad']", "//input[@name='firstname']", "//input[@name='first_name']",
                         "//input[@placeholder='Ad']", "//input[@id='ad']"],
        "soyad_alani":  ["//input[@name='soyad']", "//input[@name='lastname']", "//input[@name='last_name']"],
        "eposta_alani": ["//input[@type='email']", "//input[@name='email']", "//input[@name='e-posta']"],
        "sifre_alani":  ["//input[@type='password']"],
        "adres_alani":  ["//textarea[@name='adres']", "//textarea[@name='address']",
                         "//input[@name='address']", "//input[@name='adres']"],
        "telefon_alani":["//input[@type='tel']", "//input[@name='phone']", "//input[@name='telefon']"],
    }

    def __init__(self, guven_esigi: float = _GUVEN_ESIGI) -> None:
        self.guven_esigi = guven_esigi
        NISAN_DIZINI.mkdir(parents=True, exist_ok=True)

    # ── Ana API ────────────────────────────────────────────────────────

    def bul(self, hedef: str, driver: Any = None,
            metin_alternatif: str = "") -> Dict[str, Any]:
        """3 asamali hiyerarsi ile hedefi bul.

        Args:
            hedef: Sablon adi (ornek: "giris_buton") veya dosya adi.
            driver: Selenium WebDriver (Asama 1 icin).
            metin_alternatif: Asama 3'te aranacak metin.

        Returns:
            {"asama": 1|2|3, "x": int, "y": int, "guven": float,
             "metin": str, "element": WebElement|None}
        """
        # Asama 1: DOM
        if driver and hedef in self._SABLON_DOM:
            sonuc = self._dom_ara(driver, self._SABLON_DOM[hedef])
            if sonuc:
                return sonuc

        # Asama 2: Gorsel sablon
        if _OPENCV_VAR and _MSS_VAR:
            sonuc = self._sablon_ara(hedef)
            if sonuc and sonuc["guven"] >= self.guven_esigi:
                return sonuc

        # Asama 3: Metin OCR
        if _TESSERACT_VAR and _MSS_VAR:
            aranacak = metin_alternatif or hedef
            sonuc = self._ocr_ara(aranacak)
            if sonuc:
                return sonuc

        return {"asama": 0, "x": 0, "y": 0, "guven": 0.0,
                "metin": "", "element": None, "hata": f"Hedef bulunamadi: {hedef}"}

    # ── Asama 1: DOM ──────────────────────────────────────────────────

    def _dom_ara(self, driver: Any, seciciler: List[str]) -> Optional[Dict[str, Any]]:
        """Selenium DOM'da secicileri dene, ilk bulunanin konumunu don."""
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            for secici in seciciler:
                try:
                    element = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, secici))
                    )
                    rect = element.rect
                    return {
                        "asama": 1,
                        "x": int(rect["x"] + rect["width"] / 2),
                        "y": int(rect["y"] + rect["height"] / 2),
                        "guven": 1.0,
                        "metin": element.text[:50] or secici,
                        "element": element,
                    }
                except Exception:
                    continue
        except Exception as e:
            logger.debug("[Nisan] DOM arama hatasi: %s", e)
        return None

    # ── Asama 2: Gorsel sablon (OpenCV) ───────────────────────────────

    def _sablon_ara(self, hedef: str) -> Optional[Dict[str, Any]]:
        """Ekran goruntusunu al, .ReYMeN/nisanlar/ dosyasiyla karsilastir."""
        # Sablon dosyasini bul
        sablon_yolu = self._sablon_bul(hedef)
        if not sablon_yolu:
            return None

        try:
            with _mss.mss() as sct:
                mon = sct.monitors[1]
                goruntu = sct.grab(mon)
                ekran = _np.array(goruntu)
                # MSS'den gelen BGRA -> BGR
                ekran_bgr = _cv2.cvtColor(ekran, _cv2.COLOR_BGRA2BGR)

            sablon = _cv2.imread(str(sablon_yolu), _cv2.IMREAD_COLOR)
            if sablon is None:
                logger.warning("[Nisan] Sablon okunamadi: %s", sablon_yolu)
                return None

            # Template matching
            sonuc = _cv2.matchTemplate(ekran_bgr, sablon, _cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = _cv2.minMaxLoc(sonuc)

            if max_val >= self.guven_esigi:
                h, w = sablon.shape[:2]
                merkez_x = max_loc[0] + w // 2
                merkez_y = max_loc[1] + h // 2
                logger.info("[Nisan] Sablon bulundu: %s (guven: %.2f, konum: %d,%d)",
                           sablon_yolu.name, max_val, merkez_x, merkez_y)
                return {
                    "asama": 2,
                    "x": merkez_x,
                    "y": merkez_y,
                    "guven": round(max_val, 3),
                    "metin": sablon_yolu.stem,
                    "element": None,
                }
            else:
                logger.debug("[Nisan] Sablon eslesmedi: %s (guven: %.2f < %.2f)",
                            sablon_yolu.name, max_val, self.guven_esigi)
        except Exception as e:
            logger.debug("[Nisan] Sablon arama hatasi: %s", e)
        return None

    def _sablon_bul(self, hedef: str) -> Optional[Path]:
        """Hedef adina gore .png dosyasini bul."""
        # 1. Tam dosya adi
        yol = NISAN_DIZINI / f"{hedef}.png"
        if yol.exists():
            return yol
        # 2. icinde gecen
        for f in NISAN_DIZINI.glob("*.png"):
            if hedef.lower() in f.stem.lower():
                return f
        return None

    # ── Asama 3: Metin OCR ────────────────────────────────────────────

    def _ocr_ara(self, aranan: str) -> Optional[Dict[str, Any]]:
        """Ekrani OCR ile tara, aranan metni bul, konumunu don."""
        try:
            with _mss.mss() as sct:
                mon = sct.monitors[1]
                goruntu = sct.grab(mon)
                img = _PIL_Image.frombytes("RGB", goruntu.size, goruntu.rgb)

            # pytesseract ile veri al (konum bilgisi icin)
            veri = _pytesseract.image_to_data(img, lang="tur+eng", output_type=_pytesseract.Output.DICT)

            for i, metin in enumerate(veri["text"]):
                if metin and aranan.lower() in metin.lower():
                    x = veri["left"][i] + veri["width"][i] // 2
                    y = veri["top"][i] + veri["height"][i] // 2
                    guven = veri["conf"][i] / 100.0 if veri["conf"][i] != "-1" else 0.5
                    logger.info("[Nisan] OCR bulundu: '%s' (%s) -> (%d,%d) guven=%.2f",
                               metin, aranan, x, y, guven)
                    return {
                        "asama": 3,
                        "x": x,
                        "y": y,
                        "guven": guven,
                        "metin": metin,
                        "element": None,
                    }
        except Exception as e:
            logger.debug("[Nisan] OCR arama hatasi: %s", e)
        return None


# ── motor.py entegrasyonu icin yardimci ──────────────────────────────────────

_nisan_bulucu: Optional[NisanBulucu] = None


def nisan_bul(hedef: str, driver: Any = None,
              metin_alternatif: str = "") -> Dict[str, Any]:
    """Kuresel NisanBulucu ornegini kullanarak hedef bul (motor.py icin)."""
    global _nisan_bulucu
    if _nisan_bulucu is None:
        _nisan_bulucu = NisanBulucu()
    return _nisan_bulucu.bul(hedef, driver=driver, metin_alternatif=metin_alternatif)


# ── Hizli test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    print("=== NisanBulucu Test ===")
    print(f"Nisan dizini: {NISAN_DIZINI}")
    print(f"Nisan dosyalari: {list(NISAN_DIZINI.glob('*.png'))}")

    bulucu = NisanBulucu()
    print(f"Guven esigi: {bulucu.guven_esigi}")
    print(f"OpenCV: {_OPENCV_VAR}, MSS: {_MSS_VAR}, Tesseract: {_TESSERACT_VAR}")
    print(f"Bilinen sablonlar: {list(bulucu._SABLON_DOM.keys())}")

    # Ornek: driver'siz test (Asama 1 atlanir, Asama 2/3 bagli)
    sonuc = bulucu.bul("giris_buton")
    print(f"\nTest sonucu: {sonuc}")

    print("\n✓ Test tamam.")
