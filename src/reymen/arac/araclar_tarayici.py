# -*- coding: utf-8 -*-
"""
araclar_tarayici.py — Tarayıcı otomasyonu (Playwright).
Site açar, metin çeker, tıklar, yazı yazar.

KURULUM (bir kerelik):
    pip install playwright
    playwright install chromium

Playwright yoksa import hata vermez; araç "kurulu değil" der.
"""
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except Exception:
    PLAYWRIGHT_OK = False


class TarayiciKontrol:
    def __init__(self, headless=True):
        self.headless = headless

    def sayfa_ac_ve_oku(self, url, secici=None):
        """Bir URL açar; secici verilirse o elementin, yoksa tüm sayfanın metnini döndürür."""
        if not PLAYWRIGHT_OK:
            return "[Tarayıcı]: Playwright kurulu değil (pip install playwright && playwright install chromium)."
        try:
            with sync_playwright() as p:
                tarayici = p.chromium.launch(headless=self.headless)
                sayfa = tarayici.new_page()
                sayfa.goto(url, timeout=30000)
                if secici:
                    metin = sayfa.inner_text(secici)
                else:
                    metin = sayfa.inner_text("body")
                tarayici.close()
                return f"[Sayfa İçeriği]:\n{metin[:2000]}"
        except Exception as e:
            return f"[Tarayıcı Hatası]: {e}"

    def tikla_ve_yaz(self, url, tiklanacak_secici=None, yazi_secici=None, yazi=None):
        """Sayfayı açar; opsiyonel olarak bir elemana tıklar ve/veya bir alana yazı yazar."""
        if not PLAYWRIGHT_OK:
            return "[Tarayıcı]: Playwright kurulu değil."
        try:
            with sync_playwright() as p:
                tarayici = p.chromium.launch(headless=self.headless)
                sayfa = tarayici.new_page()
                sayfa.goto(url, timeout=30000)
                if yazi_secici and yazi:
                    sayfa.fill(yazi_secici, yazi)
                if tiklanacak_secici:
                    sayfa.click(tiklanacak_secici)
                sonuc = sayfa.inner_text("body")[:1500]
                tarayici.close()
                return f"[Tarayıcı Eylem Sonucu]:\n{sonuc}"
        except Exception as e:
            return f"[Tarayıcı Hatası]: {e}"


def motor_kaydet(motor):
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    motor._plugin_arac_kaydet(
        "TARAYICI_AC",
        lambda url="", secici="": TarayiciKontrol().sayfa_ac_ve_oku(url, secici or None),
        "URL'yi tarayıcıda aç ve metin döndür (url, secici: CSS seçici opsiyonel)",
    )
    motor._plugin_arac_kaydet(
        "TARAYICI_TIKLA",
        lambda url="", tikla_secici="", yazi_secici="", yazi="": TarayiciKontrol().tikla_ve_yaz(
            url, tikla_secici or None, yazi_secici or None, yazi or None
        ),
        "Sayfayı aç, elemente tıkla/yaz (url, tikla_secici, yazi_secici, yazi)",
    )


if __name__ == "__main__":
    t = TarayiciKontrol()
    print("TarayiciKontrol hazir (playwright:%s)" % PLAYWRIGHT_OK)
