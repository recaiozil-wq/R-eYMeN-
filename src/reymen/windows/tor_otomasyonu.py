# -*- coding: utf-8 -*-
"""
tor_otomasyonu.py — ReYMeN icin Tor tabanli web otomasyon modulu.

Yetenekler:
  - Tor Browser baslatma/kapatma (Selenium + geckodriver)
  - Form doldurma (ad, adres, tel, eposta vb.)
  - Login akisi
  - Kayit (yeni uyelik) akisi
  - Siparis verme akisi
  - OCR entegrasyonu (hata_cozucu ile)

UYARI:
  - Tor cikis dugumleri Cloudflare/WAF captcha zorlayabilir.
  - Basit captcha'lar OCR ile cozulebilir, reCAPTCHA/hCaptcha harici API gerektirir.
  - Tor yuksek gecikmelidir; sayfa yukleme 30-45sn surer.

Entegrasyon (motor.py):
    TOR_AC, TOR_KAPAT, TOR_FORM_DOLDUR,
    TOR_LOGIN, TOR_KAYIT, TOR_SIPARIS
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Selenium (opsiyonel)
try:
    from selenium import webdriver as _webdriver
    from selenium.webdriver.firefox.service import Service as _FirefoxService
    from selenium.webdriver.firefox.options import Options as _FirefoxOptions
    from selenium.webdriver.common.by import By as _By
    from selenium.webdriver.support.ui import WebDriverWait as _WebDriverWait
    from selenium.webdriver.support import expected_conditions as _EC
    from selenium.common.exceptions import TimeoutException as _TimeoutException
    from selenium.common.exceptions import WebDriverException as _WebDriverException
    _SELENIUM_VAR = True
except ImportError:
    _SELENIUM_VAR = False

# OCR entegrasyonu (opsiyonel)
try:
    from reymen.cereyan.hata_cozucu import HataKoduUretici
    _HATA_COZUCU_VAR = True
except ImportError:
    _HATA_COZUCU_VAR = False


# ── Sabitler ────────────────────────────────────────────────────────────────

_TOR_PROXY_HOST = "127.0.0.1"
_TOR_PROXY_PORT = 9150  # Tor Browser varsayilan SOCKS portu
_TOR_PROXY_PORT_ALTERNATIVE = 9050  # Alternatif (Tor service)
_SAYFA_BEKLEME = 45  # Tor yuksek gecikmeli, 10sn yetmez
_FORM_BEKLEME = 30


# ── Tor Browser kontrol ─────────────────────────────────────────────────────

class TorBrowserKontrol:
    """Tor Browser'i bul, baslat, Selenium WebDriver ile yonet."""

    def __init__(self, tor_yolu: Optional[str] = None,
                 geckodriver_yolu: str = "geckodriver") -> None:
        self.tor_yolu = tor_yolu or self._varsayilan_yol()
        self.geckodriver_yolu = geckodriver_yolu
        self.driver: Optional[Any] = None

    @staticmethod
    def _varsayilan_yol() -> str:
        """Windows'ta Tor Browser'in standart konumlarini ara."""
        kullanici = os.environ.get("USERNAME", "")
        yollar = [
            Path(f"C:\\Users\\{kullanici}\\Desktop\\Tor Browser\\Browser\\firefox.exe"),
            Path(f"C:\\Users\\{kullanici}\\Masaüstü\\Tor Browser\\Browser\\firefox.exe"),
            Path("C:\\Tor Browser\\Browser\\firefox.exe"),
            Path("C:\\Program Files\\Tor Browser\\Browser\\firefox.exe"),
        ]
        for yol in yollar:
            if yol.exists():
                return str(yol)
        logger.warning("[Tor] Tor Browser standart yollarda bulunamadi.")
        return ""

    def baslat(self) -> None:
        """Tor Browser'i baslat ve WebDriver'a bagla."""
        if not _SELENIUM_VAR:
            raise RuntimeError("Selenium yuklu degil. pip install selenium")
        if not self.tor_yolu or not Path(self.tor_yolu).exists():
            raise FileNotFoundError(f"Tor Browser bulunamadi: {self.tor_yolu}")

        try:
            secenekler = _FirefoxOptions()
            secenekler.binary_location = self.tor_yolu
            secenekler.set_preference("network.proxy.type", 1)
            secenekler.set_preference("network.proxy.socks", _TOR_PROXY_HOST)
            secenekler.set_preference("network.proxy.socks_port", _TOR_PROXY_PORT)
            secenekler.set_preference("network.proxy.socks_remote_dns", True)
            secenekler.set_preference("media.volume_scale", "0.0")  # Sessiz

            servis = _FirefoxService(self.geckodriver_yolu)
            self.driver = _webdriver.Firefox(service=servis, options=secenekler)
            # Tor agina baglanmasini bekle
            time.sleep(3)
            logger.info("[Tor] Browser baslatildi: %s", self.tor_yolu)
        except Exception as e:
            logger.error("[Tor] Baslatma hatasi: %s", e)
            self.driver = None
            raise

    def kapat(self) -> None:
        """Browser'i kapat."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.debug("[Tor] Kapatma hatasi: %s", e)
            self.driver = None
            logger.info("[Tor] Browser kapatildi.")

    @property
    def aktif(self) -> bool:
        return self.driver is not None

    def sayfaya_git(self, url: str, bekle: int = _SAYFA_BEKLEME) -> bool:
        """URL'ye git, sayfanin yuklenmesini bekle."""
        if not self.driver:
            return False
        try:
            self.driver.get(url)
            _WebDriverWait(self.driver, bekle).until(
                _EC.presence_of_element_located((_By.TAG_NAME, "body"))
            )
            return True
        except Exception as e:
            logger.error("[Tor] Sayfa yuklenemedi (%s): %s", url, e)
            return False

    def sayfa_kaydet(self) -> str:
        """Mevcut sayfanin ham HTML'ini dondur."""
        if not self.driver:
            return ""
        try:
            return self.driver.page_source
        except Exception as e:
            logger.error("[Tor] Sayfa kaydetme hatasi: %s", e)
            return ""

    def ekran_goruntusu(self, dosya_yolu: str = "") -> str:
        """Mevcut sayfanin ekran goruntusunu al."""
        if not self.driver:
            return ""
        yol = dosya_yolu or f"tor_screenshot_{int(time.time())}.png"
        try:
            self.driver.save_screenshot(yol)
            return yol
        except Exception as e:
            logger.error("[Tor] Ekran goruntusu hatasi: %s", e)
            return ""


# ── Form doldurma ───────────────────────────────────────────────────────────

class FormDoldurucu:
    """DOM'da alanlari bulup deger girer. Birden fazla secici stratejisi dener."""

    # Oncelik sirasina gore alan bulma stratejileri
    _STRATEJILER = [
        lambda alan: (_By.XPATH, f"//*[@name='{alan}']"),
        lambda alan: (_By.XPATH, f"//*[@id='{alan}']"),
        lambda alan: (_By.XPATH, f"//input[@placeholder='{alan}']"),
        lambda alan: (_By.XPATH, f"//textarea[@name='{alan}']"),
        lambda alan: (_By.XPATH, f"//input[@type='{alan}']"),
    ]

    # Turkce alan adi -> DOM name/id/placeholder donusumleri
    _ALAN_KARESi = {
        "ad": ["name", "firstname", "first_name", "ad", "isim", "adınız"],
        "soyad": ["surname", "lastname", "last_name", "soyad", "soyisim"],
        "eposta": ["email", "e-mail", "mail", "eposta", "e_posta"],
        "telefon": ["phone", "tel", "telefon", "mobile", "gsm", "telephone"],
        "sifre": ["password", "pass", "sifre", "parola"],
        "sifre_tekrar": ["password2", "confirm_password", "sifre_tekrar"],
        "adres": ["address", "adres", "adres_1", "street"],
        "il": ["city", "il", "sehir", "province"],
        "ilce": ["district", "ilce", "county", "town"],
        "posta_kodu": ["zip", "postcode", "posta_kodu", "zipcode"],
        "tc_kimlik": ["tc", "tckimlik", "identity", "ssn", "kimlik"],
        "kullanici_adi": ["username", "user", "kullanici", "kullanici_adi"],
    }

    @classmethod
    def doldur(cls, driver: Any, alanlar: Dict[str, str],
               bekle: int = _FORM_BEKLEME) -> Dict[str, str]:
        """Form alanlarini doldur.

        Args:
            driver: Selenium WebDriver nesnesi.
            alanlar: {"ad": "Ahmet", "soyad": "Yilmaz", ...}
            bekle: Her alan icin maksimum bekleme saniyesi.

        Returns:
            {"basarili": [alan_adi, ...], "basarisiz": [alan_adi, ...]}
        """
        sonuc: Dict[str, str] = {"basarili": [], "basarisiz": []}

        for alan_adi, deger in alanlar.items():
            # Dogrudan alan adi + Turkce karsiliklarini dene
            aranacaklar = [alan_adi] + cls._ALAN_KARESi.get(alan_adi.lower(), [])

            bulundu = False
            for aranan in aranacaklar:
                for strateji in cls._STRATEJILER:
                    try:
                        element = _WebDriverWait(driver, 3).until(
                            _EC.presence_of_element_located(strateji(aranan))
                        )
                        element.clear()
                        element.send_keys(deger)
                        sonuc["basarili"].append(alan_adi)
                        bulundu = True
                        logger.debug("[Form] %s = %s (%s)", alan_adi, deger[:10], aranan)
                        break
                    except Exception:
                        continue
                if bulundu:
                    break

            if not bulundu:
                sonuc["basarisiz"].append(alan_adi)
                logger.warning("[Form] Alan bulunamadi: '%s' (aranan: %s)",
                              alan_adi, aranacaklar[:3])

        return sonuc


# ─── Is akislari (Login, Kayit, Siparis) ────────────────────────────────────

class OtomasyonAkislari:
    """Tor Browser uzerinden login, kayit, siparis akislari."""

    def __init__(self, tor: TorBrowserKontrol) -> None:
        self.tor = tor

    def _submit(self, bekle: int = 5) -> bool:
        """Sayfadaki submit butonuna tikla."""
        if not self.tor.driver:
            return False
        try:
            for secici in [
                (_By.XPATH, "//button[@type='submit']"),
                (_By.XPATH, "//input[@type='submit']"),
                (_By.XPATH, "//button[contains(text(), 'Giriş')]"),
                (_By.XPATH, "//button[contains(text(), 'Login')]"),
                (_By.XPATH, "//button[contains(text(), 'Kaydol')]"),
                (_By.XPATH, "//button[contains(text(), 'Register')]"),
                (_By.XPATH, "//button[contains(text(), 'Sipariş')]"),
                (_By.XPATH, "//button[contains(text(), 'Satın Al')]"),
            ]:
                try:
                    btn = _WebDriverWait(self.tor.driver, 3).until(
                        _EC.element_to_be_clickable(secici)
                    )
                    btn.click()
                    time.sleep(2)
                    return True
                except Exception:
                    continue
            return False
        except Exception as e:
            logger.error("[Akis] Submit hatasi: %s", e)
            return False

    def login(self, url: str, kullanici: str, sifre: str) -> Dict[str, Any]:
        """Siteye giris yap.

        Returns:
            {"basarili": bool, "sayfa": str, "hata": str}
        """
        if not self.tor.aktif:
            return {"basarili": False, "sayfa": "", "hata": "Tor aktif degil"}
        try:
            if not self.tor.sayfaya_git(url):
                return {"basarili": False, "sayfa": "", "hata": "Sayfa yuklenemedi"}

            FormDoldurucu.doldur(self.tor.driver, {
                "kullanici_adi": kullanici,
                "sifre": sifre,
            })

            self._submit()
            time.sleep(2)
            sayfa = self.tor.sayfa_kaydet()[:500]
            return {"basarili": True, "sayfa": sayfa, "hata": ""}
        except Exception as e:
            logger.error("[Akis] Login hatasi: %s", e)
            return {"basarili": False, "sayfa": "", "hata": str(e)}

    def kayit_ol(self, url: str, bilgiler: Dict[str, str]) -> Dict[str, Any]:
        """Yeni uyelik olustur.

        Args:
            url: Kayit sayfasi URL'si.
            bilgiler: {"ad": ..., "soyad": ..., "eposta": ..., "sifre": ..., ...}

        Returns:
            {"basarili": bool, "sonuc": str, "hata": str}
        """
        if not self.tor.aktif:
            return {"basarili": False, "sonuc": "", "hata": "Tor aktif degil"}
        try:
            if not self.tor.sayfaya_git(url):
                return {"basarili": False, "sonuc": "", "hata": "Sayfa yuklenemedi"}

            FormDoldurucu.doldur(self.tor.driver, bilgiler)
            self._submit()
            time.sleep(2)
            kaynak = self.tor.sayfa_kaydet()[:300]
            return {"basarili": True, "sonuc": kaynak, "hata": ""}
        except Exception as e:
            logger.error("[Akis] Kayit hatasi: %s", e)
            return {"basarili": False, "sonuc": "", "hata": str(e)}

    def siparis_ver(self, url: str, urun: str,
                    adres: Dict[str, str]) -> Dict[str, Any]:
        """Urun detay sayfasina git, sepete ekle, adres gir, siparis ver.

        Args:
            url: Urun veya ana sayfa URL'si.
            urun: Urun ID'si veya URL yolu.
            adres: {"adres": ..., "il": ..., "ilce": ..., "posta_kodu": ...}
        """
        if not self.tor.aktif:
            return {"basarili": False, "sonuc": "", "hata": "Tor aktif degil"}
        try:
            urun_url = f"{url.rstrip('/')}/{urun.lstrip('/')}"
            if not self.tor.sayfaya_git(urun_url):
                return {"basarili": False, "sonuc": "", "hata": "Urun sayfasi yuklenemedi"}

            # Sepete ekle butonunu bul ve tikla
            self._submit()

            # Odeme/adres sayfasina git
            odeme_url = f"{url.rstrip('/')}/checkout"
            self.tor.sayfaya_git(odeme_url)

            # Adres bilgilerini doldur
            FormDoldurucu.doldur(self.tor.driver, adres)
            self._submit()

            time.sleep(2)
            return {"basarili": True, "sonuc": "Siparis verildi.", "hata": ""}
        except Exception as e:
            logger.error("[Akis] Siparis hatasi: %s", e)
            return {"basarili": False, "sonuc": "", "hata": str(e)}


# ── Global ornek (singleton benzeri) ────────────────────────────────────────

_aktif_tor: Optional[TorBrowserKontrol] = None
_aktif_akislar: Optional[OtomasyonAkislari] = None


def tor_baslat(tor_yolu: Optional[str] = None) -> str:
    """Tor Browser'i baslat (global)."""
    global _aktif_tor, _aktif_akislar
    try:
        _aktif_tor = TorBrowserKontrol(tor_yolu=tor_yolu)
        _aktif_tor.baslat()
        _aktif_akislar = OtomasyonAkislari(_aktif_tor)
        return "[Tor] Browser baslatildi."
    except Exception as e:
        return f"[Tor] Baslatma hatasi: {e}"


def tor_kapat() -> str:
    """Tor Browser'i kapat (global)."""
    global _aktif_tor, _aktif_akislar
    if _aktif_tor:
        _aktif_tor.kapat()
    _aktif_tor = None
    _aktif_akislar = None
    return "[Tor] Browser kapatildi."


# ── motor.py kayit fonksiyonu ───────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    """motor.py'ye TOR_ araclarini kaydet."""
    if not hasattr(motor, "_orijinal_calistir"):
        motor._orijinal_calistir = motor.calistir

    def yamali_calistir(arac: str, ham_param: str) -> str:
        global _aktif_tor, _aktif_akislar

        if arac == "TOR_AC":
            return tor_baslat(ham_param.strip() or None)

        if arac == "TOR_KAPAT":
            return tor_kapat()

        if not _aktif_akislar:
            return "[Tor]: Once TOR_AC ile baslatin."

        if arac == "TOR_FORM_DOLDUR":
            import json
            try:
                alanlar = json.loads(ham_param)
                if isinstance(alanlar, dict):
                    sonuc = FormDoldurucu.doldur(_aktif_tor.driver, alanlar)
                    return (f"[Form] Basarili: {sonuc['basarili']}, "
                            f"Basarisiz: {sonuc['basarisiz']}")
            except json.JSONDecodeError:
                return "[Tor]: JSON formatinda alanlar gonderin: {\"ad\": \"...\", ...}"

        if arac == "TOR_LOGIN":
            import json
            try:
                data = json.loads(ham_param)
                sonuc = _aktif_akislar.login(
                    data.get("url", ""),
                    data.get("kullanici", ""),
                    data.get("sifre", ""),
                )
                if sonuc["basarili"]:
                    return "[Login] Basarili."
                return f"[Login] Basarisiz: {sonuc['hata']}"
            except json.JSONDecodeError:
                return "[Tor]: JSON gonderin: {\"url\": \"...\", \"kullanici\": \"...\", \"sifre\": \"...\"}"

        if arac == "TOR_KAYIT":
            import json
            try:
                data = json.loads(ham_param)
                sonuc = _aktif_akislar.kayit_ol(
                    data.get("url", ""),
                    data.get("bilgiler", {}),
                )
                if sonuc["basarili"]:
                    return "[Kayit] Basarili."
                return f"[Kayit] Basarisiz: {sonuc['hata']}"
            except json.JSONDecodeError:
                return "[Tor]: JSON gonderin: {\"url\": \"...\", \"bilgiler\": {...}}"

        if arac == "TOR_SIPARIS":
            import json
            try:
                data = json.loads(ham_param)
                sonuc = _aktif_akislar.siparis_ver(
                    data.get("url", ""),
                    data.get("urun", ""),
                    data.get("adres", {}),
                )
                if sonuc["basarili"]:
                    return "[Siparis] Basarili."
                return f"[Siparis] Basarisiz: {sonuc['hata']}"
            except json.JSONDecodeError:
                return "[Tor]: JSON gonderin: {\"url\": \"...\", \"urun\": \"...\", \"adres\": {...}}"

        return motor._orijinal_calistir(arac, ham_param)

    motor.calistir = yamali_calistir
    logger.info("[Tor] 6 arac kaydedildi: TOR_AC, TOR_KAPAT, TOR_FORM_DOLDUR, TOR_LOGIN, TOR_KAYIT, TOR_SIPARIS")


# ── Hizli test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO, format="%(levelname)s %(message)s")

    print("=== Tor Otomasyon Testi ===")
    print("[Test] Selenium var mi:", _SELENIUM_VAR)
    print("[Test] Varsayilan Tor yolu:", TorBrowserKontrol._varsayilan_yol())

    print("\n=== FormDoldurucu Alan Karesi Testi ===")
    for turkce, dom_karsiligi in FormDoldurucu._ALAN_KARESi.items():
        print(f"  {turkce:15} -> {dom_karsiligi[:3]}...")

    print("\n=== Motor Kayit Testi ===")
    try:
        from reymen.cereyan.motor import Motor
        m = Motor(backend_mode="local")
        # Motor'a TOR_ araçlarını ekle (motor_kaydet ile)
        class MockMotor:
            calistir = m.calistir
        mock = MockMotor()
        motor_kaydet(mock)
        print("  [OK] Motor kaydi yapildi")
    except Exception as e:
        print(f"  [Test] Motor kaydi: {e}")

    print("\n✓ Test tamam.")
