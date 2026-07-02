# -*- coding: utf-8 -*-
"""
araclar_gelismis.py — Gelismis Arac Seti.

Araçlar:
  BrowserTool      — Headless tarayici + screenshot + JS inject
  ApprovalTool     — Kullanici onay diyalogu (GUI/terminal)
  SupervisorTool   — Gorev izleme, thread saglik kontrolu, zaman asimi

motor.py'e dogrudan kayit edilebilir veya bagimsiz kullanilabilir.
"""
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent


# ═══════════════════════════════════════════════════════════════
# BROWSER TOOL — Headless Tarayici
# ═══════════════════════════════════════════════════════════════

class BrowserTool:
    """
    Playwright varsa: headless Chromium, screenshot, JS.
    Yoksa: urllib ile HTML → temiz metin fallback.

    Gelişmiş özellikler:
    - Form doldurma (fill, select_option)
    - Element bekleme (wait_for)
    - Hover, scroll, geçmiş
    - Sekme yönetimi
    - Sayfa snapshot / HTML
    - Network izleme
    - Dialog yönetimi
    """

    def __init__(self, headless: bool = True):
        self._headless = headless
        self._pw = None
        self._browser = None
        self._page = None
        self._context = None
        self._playwright_var = None
        self._tabs: list = []
        self._tab_index = 0
        self._recorder = None  # type: ignore  # WorkflowRecorder atanir

    def _playwright_yukle(self) -> bool:
        if self._playwright_var is not None:
            return self._playwright_var
        try:
            from playwright.sync_api import sync_playwright
            self._playwright_var = True
        except ImportError:
            self._playwright_var = False
        return self._playwright_var

    @staticmethod
    def _chrome_path():
        """Windows'ta Playwright headless shell yolunu bul."""
        import os
        base = os.path.expanduser("~/AppData/Local/ms-playwright")
        if not os.path.isdir(base):
            return ""
        dirs = sorted(
            [d for d in os.listdir(base) if "headless_shell" in d],
            reverse=True
        )
        if not dirs:
            return ""
        shell_dir = os.path.join(base, dirs[0])
        # Olası konumlar
        for cand in (
            os.path.join(shell_dir, "chrome-headless-shell-win64", "chrome-headless-shell.exe"),
            os.path.join(shell_dir, dirs[0].replace("_", "-"), "chrome-headless-shell.exe"),
            os.path.join(shell_dir, "chrome-headless-shell.exe"),
        ):
            if os.path.isfile(cand):
                return cand
        return ""

    def _sayfa_al(self):
        """Mevcut sayfayı döndür, kapalıysa yenisini aç.

        Birlesik versiyon — 3 katmanli fallback:
        1. Mevcut page saglikliysa -> aynisini don
        2. Context varsa -> yeni tab
        3. Hic yoksa -> yeni browser baslat
        """
        # 1. Mevcut sayfa saglik kontrolu
        if self._page:
            try:
                self._page.evaluate("1")
                return self._page
            except Exception:
                self._page = None

        # 2. Context canliysa yeni TAB
        if self._context:
            self._page = self._context.new_page()
            self._page.on("close", self._sayfa_kapandi)
            return self._page

        # 3. Hic yoksa — SADECE burada browser baslat
        if not self._pw:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            chrome_path = self._chrome_path()
            launch_args = {"headless": self._headless, "args": ["--no-sandbox"]}
            if chrome_path:
                launch_args["executable_path"] = chrome_path
            self._browser = self._pw.chromium.launch(**launch_args)
            self._context = self._browser.new_context(
                user_agent="Mozilla/5.0 ReYMeNAgent/1.0"
            )

        self._page = self._context.new_page()
        self._page.on("close", self._sayfa_kapandi)
        return self._page

    def _sayfa_kapandi(self, sayfa):
        """Sayfa kapandiginda referansi temizle."""
        import logging
        logging.getLogger("BrowserTool").warning(
            "[Browser] Sayfa kapatildi: %s", sayfa.url
        )
        if self._page is sayfa:
            self._page = None

    # ── Yardımcı: güvenli hata yönetimi ─────────────────────────────
    _MAX_RETRY = 3
    _retry_counter = 0

    def _hata_kontrol(self, selector: str = "") -> str:
        """Hata anında screenshot al + log."""
        import time, logging
        log = logging.getLogger("BrowserTool")
        ts = int(time.time())
        ss_path = f"_browser_hata_{ts}.png"
        try:
            if self._page:
                self._page.screenshot(path=ss_path, full_page=True)
        except Exception:
            ss_path = ""
        log.warning("[Browser] Hata: selector=%s screenshot=%s", selector, ss_path)
        return ss_path

    def _sayfa_saglik_kontrol(self) -> bool:
        """Sayfa hala açık mı, kapandıysa sıfırla."""
        try:
            self._sayfa_al()  # canlılık testi + otomatik yeniden açma
            self._retry_counter = 0
            return True
        except Exception:
            self._retry_counter += 1
            if self._retry_counter >= self._MAX_RETRY:
                self._retry_counter = 0
                return False
            return self._sayfa_al() is not None

    # ── Temel ──────────────────────────────────────────────────────

    def ac(self, url: str) -> str:
        if not self._playwright_yukle():
            return self._urllib_fallback(url)
        import time
        from playwright.sync_api import TimeoutError as PWTimeout
        son_hata = ""
        for deneme in range(3):
            try:
                p = self._sayfa_al()
                sure = 15000 + (deneme * 10000)  # 15s, 25s, 35s
                p.goto(url, timeout=sure, wait_until="domcontentloaded")
                baslik = p.title()
                metin = p.inner_text("body")[:2000]
                if self._recorder:
                    self._recorder.kaydet("ac", url=url)
                return f"[Browser] {baslik}\nURL: {url}\n\n{metin}"
            except PWTimeout:
                son_hata = f"Zaman asimi ({sure/1000}s), deneme {deneme+1}/3"
                self._hata_kontrol(url)
                time.sleep(1 * (deneme + 1))
                continue
            except Exception as e:
                son_hata = str(e)[:100]
                self._hata_kontrol(url)
                break
        return f"[Browser:Hata] {url} yuklenemedi: {son_hata}"

    def screenshot(self, url: str = "", cikti: str = "screenshot.png") -> str:
        if not self._playwright_yukle():
            return "[Browser] Playwright yuklu degil — screenshot alinamaz."
        try:
            p = self._sayfa_al()
            if url and self._page:
                p.goto(url, timeout=20000, wait_until="networkidle")
            p.screenshot(path=cikti, full_page=True)
            if self._recorder:
                self._recorder.kaydet("screenshot", url=url, cikti=cikti)
            return f"[Browser] Screenshot alindi: {cikti}"
        except Exception as e:
            return f"[Browser] Screenshot hatasi: {e}"

    def js_calistir(self, url: str = "", js: str = "document.title") -> str:
        if not self._playwright_yukle():
            return "[Browser] Playwright yuklu degil."
        for deneme in range(2):
            try:
                p = self._sayfa_al()
                if url:
                    p.goto(url, timeout=20000)
                sonuc = p.evaluate(js)
                return f"[Browser] JS sonucu: {sonuc}"
            except Exception as e:
                if deneme == 0:
                    import time
                    time.sleep(1)
                    continue
                # Fallback: DOM ile oku
                try:
                    p = self._sayfa_al()
                    metin = p.inner_text("body")[:2000]
                    return f"[Browser] JS hatasi: {e}\nDOM fallback: {metin[:200]}"
                except Exception:
                    return f"[Browser:Hata] JS: {e}"

    def tikla(self, secici: str) -> str:
        if not self._page:
            return "[Browser] Once ac() cagir."
        from playwright.sync_api import TimeoutError as PWTimeout
        for deneme in range(2):
            try:
                self._page.click(secici, timeout=5000)
                time.sleep(0.5)
                if self._recorder:
                    self._recorder.kaydet("tikla", secici=secici)
                return f"[Browser] Tiklandi: {secici}"
            except PWTimeout:
                try:
                    self._page.wait_for_selector(secici, state="visible", timeout=10000)
                    self._page.click(secici, timeout=5000)
                    if self._recorder:
                        self._recorder.kaydet("tikla", secici=secici)
                    return f"[Browser] Tiklandi (bekleme sonrasi): {secici}"
                except PWTimeout:
                    self._hata_kontrol(secici)
                    if deneme == 0:
                        time.sleep(2)
                        continue
                    return f"[Browser:Hata] Element 15s icinde bulunamadi: {secici}"
            except Exception as e:
                self._hata_kontrol(secici)
                return f"[Browser:Hata] Tiklama: {e}"

    def kapat(self):
        try:
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception as e:
            print(f"[UYARI] BrowserTool kapatma: {e}")
        self._page = self._tabs = None
        self._browser = self._pw = None
        self._context = None
        self._tab_index = 0

    # ── Gelişmiş ───────────────────────────────────────────────────

    def fill(self, secici: str, deger: str) -> str:
        """Form alanını doldur."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            self._page.fill(secici, deger, timeout=5000)
            if self._recorder:
                self._recorder.kaydet("fill", secici=secici, deger=deger)
            return f"[Browser] Dolduruldu: {secici} = {deger[:50]}"
        except Exception as e:
            try:
                disabled = self._page.is_disabled(secici)
                if disabled:
                    return f"[Browser:Hata] Input pasif (disabled): {secici}"
                self._page.type(secici, deger, delay=50)
                if self._recorder:
                    self._recorder.kaydet("type", secici=secici, deger=deger)
                return f"[Browser] Yazildi (type fallback): {secici} = {deger[:50]}"
            except Exception as e2:
                self._hata_kontrol(secici)
                return f"[Browser:Hata] Doldurma: {e}"

    def type_text(self, secici: str, deger: str) -> str:
        """Karakter karakter yaz (keyboard event tetikler)."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            self._page.type(secici, deger, timeout=5000)
            if self._recorder:
                self._recorder.kaydet("type", secici=secici, deger=deger)
            return f"[Browser] Yazildi: {secici} = {deger[:50]}"
        except Exception as e:
            return f"[Browser] Type hatasi: {e}"

    def select_option(self, secici: str, deger: str) -> str:
        """Dropdown'tan değer seç."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            self._page.select_option(secici, deger, timeout=5000)
            if self._recorder:
                self._recorder.kaydet("sec", secici=secici, deger=deger)
            return f"[Browser] Secildi: {secici} = {deger}"
        except Exception as e:
            try:
                secenekler = self._page.eval_on_selector_all(
                    f"{secici} option",
                    "els => els.map(e => e.value)"
                )
                return (f"[Browser:Hata] '{deger}' bulunamadi: {e}\n"
                        f"Mevcut secenekler ({len(secenekler)}): {secenekler[:20]}")
            except Exception:
                self._hata_kontrol(secici)
                return f"[Browser:Hata] Select: {e}"

    def wait_for(self, secici: str, timeout: int = 10) -> str:
        """Element sayfada görünene kadar bekle."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            self._page.wait_for_selector(secici, timeout=timeout * 1000)
            return f"[Browser] Element gorundu: {secici}"
        except Exception as e:
            return f"[Browser] Wait hatasi: {e}"

    def wait_for_text(self, metin: str, timeout: int = 10) -> str:
        """Metin sayfada görünene kadar bekle."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            self._page.wait_for_function(
                f'document.body.innerText.includes("{metin}")',
                timeout=timeout * 1000,
            )
            return f"[Browser] Metin gorundu: {metin[:50]}"
        except Exception as e:
            return f"[Browser] Wait text hatasi: {e}"

    def hover(self, secici: str) -> str:
        """Elementin üzerine gel."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        from playwright.sync_api import TimeoutError as PWTimeout
        try:
            self._page.hover(secici, timeout=5000)
            if self._recorder:
                self._recorder.kaydet("hover", secici=secici)
            return f"[Browser] Hover: {secici}"
        except PWTimeout:
            try:
                self._page.wait_for_selector(secici, state="visible", timeout=10000)
                self._page.hover(secici, timeout=5000)
                if self._recorder:
                    self._recorder.kaydet("hover", secici=secici)
                return f"[Browser] Hover (bekleme sonrasi): {secici}"
            except Exception:
                self._hata_kontrol(secici)
                return f"[Browser:Hata] Hover: element bulunamadi: {secici}"
        except Exception as e:
            self._hata_kontrol(secici)
            return f"[Browser:Hata] Hover: {e}"

    def scroll(self, dx: int = 0, dy: int = 300) -> str:
        """Sayfayı kaydır."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            self._page.evaluate(f"window.scrollBy({dx}, {dy})")
            if self._recorder:
                self._recorder.kaydet("scroll", dx=dx, dy=dy)
            return f"[Browser] Scroll: dx={dx} dy={dy}"
        except Exception as e:
            return f"[Browser] Scroll hatasi: {e}"

    def scroll_to(self, secici: str) -> str:
        """Elemente kaydır."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            self._page.evaluate(f'document.querySelector("{secici}")?.scrollIntoView()')
            time.sleep(0.3)
            return f"[Browser] Scroll to: {secici}"
        except Exception as e:
            return f"[Browser] Scroll hatasi: {e}"

    def back(self) -> str:
        """Önceki sayfaya git."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            self._page.go_back()
            if self._recorder:
                self._recorder.kaydet("back")
            return f"[Browser] Geri: {self._page.title()}"
        except Exception as e:
            return f"[Browser] Geri hatasi: {e}"

    def forward(self) -> str:
        """Sonraki sayfaya git."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            self._page.go_forward()
            if self._recorder:
                self._recorder.kaydet("forward")
            return f"[Browser] Ileri: {self._page.title()}"
        except Exception as e:
            return f"[Browser] Ileri hatasi: {e}"

    def reload(self) -> str:
        """Sayfayı yenile."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            self._page.reload()
            return f"[Browser] Yenilendi: {self._page.title()}"
        except Exception as e:
            return f"[Browser] Yenileme hatasi: {e}"

    def new_tab(self, url: str = "") -> str:
        """Yeni sekme aç."""
        if not self._playwright_yukle():
            return "[Browser] Playwright yuklu degil."
        try:
            if not self._context:
                self._sayfa_al()
            yeni = self._context.new_page() if self._context else self._page
            if url:
                yeni.goto(url, timeout=20000)
            # Kapanma olayını dinle
            def _tab_kapandi(sayfa):
                import logging
                idx = self._tabs.index(sayfa) if sayfa in self._tabs else -1
                logging.getLogger("BrowserTool").warning(
                    "[Browser] Sekme kapatildi: #%d %s", idx, sayfa.url
                )
                if idx >= 0 and idx < len(self._tabs):
                    self._tabs[idx] = None  # işaretle
            yeni.on("close", _tab_kapandi)
            self._tabs.append(yeni)
            self._page = yeni
            self._tab_index = len(self._tabs) - 1
            # Boş referansları temizle
            self._tabs = [t for t in self._tabs if t is not None]
            return f"[Browser] Yeni sekme #{self._tab_index}: {yeni.title()}"
        except Exception as e:
            return f"[Browser:Hata] Yeni sekme: {e}"

    def switch_tab(self, index: int) -> str:
        """Sekmeye geç."""
        # Önce boş referansları temizle
        self._tabs = [t for t in self._tabs if t is not None]
        if not self._tabs:
            return "[Browser] Acik sekme yok."
        if index < 0 or index >= len(self._tabs):
            return f"[Browser] Gecersiz sekme: {index} (0-{len(self._tabs)-1})"
        try:
            # Sayfanın hala açık olduğunu kontrol et
            sayfa = self._tabs[index]
            try:
                sayfa.evaluate("1")
            except Exception:
                self._tabs.pop(index)
                self._tabs = [t for t in self._tabs if t is not None]
                if not self._tabs:
                    self._page = None
                    return "[Browser] Sekme kapanmis, acik sekme yok."
                index = min(index, len(self._tabs) - 1)
                sayfa = self._tabs[index]
            self._page = sayfa
            self._tab_index = index
            return f"[Browser] Sekme #{index}: {self._page.title()}"
        except Exception as e:
            return f"[Browser:Hata] Sekme gecis: {e}"

    def close_tab(self, index: int = -1) -> str:
        """Sekmeyi kapat (varsayilan: aktif)."""
        self._tabs = [t for t in self._tabs if t is not None]
        if not self._tabs:
            return "[Browser] Acik sekme yok."
        i = index if index >= 0 else self._tab_index
        if i < 0 or i >= len(self._tabs):
            return f"[Browser] Gecersiz sekme: {i}"
        try:
            self._tabs[i].close()
            self._tabs.pop(i)
            self._tabs = [t for t in self._tabs if t is not None]
            if not self._tabs:
                self._page = None
                self._tab_index = 0
                return "[Browser] Son sekme kapatildi."
            i = min(i, len(self._tabs) - 1)
            self._page = self._tabs[i]
            self._tab_index = i
            return f"[Browser] Sekme #{i} kapatildi."
        except Exception as e:
            return f"[Browser:Hata] Sekme kapatma: {e}"

    def tabs_list(self) -> str:
        """Açık sekmeleri listele."""
        if not self._tabs:
            return "[Browser] Acik sekme yok."
        satirlar = [f"[Browser] {len(self._tabs)} sekme:"]
        for i, t in enumerate(self._tabs):
            isaret = " <" if i == self._tab_index else "  "
            try:
                satirlar.append(f"  {isaret} #{i}: {t.title()[:60]}")
            except Exception:
                satirlar.append(f"  {isaret} #{i}: [kapali]")
        return "\n".join(satirlar)

    # ── Sayfa içeriği ──────────────────────────────────────────────

    def snapshot(self, maks: int = 3000) -> str:
        """Sayfanın tüm metnini döndür."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            metin = self._page.inner_text("body")
            return f"[Browser] Sayfa ({len(metin)} char):\n{metin[:maks]}"
        except Exception as e:
            return f"[Browser] Snapshot hatasi: {e}"

    def html(self, maks: int = 3000) -> str:
        """Sayfanın HTML kaynağını döndür."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            html_icerik = self._page.content()
            return f"[Browser] HTML ({len(html_icerik)} char):\n{html_icerik[:maks]}"
        except Exception as e:
            return f"[Browser] HTML hatasi: {e}"

    def title(self) -> str:
        """Sayfa başlığını döndür."""
        if not self._page:
            return "[Browser] Sayfa acik degil."
        try:
            return f"[Browser] Baslik: {self._page.title()}"
        except Exception as e:
            return f"[Browser] Baslik hatasi: {e}"

    def url(self) -> str:
        """Mevcut URL'yi döndür."""
        if not self._page:
            return "[Browser] Sayfa acik degil."
        try:
            return f"[Browser] URL: {self._page.url}"
        except Exception as e:
            return f"[Browser] URL hatasi: {e}"

    # ── Dialog ─────────────────────────────────────────────────────

    def dialog_accept(self) -> str:
        """Dialog'u onayla (alert/confirm/prompt)."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            self._page.once("dialog", lambda d: d.accept())
            return "[Browser] Dialog onaylandi."
        except Exception as e:
            return f"[Browser] Dialog hatasi: {e}"

    def dialog_dismiss(self) -> str:
        """Dialog'u reddet."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            self._page.once("dialog", lambda d: d.dismiss())
            return "[Browser] Dialog reddedildi."
        except Exception as e:
            return f"[Browser] Dialog hatasi: {e}"

    # ── Network ─────────────────────────────────────────────────────

    def network_requests(self, limit: int = 10) -> str:
        """Son network isteklerini listele (sadece URL)."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            from playwright.sync_api import Request
            requests = []
            def _kaydet(req: Request):
                if len(requests) < limit:
                    requests.append(f"{req.method} {req.url[:120]}")
            self._page.on("request", _kaydet)
            return f"[Browser] Network dinleyici aktif (son {limit} istek)."
        except Exception as e:
            return f"[Browser] Network hatasi: {e}"

    def clear_network(self) -> str:
        """Network log'larını temizle."""
        if not self._page:
            return "[Browser] Once ac() cagir."
        try:
            self._page.remove_listener("request", lambda _: None)
            return "[Browser] Network log temizlendi."
        except Exception as e:
            return f"[Browser] Temizleme hatasi: {e}"

    # ── Devlet yönetimi ────────────────────────────────────────────

    def cookies(self) -> str:
        """Mevcut cookie'leri listele."""
        if not self._context:
            return "[Browser] Context yok."
        try:
            ciks = self._context.cookies()
            if not ciks:
                return "[Browser] Cookie yok."
            satirlar = [f"[Browser] {len(ciks)} cookie:"]
            for c in ciks[:10]:
                satirlar.append(f"  {c['name']} = {c['value'][:40]}")
            return "\n".join(satirlar)
        except Exception as e:
            return f"[Browser] Cookie hatasi: {e}"

    def clear_state(self) -> str:
        """Cookie, storage, cache temizle."""
        if not self._context:
            return "[Browser] Context yok."
        if not self._page:
            return "[Browser] Sayfa acik degil."
        try:
            self._context.clear_cookies()
            self._page.evaluate("localStorage.clear(); sessionStorage.clear();")
            return "[Browser] State temizlendi (cookie+storage)."
        except Exception as e:
            return f"[Browser] State temizleme hatasi: {e}"

    # ── Fallback ───────────────────────────────────────────────────

    def _urllib_fallback(self, url: str) -> str:
        import urllib.request
        from html.parser import HTMLParser
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                html = r.read().decode(r.headers.get_content_charset("utf-8") or "utf-8", errors="replace")
            class P(HTMLParser):
                def __init__(self):
                    super().__init__(); self._t=[]; self._s=False
                def handle_starttag(self, t, _):
                    if t in ("script","style"): self._s=True
                def handle_endtag(self, t):
                    if t in ("script","style"): self._s=False
                def handle_data(self, d):
                    if not self._s and d.strip(): self._t.append(d.strip())
            p=P(); p.feed(html)
            return "[Browser:urllib] " + " ".join(p._t)[:2000]
        except Exception as e:
            return f"[Browser] Hata: {e}"


# ═══════════════════════════════════════════════════════════════
# APPROVAL TOOL — Onay Diyalogu
# ═══════════════════════════════════════════════════════════════

class ApprovalTool:
    """
    Riskli eylemler icin kullanici onayi ister.
    GUI varsa tkinter dialog, yoksa terminal prompt.
    Zaman asiminda auto-deny.
    """

    def __init__(self, varsayilan_ret: bool = True, timeout: int = 30):
        self.varsayilan_ret = varsayilan_ret
        self.timeout = timeout

    def onay_iste(self, baslik: str, mesaj: str, eylem: str = "") -> bool:
        """True = onaylandi, False = reddedildi."""
        tam_mesaj = f"{mesaj}"
        if eylem:
            tam_mesaj += f"\nEylem: {eylem}"

        # GUI dene
        if self._gui_dene(baslik, tam_mesaj):
            return True

        # Terminal fallback — zaman asimi ile
        return self._terminal_onay(baslik, tam_mesaj)

    def _gui_dene(self, baslik: str, mesaj: str) -> bool | None:
        """tkinter mesaj kutusu — True=onay, None=GUI yok/hata."""
        try:
            import tkinter as tk
            from tkinter import messagebox
            sonuc = [None]
            def _goster():
                root = tk.Tk()
                root.withdraw()
                cevap = messagebox.askyesno(baslik, mesaj, default="no")
                sonuc[0] = cevap
                root.destroy()
            t = threading.Thread(target=_goster, daemon=True)
            t.start()
            t.join(timeout=self.timeout)
            return sonuc[0]
        except Exception:
            return None

    def _terminal_onay(self, baslik: str, mesaj: str) -> bool:
        """Terminal'de [e/H] onayi — zaman asimi = ret."""
        print(f"\n{'='*50}")
        print(f"  ONAY GEREKIYOR: {baslik}")
        print(f"  {mesaj}")
        print(f"  [{self.timeout}sn icinde cevap verilmezse ret]")
        print(f"{'='*50}")

        cevap = [None]

        def _oku():
            try:
                c = input("  Onayliyor musunuz? [e/H] > ").strip().lower()
                cevap[0] = c in ("e", "evet", "y", "yes")
            except Exception:
                cevap[0] = False

        t = threading.Thread(target=_oku, daemon=True)
        t.start()
        t.join(timeout=self.timeout)

        if cevap[0] is None:
            print(f"  [Zaman asimi] Otomatik red.")
            return False

        return bool(cevap[0])

    def motor_onay_fonksiyonu(self, arac: str, ozet: str) -> bool:
        """motor.py onay_fonksiyonu formatina uygun wrapper."""
        RISKLI_ARAÇLAR = {
            "KOMUT_CALISTIR": "Sistem komutu calistirilacak",
            "PYTHON_CALISTIR": "Python kodu calistirilacak",
            "DOSYA_YAZ": "Dosya yazilacak",
            "TARAYICI_AC": "Tarayici acilacak",
            "EKRAN_TIKLA": "Ekrana tiklanacak",
        }
        aciklama = RISKLI_ARAÇLAR.get(arac, f"{arac} calismak uzerine")
        return self.onay_iste(
            f"Onay: {arac}",
            f"{aciklama}:\n{ozet[:200]}",
            eylem=arac,
        )


# ═══════════════════════════════════════════════════════════════
# SUPERVISOR TOOL — Gorev Izleyici
# ═══════════════════════════════════════════════════════════════

class SupervisorTool:
    """
    Gorev izleyici — thread saglik kontrolu, zaman asimi, hata sayaci.
    Ana dongunun disinda bir watchdog gibi calisir.
    """

    def __init__(self, zaman_asimi: int = 300, hata_esigi: int = 5):
        self.zaman_asimi = zaman_asimi
        self.hata_esigi = hata_esigi
        self._gorevler: dict[str, dict] = {}
        self._kilit = threading.Lock()
        self._izleyici: threading.Thread | None = None
        self._calisiyor = False

    def izlemeyi_baslat(self):
        self._calisiyor = True
        self._izleyici = threading.Thread(target=self._izle, daemon=True)
        self._izleyici.start()

    def izlemeyi_durdur(self):
        self._calisiyor = False

    def gorev_kaydet(self, gorev_id: str, thread: threading.Thread, meta: dict = None):
        with self._kilit:
            self._gorevler[gorev_id] = {
                "thread": thread,
                "baslangic": time.time(),
                "hata_sayisi": 0,
                "durum": "calisiyor",
                "meta": meta or {},
            }

    def hata_bildir(self, gorev_id: str):
        with self._kilit:
            if gorev_id in self._gorevler:
                self._gorevler[gorev_id]["hata_sayisi"] += 1

    def gorev_durumu(self, gorev_id: str) -> dict:
        with self._kilit:
            return dict(self._gorevler.get(gorev_id, {}))

    def tum_gorevler(self) -> list[dict]:
        with self._kilit:
            sonuc = []
            for gid, g in self._gorevler.items():
                sure = round(time.time() - g["baslangic"], 1)
                canli = g["thread"].is_alive() if g.get("thread") else False
                sonuc.append({
                    "id": gid,
                    "sure": sure,
                    "canli": canli,
                    "hata": g["hata_sayisi"],
                    "durum": g["durum"],
                })
            return sonuc

    def _izle(self):
        while self._calisiyor:
            time.sleep(5)
            with self._kilit:
                olmus = []
                for gid, g in self._gorevler.items():
                    sure = time.time() - g["baslangic"]
                    if g.get("thread") and not g["thread"].is_alive():
                        g["durum"] = "bitti"
                        olmus.append(gid)
                    elif sure > self.zaman_asimi:
                        g["durum"] = "zaman_asimi"
                        print(f"[Supervisor] Zaman asimi: {gid} ({sure:.0f}s)")
                    elif g["hata_sayisi"] >= self.hata_esigi:
                        g["durum"] = "hata_esigi"
                        print(f"[Supervisor] Hata esigi: {gid} ({g['hata_sayisi']} hata)")

    def rapor(self) -> str:
        gorevler = self.tum_gorevler()
        if not gorevler:
            return "[Supervisor] Izlenen gorev yok."
        satirlar = [f"[Supervisor] {len(gorevler)} gorev:"]
        for g in gorevler:
            canli = "CANLI" if g["canli"] else "BITTI"
            satirlar.append(
                f"  {g['id']:20s} {canli:6s} {g['sure']:6.1f}s  "
                f"hata:{g['hata']} {g['durum']}"
            )
        return "\n".join(satirlar)


# ═══════════════════════════════════════════════════════════════
# Motor kayit fonksiyonu
# ═══════════════════════════════════════════════════════════════

_browser = BrowserTool()
_supervisor = SupervisorTool()
_supervisor.izlemeyi_baslat()


def motor_kaydet(motor, onay_tool: ApprovalTool = None):
    """motor.py'ye gelismis araclari kaydet."""
    k = lambda ad, fonk, aciklama="": motor._plugin_arac_kaydet(ad, fonk, aciklama)
    def browser_ac(ham: str) -> str:
        params = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
        return _browser.ac(params[0] if params else ham.strip('"'))

    def browser_screenshot(ham: str) -> str:
        params = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
        url = params[0] if params else ""
        dosya = params[1] if len(params) > 1 else "screenshot.png"
        return _browser.screenshot(url, dosya)

    def browser_js(ham: str) -> str:
        params = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
        url = params[0] if params else ""
        js = params[1] if len(params) > 1 else "document.title"
        return _browser.js_calistir(url, js)

    def browser_fill(ham: str) -> str:
        params = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
        if len(params) < 2:
            return '[Browser] Kullanim: BROWSER_FILL "secici" "deger"'
        return _browser.fill(params[0], params[1])

    def browser_click(ham: str) -> str:
        params = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
        return _browser.tikla(params[0] if params else ham.strip('"'))

    def browser_wait(ham: str) -> str:
        params = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
        secici = params[0] if params else ham.strip('"')
        timeout = int(params[1]) if len(params) > 1 else 10
        return _browser.wait_for(secici, timeout)

    def browser_select(ham: str) -> str:
        params = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
        if len(params) < 2:
            return '[Browser] Kullanim: BROWSER_SELECT "secici" "deger"'
        return _browser.select_option(params[0], params[1])

    def browser_snapshot(ham: str) -> str:
        return _browser.snapshot()

    def browser_html(ham: str) -> str:
        return _browser.html()

    def browser_type_text(ham: str) -> str:
        """BROWSER_TYPE_TEXT "secici" "metin": karakter karakter yaz"""
        params = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
        if len(params) < 2:
            return '[Browser] Kullanim: BROWSER_TYPE_TEXT "secici" "metin"'
        return _browser.type_text(params[0], params[1])

    def browser_tabs(ham: str) -> str:
        """BROWSER_TABS: sekmeleri listele"""
        return _browser.tabs_list()

    def browser_new_tab(ham: str) -> str:
        """BROWSER_NEW_TAB "url": yeni sekme ac"""
        params = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
        return _browser.new_tab(params[0] if params else "")

    def browser_switch_tab(ham: str) -> str:
        """BROWSER_SWITCH_TAB index: sekmeye gec"""
        try:
            idx = int(ham.strip())
            return _browser.switch_tab(idx)
        except ValueError:
            return "[Browser] Gecersiz sekme index."

    def browser_back(ham: str) -> str:
        return _browser.back()

    def browser_forward(ham: str) -> str:
        return _browser.forward()

    def browser_reload(ham: str) -> str:
        return _browser.reload()

    def browser_scroll(ham: str) -> str:
        """BROWSER_SCROLL "dy" veya BROWSER_SCROLL: 300px asagi"""
        try:
            dy = int(ham.strip())
            return _browser.scroll(dy=dy)
        except ValueError:
            return _browser.scroll(dy=300)

    def browser_hover(ham: str) -> str:
        params = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
        return _browser.hover(params[0] if params else ham.strip('"'))

    def browser_close(ham: str) -> str:
        _browser.kapat()
        return "[Browser] Kapandi."

    def browser_status(ham: str) -> str:
        if _browser._page:
            return f"[Browser] Acik: {_browser.title()}\n{_browser.url()}"
        return "[Browser] Kapali."

    # ── Workflow Recorder araclari ──────────────────────────────────
    _recorder = None
    def _recorder_al():
        nonlocal _recorder
        if _recorder is None:
            from reymen.arac.workflow_recorder import WorkflowRecorder
            _recorder = WorkflowRecorder()
        return _recorder

    def workflow_basla(ham: str) -> str:
        rec = _recorder_al()
        ad = ham.strip('"') or f"workflow_{int(time.time())}"
        _browser._recorder = rec
        return rec.basla(ad)

    def workflow_bitir(ham: str) -> str:
        rec = _recorder_al()
        sonuc = rec.bitir()
        _browser._recorder = None
        return sonuc

    def workflow_tekrarla(ham: str) -> str:
        rec = _recorder_al()
        ad = ham.strip('"')
        return rec.tekrarla(ad, _browser)

    def workflow_listele(ham: str) -> str:
        return _recorder_al().listele()

    def workflow_sil(ham: str) -> str:
        ad = ham.strip('"')
        return _recorder_al().sil(ad)

    def browser_vision(ham: str) -> str:
        """BROWSER_VISION \"soru\": sayfanin screenshot'ini al, path doner"""
        import time
        ss_dosya = f"_browser_vision_{int(time.time())}.png"
        sonuc = _browser.screenshot(cikti=ss_dosya)
        if "hata" in sonuc.lower():
            return sonuc
        soru = ham.strip('"') or "Bu sayfada ne goruyorsun?"
        return f"[Browser Vision] Screenshot: {ss_dosya}\nSoru: {soru}\nDosyayi GORUNTU_ANALIZ veya baska bir arac ile analiz edebilirsin."

    def supervisor_rapor(ham: str) -> str:
        return _supervisor.rapor()

    def onay_iste_arac(ham: str) -> str:
        params = re.findall(r'"((?:[^"\\]|\\.)*)"', ham)
        mesaj = params[0] if params else ham
        tool = onay_tool or ApprovalTool()
        sonuc = tool.onay_iste("ReYMeN Onay", mesaj)
        return f"[Onay] {'ONAYLANDI' if sonuc else 'REDDEDILDI'}"

    k("BROWSER_HEADLESS", browser_ac)
    k("BROWSER_SCREENSHOT", browser_screenshot)
    k("BROWSER_JS", browser_js)
    k("SUPERVISOR_RAPOR", supervisor_rapor)
    k("ONAY_ISTE", onay_iste_arac)

    # Gelişmiş browser
    k("BROWSER_FILL", browser_fill)
    k("BROWSER_CLICK", browser_click)
    k("BROWSER_WAIT", browser_wait)
    k("BROWSER_SELECT", browser_select)
    k("BROWSER_SNAPSHOT", browser_snapshot)
    k("BROWSER_HTML", browser_html)
    k("BROWSER_TYPE_TEXT", browser_type_text)
    k("BROWSER_VISION", browser_vision)
    k("BROWSER_TABS", browser_tabs)
    k("BROWSER_NEW_TAB", browser_new_tab)
    k("BROWSER_SWITCH_TAB", browser_switch_tab)
    k("BROWSER_BACK", browser_back)
    k("BROWSER_FORWARD", browser_forward)
    k("BROWSER_RELOAD", browser_reload)
    k("BROWSER_SCROLL", browser_scroll)
    k("BROWSER_HOVER", browser_hover)
    k("BROWSER_CLOSE", browser_close)
    k("BROWSER_STATUS", browser_status)
    k("WORKFLOW_BASLA", workflow_basla, "Is akisi kaydi baslat. Parametre: workflow_adi (bos olursa otomatik)")
    k("WORKFLOW_BITIR", workflow_bitir, "Aktif kaydi bitir ve JSON dosyasina kaydet")
    k("WORKFLOW_TEKRARLA", workflow_tekrarla, "Kayitli workflow'u tekrarla. Parametre: workflow_adi")
    k("WORKFLOW_LISTELE", workflow_listele, "Kayitli workflow'lari listele")
    k("WORKFLOW_SIL", workflow_sil, "Bir workflow'u sil. Parametre: workflow_adi")
    print("[GelismisTools] 28 arac kayit edildi.")

    # ── HyperFrames Video Generation ─────────────────────────────────
    try:
        from reymen.tools.hyperframes_tool import (
            hyperframes_olustur,
            template_listele as hf_template_listele,
            hyperframes_hizli_metin,
            hyperframes_hizli_grafik,
            hyperframes_hizli_gecis,
        )

        def hyperframes_video_arac(ham: str) -> str:
            """HYPERFRAMES_VIDEO template,param_json,cikti_yolu"""
            import json
            params = ham.strip().split(",", 2)
            template = "METIN_ANIMASYONU"
            param_dict = {}
            cikti = None
            if len(params) >= 1 and params[0].strip():
                template = params[0].strip().upper()
            if len(params) >= 2 and params[1].strip():
                try:
                    param_dict = json.loads(params[1].strip())
                except json.JSONDecodeError:
                    return f"[HyperFrames] JSON hatasi: {params[1][:100]}"
            if len(params) >= 3 and params[2].strip():
                cikti = params[2].strip()
            sonuc = hyperframes_olustur(template=template, params=param_dict, cikti=cikti)
            if sonuc["basarili"]:
                return (
                    f"[HyperFrames] Video basariyla olusturuldu!\n"
                    f"  Cikti: {sonuc['cikti']}\n"
                    f"  Frame sayisi: {sonuc['frame_sayisi']}\n"
                    f"  Template: {template}\n"
                    f"  [MEDIA:file=\"{sonuc['cikti']}\"]"
                )
            return f"[HyperFrames] Hata: {sonuc['hata']}"

        def hyperframes_template_list(ham: str) -> str:
            return hf_template_listele()

        k("HYPERFRAMES_VIDEO", hyperframes_video_arac,
          "HTML+CSS+JS animasyon videosu. Parametreler: template, param_json (JSON), cikti_yolu (ops.)")
        k("HYPERFRAMES_TEMPLATES", hyperframes_template_list,
          "Mevcut HyperFrame template'lerini listeler.")
        print("[GelismisTools] HyperFrames araclari eklendi.")
    except ImportError:
        pass  # hyperframes_tool yoksa sessiz gec
    except Exception as e:
        print(f"[GelismisTools] HyperFrames yukleme hatasi: {e}")


# ═══════════════════════════════════════════════════════════════
# FAL.AI — Görsel Oluşturma (KALDIRILDI: araclar_goruntu.py'ye tasindi)
# ═══════════════════════════════════════════════════════════════
