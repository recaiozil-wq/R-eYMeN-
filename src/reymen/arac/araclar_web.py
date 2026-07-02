# -*- coding: utf-8 -*-
"""
araclar_web.py — Web arama + sayfa icerik cekme (cok kaynakli, dayanikli).

Web arama: SearchDispatcher'a yönlendirir (reymen.arac.web_search_engine).
Sayfa icerik cekme: Playwright > urllib fallback.

API anahtari gerekmez (DuckDuckGo fallback her zaman calisir).
"""
import html
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from src.reymen.arac.web_search_engine import _get_registry as _get_dispatcher

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
_HEADERS = {"User-Agent": _UA}


def _temizle(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def _http_get(url: str, params: dict = None, headers: dict = None,
              timeout: int = 15) -> str:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={**_HEADERS, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        charset = r.headers.get_content_charset("utf-8") or "utf-8"
        return r.read().decode(charset, errors="replace")


# ── Ana arama fonksiyonu (SearchDispatcher'a yönlendirir) ─────────────────

def web_ara(sorgu: str, adet: int = 5) -> str:
    """Internette arar. SearchDispatcher'a yönlendirir (auto-detect)."""
    dispatcher = _get_dispatcher()
    return dispatcher.ara(sorgu, engine="auto", max_sonuc=adet)


# ── Sayfa icerik cekme ────────────────────────────────────────────────────

def web_icerik_al(url: str, max_karakter: int = 3000) -> str:
    """Bir URL'nin metin icerigini cekin. Playwright > urllib fallback."""
    # Playwright dene
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True, args=["--no-sandbox"])
            p = b.new_page()
            p.goto(url, timeout=20000, wait_until="domcontentloaded")
            baslik = p.title()
            metin = p.inner_text("body")[:max_karakter]
            b.close()
        return f"[Sayfa] {baslik}\nURL: {url}\n\n{metin}"
    except Exception as e:
        print(f"[UYARI] araclar_web.py Playwright hatasi: {e}")

    # urllib fallback
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            charset = r.headers.get_content_charset("utf-8") or "utf-8"
            icerik = r.read().decode(charset, errors="replace")

        class _P(HTMLParser):
            def __init__(self):
                super().__init__()
                self._t = []
                self._atla = False
            def handle_starttag(self, t, _):
                if t in ("script", "style", "nav", "footer"):
                    self._atla = True
            def handle_endtag(self, t):
                if t in ("script", "style", "nav", "footer"):
                    self._atla = False
            def handle_data(self, d):
                if not self._atla and d.strip():
                    self._t.append(d.strip())

        p = _P()
        p.feed(icerik)
        metin = " ".join(p._t)[:max_karakter]
        return f"[Sayfa:urllib] URL: {url}\n\n{metin}"
    except Exception as e:
        return f"[Web] Icerik alinamadi: {e}"


# ── Motor kayit ───────────────────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    try:
        motor._plugin_arac_kaydet(
            "WEB_ARA",
            lambda ham="": web_ara(
                re.findall(r'"((?:[^"\\]|\\.)*)"', ham)[0]
                if re.findall(r'"((?:[^"\\]|\\.)*)"', ham) else ham.strip('"')
            ),
            "Web aramasi yapar (coklu back-end, auto-detect). "
            "Kullanim: WEB_ARA(\"sorgu\")",
        )
        motor._plugin_arac_kaydet(
            "WEB_ICERIK",
            lambda ham="": web_icerik_al(
                re.findall(r'"((?:[^"\\]|\\.)*)"', ham)[0]
                if re.findall(r'"((?:[^"\\]|\\.)*)"', ham) else ham.strip('"')
            ),
            "Bir URL'nin metin icerigini al",
        )
    except Exception as e:
        print(f"[WebArama] Motor kayit hatasi: {e}")


if __name__ == "__main__":
    import sys
    sorgu = sys.argv[1] if len(sys.argv) > 1 else "python asyncio nedir"
    print(web_ara(sorgu, adet=3))
