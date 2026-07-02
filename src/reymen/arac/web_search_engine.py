# -*- coding: utf-8 -*-
"""
web_search_engine.py — Çok back-end'li web arama motoru (ABC tabanlı).

WebSearchEngine ABC:
  - Soyut calistir(sorgu, max_sonuc) → str

Engine'ler:
  - DuckDuckGoEngine  — duckduckgo-search kütüphanesi (öncelikli) / DDG Lite HTML (fallback)
  - GoogleEngine      — stub (GOOGLE_API_KEY gerektirir, NotImplementedError)
  - BingEngine        — stub (BING_API_KEY gerektirir, NotImplementedError)
  - FirecrawlEngine   — Firecrawl API (FIRECRAWL_API_KEY)
  - BraveSearchEngine — Brave Search API (BRAVE_API_KEY)
  - SearXNGEngine     — SearXNG örnek (SEARXNG_URL)
  - ExaEngine         — Exa API (EXA_API_KEY)

WebSearchRegistry:
  - engine kaydet / seç (ad ile) / calistir (engine adı + sorgu ile)
  - Auto-detect: env var'larına göre hangi engine'lerin hazır olduğunu belirler
  - Config backend seçimi: config'de web.backend veya web.search_backend varsa o engine kullanılır
  - Varsayılan engine: duckduckgo (her zaman çalışır)

Motor tool:
  WEB_ARAMA(sorgu, backend="duckduckgo") → str
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from html.parser import HTMLParser
from typing import Optional

import yaml
import logging
logger = logging.getLogger(__name__)

log = logging.getLogger(__name__)

# Shared HTTP helpers
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
_HEADERS = {"User-Agent": _UA}


def _http_get(url: str, params: dict = None, headers: dict = None,
              timeout: int = 15) -> str:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={**_HEADERS, **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        charset = r.headers.get_content_charset("utf-8") or "utf-8"
        return r.read().decode(charset, errors="replace")


def _http_post_json(url: str, data: dict, headers: dict = None,
                    timeout: int = 20) -> str:
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={**_HEADERS, "Content-Type": "application/json",
                 **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


# ═══════════════════════════════════════════════════════════════════════════════
# Soyut Taban Sınıfı
# ═══════════════════════════════════════════════════════════════════════════════

class WebSearchEngine(ABC):
    """Tüm web arama engine'leri için soyut taban sınıfı."""

    @property
    @abstractmethod
    def ad(self) -> str:
        """Engine'in benzersiz adı (küçük harf)."""

    @abstractmethod
    def calistir(self, sorgu: str, max_sonuc: int = 5) -> str:
        """Web araması yap, formatlı metin döndür."""
        ...

    def __init__(self) -> None:
        self._hazir = self._bagimliliklari_kontrol_et()

    def _bagimliliklari_kontrol_et(self) -> bool:
        """Alt sınıflar override edebilir. Varsayılan: True."""
        return True

    @property
    def hazir(self) -> bool:
        """Engine kullanıma hazır mı?"""
        return self._hazir

    def hazir_degilse_hata(self) -> Optional[str]:
        """Engine hazır değilse açıklayıcı hata mesajı döndür, yoksa None."""
        return None

    @staticmethod
    def _sonuc_formatla(results: list, kaynak: str) -> str:
        """Sonuçları formatla — tüm engine'ler ortak kullanır."""
        if not results:
            return ""
        satirlar = [f"[Web Arama — {kaynak}]:", "=" * 50]
        for i, r in enumerate(results, 1):
            title = r.get("title", "") or r.get("baslik", "") or ""
            href = r.get("href", "") or r.get("url", "") or ""
            body = r.get("body", "") or r.get("ozet", "") or ""
            satirlar.append(f"\n{i}. {title}")
            if href:
                satirlar.append(f"   URL: {href}")
            if body:
                satirlar.append(f"   Özet: {body[:180]}")
        return "\n".join(satirlar)


# ═══════════════════════════════════════════════════════════════════════════════
# DuckDuckGo Engine
# ═══════════════════════════════════════════════════════════════════════════════

class DuckDuckGoEngine(WebSearchEngine):
    """DuckDuckGo arama engine'i. API key gerekmez.

    Öncelik: duckduckgo-search kütüphanesi
    Fallback: DDG Lite HTML scraping
    """

    @property
    def ad(self) -> str:
        return "duckduckgo"

    def _bagimliliklari_kontrol_et(self) -> bool:
        # duckduckgo-search isteğe bağlı — hiçbiri yoksa Lite HTML fallback çalışır
        return True

    def _ddgs_library_ara(self, sorgu: str, max_sonuc: int = 5) -> Optional[list[dict]]:
        try:
            # duckduckgo_search -> ddgs (yeni paket adi)
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            ddgs = DDGS()
            results = list(ddgs.text(sorgu, max_results=max_sonuc))
            if hasattr(ddgs, "close"):
                ddgs.close()
            if results:
                return [
                    {"href": r.get("href", ""), "title": r.get("title", ""), "body": r.get("body", "")}
                    for r in results
                ]
        except Exception as e:
            log.debug("duckduckgo-search kutuphanesi calismadi: %s", e)
        return None

    def _ddg_lite_ara(self, sorgu: str, max_sonuc: int = 5) -> list[dict]:
        class _Parser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results: list[dict] = []
                self._current: Optional[dict] = None
                self._in_link = False
                self._skip_domains = {"duckduckgo.com", "wikipedia.org"}

            def handle_starttag(self, tag, attrs):
                ad = dict(attrs)
                if tag == "a" and "href" in ad:
                    href = ad["href"]
                    if href.startswith("http") and not any(d in href for d in self._skip_domains):
                        self._in_link = True
                        self._current = {"href": href, "title": "", "body": ""}

            def handle_data(self, data):
                if self._in_link and self._current is not None:
                    self._current["title"] += data.strip()

            def handle_endtag(self, tag):
                if tag == "a" and self._current is not None and self._current.get("title", "").strip():
                    self.results.append(self._current)
                    self._current = None
                    self._in_link = False

        try:
            url = "https://lite.duckduckgo.com/lite/"
            data = urllib.parse.urlencode({"q": sorgu}).encode()
            req = urllib.request.Request(url, data=data)
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            req.add_header("Accept", "text/html")
            resp = urllib.request.urlopen(req, timeout=15)
            html = resp.read().decode("utf-8", errors="replace")
            parser = _Parser()
            parser.feed(html)
            return parser.results[:max_sonuc]
        except Exception as e:
            log.debug("DDG Lite scraping hatasi: %s", e)
            return []

    def calistir(self, sorgu: str, max_sonuc: int = 5) -> str:
        results = self._ddgs_library_ara(sorgu, max_sonuc)
        if results is None:
            results = self._ddg_lite_ara(sorgu, max_sonuc)

        if not results:
            return "Sonuc bulunamadi."

        satirlar = []
        for i, r in enumerate(results, 1):
            title = (r.get("title") or "").strip()
            href = (r.get("href") or "").strip()
            body = (r.get("body") or "").strip()[:200]
            satirlar.append(f"[{i}] {title}")
            if href:
                satirlar.append(f"     {href}")
            if body:
                satirlar.append(f"     {body}")
        return "\n".join(satirlar)


# ═══════════════════════════════════════════════════════════════════════════════
# Google Engine (Stub)
# ═══════════════════════════════════════════════════════════════════════════════

class GoogleEngine(WebSearchEngine):
    """Google Custom Search JSON API stub.

    GOOGLE_API_KEY + GOOGLE_CX ortam değişkenleri gerekli.
    Mevcut değilse NotImplementedError fırlatır.
    """

    @property
    def ad(self) -> str:
        return "google"

    def _bagimliliklari_kontrol_et(self) -> bool:
        api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
        cx = os.environ.get("GOOGLE_CX", "").strip()
        return bool(api_key and cx)

    def calistir(self, sorgu: str, max_sonuc: int = 5) -> str:
        api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
        cx = os.environ.get("GOOGLE_CX", "").strip()
        if not api_key or not cx:
            raise NotImplementedError(
                "GoogleEngine: GOOGLE_API_KEY ve GOOGLE_CX ortam değişkenleri gerekli."
            )
        raise NotImplementedError(
            "GoogleEngine henüz implemente edilmedi. "
            "GOOGLE_API_KEY ve GOOGLE_CX ayarlandı ancak HTTP istemcisi eksik."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Bing Engine (Stub)
# ═══════════════════════════════════════════════════════════════════════════════

class BingEngine(WebSearchEngine):
    """Bing Web Search API stub.

    BING_API_KEY ortam değişkeni gerekli.
    Mevcut değilse NotImplementedError fırlatır.
    """

    @property
    def ad(self) -> str:
        return "bing"

    def _bagimliliklari_kontrol_et(self) -> bool:
        return bool(os.environ.get("BING_API_KEY", "").strip())

    def calistir(self, sorgu: str, max_sonuc: int = 5) -> str:
        api_key = os.environ.get("BING_API_KEY", "").strip()
        if not api_key:
            raise NotImplementedError(
                "BingEngine: BING_API_KEY ortam değişkeni gerekli."
            )
        raise NotImplementedError(
            "BingEngine henüz implemente edilmedi. "
            "BING_API_KEY ayarlandı ancak HTTP istemcisi eksik."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Firecrawl Engine
# ═══════════════════════════════════════════════════════════════════════════════

class FirecrawlEngine(WebSearchEngine):
    """Firecrawl API ile web araması. FIRECRAWL_API_KEY gerekli.

    https://api.firecrawl.dev/v1/search endpoint'ini kullanır.
    """

    @property
    def ad(self) -> str:
        return "firecrawl"

    def _bagimliliklari_kontrol_et(self) -> bool:
        key = os.environ.get("FIRECRAWL_API_KEY") or os.environ.get("FIRECRAWL_KEY")
        return bool(key and not key.startswith("***"))

    def calistir(self, sorgu: str, max_sonuc: int = 5) -> str:
        api_key = os.environ.get("FIRECRAWL_API_KEY") or os.environ.get("FIRECRAWL_KEY")
        if not api_key or api_key.startswith("***"):
            return "[FIRECRAWL] API key bulunamadi. FIRECRAWL_API_KEY ayarlayin."

        try:
            url = "https://api.firecrawl.dev/v1/search"
            data = {"query": sorgu, "limit": max_sonuc, "lang": "tr"}
            result_text = _http_post_json(
                url, data,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=20,
            )
            sonuc = json.loads(result_text)
            if sonuc.get("success") and "data" in sonuc:
                results_data = sonuc["data"]
                raw_results = results_data.get("results", [])
                formatted = [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "body": (r.get("description", "") or r.get("content", "") or "")[:300],
                    }
                    for r in raw_results[:max_sonuc]
                ]
                if formatted:
                    return self._sonuc_formatla(formatted, "Firecrawl")
                return f"[FIRECRAWL] '{sorgu}' için sonuç bulunamadı."
            hata = sonuc.get("error", "Bilinmeyen hata")
            return f"[FIRECRAWL] Arama başarısız: {hata}"
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return "[FIRECRAWL] Kimlik doğrulama hatası. FIRECRAWL_API_KEY kontrol edin."
            elif e.code == 402:
                return "[FIRECRAWL] Kredi limiti doldu. Firecrawl dashboard'dan kredi yükleyin."
            elif e.code == 429:
                return "[FIRECRAWL] Rate limit aşıldı. Daha sonra tekrar deneyin."
            return f"[FIRECRAWL] HTTP {e.code}: {e.reason}"
        except Exception as e:
            log.exception("[FirecrawlEngine] arama hatasi:")
            return f"[FIRECRAWL] Hata: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# Brave Search Engine
# ═══════════════════════════════════════════════════════════════════════════════

class BraveSearchEngine(WebSearchEngine):
    """Brave Search API ile web araması. BRAVE_API_KEY gerekli.

    https://api.search.brave.com/res/v1/web/search endpoint'ini kullanır.
    Brave Search API, API key olmadan calismaz (rate-limited endpoint yoktur).
    Ucretsiz API key: https://brave.com/search/api/
    """

    @property
    def ad(self) -> str:
        return "brave"

    def _bagimliliklari_kontrol_et(self) -> bool:
        key = os.environ.get("BRAVE_API_KEY", "").strip()
        return bool(key and not key.startswith("***"))

    def hazir_degilse_hata(self) -> Optional[str]:
        key = os.environ.get("BRAVE_API_KEY", "").strip()
        if not key or key.startswith("***"):
            return (
                "[BRAVE] BRAVE_API_KEY bulunamadi.\n"
                "  Ucretsiz API key almak icin: https://brave.com/search/api/\n"
                "  Ardindan BRAVE_API_KEY=.env dosyasina ekleyin."
            )
        return None

    def calistir(self, sorgu: str, max_sonuc: int = 5) -> str:
        api_key = os.environ.get("BRAVE_API_KEY", "").strip()
        if not api_key or api_key.startswith("***"):
            return "[BRAVE] API key bulunamadi. BRAVE_API_KEY ayarlayin."

        try:
            result_text = _http_get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": sorgu, "count": max_sonuc, "safesearch": "off"},
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": api_key,
                },
            )
            veri = json.loads(result_text)
            web_results = veri.get("web", {}).get("results", [])
            formatted = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "body": r.get("description", ""),
                }
                for r in web_results[:max_sonuc]
            ]
            if formatted:
                return self._sonuc_formatla(formatted, "Brave Search")
            return f"[BRAVE] '{sorgu}' için sonuç bulunamadı."
        except Exception as e:
            log.exception("[BraveSearchEngine] arama hatasi:")
            return f"[BRAVE] Hata: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# SearXNG Engine
# ═══════════════════════════════════════════════════════════════════════════════

class SearXNGEngine(WebSearchEngine):
    """SearXNG (kendi instance) ile web araması. SEARXNG_URL gerekli.

    SearXNG instance'ının /search endpoint'ine JSON formatında sorgu gönderir.
    Eğer SEARXNG_URL ayarlanmamışsa, herkese açık instance'ları dener.
    """

    # Herkese açık SearXNG instance'ları (son çare fallback)
    PUBLIC_INSTANCES = [
        "https://searx.be",
        "https://search.sapti.me",
        "https://searx.work",
        "https://search.mdosch.de",
    ]

    @property
    def ad(self) -> str:
        return "searxng"

    def _bagimliliklari_kontrol_et(self) -> bool:
        url = os.environ.get("SEARXNG_URL", "").strip()
        return bool(url)

    def hazir_degilse_hata(self) -> Optional[str]:
        url = os.environ.get("SEARXNG_URL", "").strip()
        if not url:
            return (
                "[SEARXNG] SEARXNG_URL ayarlanmamis. "
                "Kendi SearXNG instance'inizi kurun veya SEARXNG_URL=.env dosyasina ekleyin.\n"
                "  Ornek: SEARXNG_URL=http://localhost:8888\n"
                "  Kurulum: docker run --name searxng -p 8888:8080 searxng/searxng"
            )
        return None

    def calistir(self, sorgu: str, max_sonuc: int = 5) -> str:
        base_url = os.environ.get("SEARXNG_URL", "").strip().rstrip("/")
        instances_to_try = []
        if base_url:
            instances_to_try.append(base_url)
        instances_to_try.extend(self.PUBLIC_INSTANCES)

        last_error = None
        for url in instances_to_try:
            try:
                result_text = _http_get(
                    f"{url}/search",
                    params={"q": sorgu, "format": "json", "pageno": 1},
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                )
                veri = json.loads(result_text)
                raw_results = veri.get("results", [])
                formatted = [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "body": r.get("content", ""),
                    }
                    for r in raw_results[:max_sonuc]
                ]
                if formatted:
                    return self._sonuc_formatla(formatted, "SearXNG")
                return f"[SEARXNG] '{sorgu}' icin sonuc bulunamadi."
            except urllib.error.HTTPError as e:
                last_error = f"HTTP {e.code}: {e.reason} ({url})"
                continue
            except Exception as e:
                last_error = f"{e} ({url})"
                continue

        return f"[SEARXNG] Hicbir instance calismadi. {last_error}"


# ═══════════════════════════════════════════════════════════════════════════════
# Exa Engine
# ═══════════════════════════════════════════════════════════════════════════════

class ExaEngine(WebSearchEngine):
    """Exa API ile web araması. EXA_API_KEY gerekli.

    https://api.exa.ai/search endpoint'ine POST JSON sorgu gönderir.
    """

    @property
    def ad(self) -> str:
        return "exa"

    def _bagimliliklari_kontrol_et(self) -> bool:
        key = os.environ.get("EXA_API_KEY", "").strip()
        return bool(key and not key.startswith("***"))

    def calistir(self, sorgu: str, max_sonuc: int = 5) -> str:
        api_key = os.environ.get("EXA_API_KEY", "").strip()
        if not api_key or api_key.startswith("***"):
            return "[EXA] API key bulunamadi. EXA_API_KEY ayarlayin."

        try:
            data = {
                "query": sorgu,
                "numResults": max_sonuc,
                "type": "keyword",
                "contents": {"text": True},
            }
            result_text = _http_post_json(
                "https://api.exa.ai/search",
                data,
                headers={"x-api-key": api_key},
                timeout=20,
            )
            sonuc = json.loads(result_text)
            raw_results = sonuc.get("results", []) or sonuc.get("data", [])
            formatted = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "body": r.get("text", "") or r.get("content", "") or "",
                }
                for r in raw_results[:max_sonuc]
            ]
            if formatted:
                return self._sonuc_formatla(formatted, "Exa")
            return f"[EXA] '{sorgu}' için sonuç bulunamadı."
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return "[EXA] Kimlik doğrulama hatası. EXA_API_KEY kontrol edin."
            elif e.code == 429:
                return "[EXA] Rate limit aşıldı. Daha sonra tekrar deneyin."
            return f"[EXA] HTTP {e.code}: {e.reason}"
        except Exception as e:
            log.exception("[ExaEngine] arama hatasi:")
            return f"[EXA] Hata: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# SearchDispatcher — Tek Dispatcher (multi-backend ABC wrapper)
# ═══════════════════════════════════════════════════════════════════════════════

class SearchDispatcher:
    """Multi-backend web arama dispatcher'ı.

    Tüm engine'leri registry'de tutar, config ve env var'larına göre
    default engine'i seçer.

    Kullanım:
        dispatcher = SearchDispatcher(config=my_config)
        dispatcher.kaydet(DuckDuckGoEngine())
        sonuc = dispatcher.ara("python asyncio", engine="duckduckgo")
        sonuc = dispatcher.ara("python asyncio")  # config'deki default
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        self._engines: dict[str, WebSearchEngine] = {}
        self._varsayilan: Optional[str] = None
        self._config = config or {}

    def kaydet(self, engine: WebSearchEngine) -> None:
        """Bir engine kaydet."""
        adi = engine.ad
        self._engines[adi] = engine
        if self._varsayilan is None:
            self._varsayilan = adi
        log.info("[SearchDispatcher] Engine kaydedildi: %s", adi)

    def _resolve_backend_from_config(self) -> Optional[str]:
        """Config'den backend seçimini çözümle.

        Öncelik sırası:
          1. web.search_backend (per-capability override)
          2. web.backend (genel web backend)
          3. WEB_SEARCH_BACKEND env var
        """
        # 1-2. YAML config
        web_cfg = self._config.get("web")
        if isinstance(web_cfg, dict):
            search_bk = web_cfg.get("search_backend")
            if isinstance(search_bk, str) and search_bk.strip():
                return search_bk.strip().lower()
            backend = web_cfg.get("backend")
            if isinstance(backend, str) and backend.strip():
                return backend.strip().lower()
        # 3. Env var
        env_backend = os.environ.get("WEB_SEARCH_BACKEND", "").strip().lower()
        if env_backend:
            return env_backend
        return None

    def _auto_detect_best(self) -> str:
        """En iyi kullanılabilir engine'i auto-detect et.

        Öncelik sırası:
          1. firecrawl (FIRECRAWL_API_KEY)
          2. exa (EXA_API_KEY)
          3. brave (BRAVE_API_KEY)
          4. searxng (SEARXNG_URL)
          5. duckduckgo (her zaman hazır, fallback)
        """
        fc_key = os.environ.get("FIRECRAWL_API_KEY") or os.environ.get("FIRECRAWL_KEY")
        if fc_key and not fc_key.startswith("***") and "firecrawl" in self._engines:
            return "firecrawl"
        exa_key = os.environ.get("EXA_API_KEY", "").strip()
        if exa_key and not exa_key.startswith("***") and "exa" in self._engines:
            return "exa"
        brave_key = os.environ.get("BRAVE_API_KEY", "").strip()
        if brave_key and not brave_key.startswith("***") and "brave" in self._engines:
            return "brave"
        searxng_url = os.environ.get("SEARXNG_URL", "").strip()
        if searxng_url and "searxng" in self._engines:
            return "searxng"
        return "duckduckgo"

    def _sec_varsayilan(self) -> Optional[WebSearchEngine]:
        """Config'den veya auto-detect'ten varsayılan engine'i seç."""
        config_backend = self._resolve_backend_from_config()
        if config_backend and config_backend in self._engines:
            eng = self._engines[config_backend]
            if eng.hazir:
                return eng
        best = self._auto_detect_best()
        eng = self._engines.get(best)
        if eng and eng.hazir:
            return eng
        return self._engines.get("duckduckgo")

    def sec(self, ad: str) -> Optional[WebSearchEngine]:
        """Ada göre engine seç. Varsayılana düş."""
        eng = self._engines.get(ad)
        if eng is None and self._varsayilan:
            log.warning("[SearchDispatcher] '%s' bulunamadi, varsayilana dusuluyor: %s", ad, self._varsayilan)
            return self._engines.get(self._varsayilan)
        return eng

    @property
    def varsayilan(self) -> Optional[WebSearchEngine]:
        return self._sec_varsayilan()

    @property
    def varsayilan_ad(self) -> str:
        eng = self.varsayilan
        return eng.ad if eng else ""

    def ara(self, sorgu: str, engine: Optional[str] = None, max_sonuc: int = 5) -> str:
        """Ana arama metodu — tek dispatcher.

        Args:
            sorgu: Arama sorgusu.
            engine: Kullanılacak engine adı (None veya "auto" = config'deki default).
            max_sonuc: Maksimum sonuç sayısı.

        Returns:
            Formatlı arama sonuçları veya hata mesajı.
        """
        if not engine or engine == "auto":
            eng = self._sec_varsayilan()
            if eng is None:
                return "[WEB_ARAMA] Kullanilabilir engine bulunamadi."
            adi = eng.ad
        else:
            eng = self.sec(engine)
            adi = engine

        if eng is None:
            return f"[WEB_ARAMA] '{engine}' engine'i bulunamadi ve varsayilan engine yok."

        if not eng.hazir:
            return f"[WEB_ARAMA] '{adi}' engine'i hazir degil (bagimlilik eksik)."
        try:
            return eng.calistir(sorgu, max_sonuc)
        except NotImplementedError as e:
            return f"[WEB_ARAMA] '{adi}' henuz implemente edilmemis: {e}"
        except Exception as e:
            log.exception("[SearchDispatcher] '%s' calistirma hatasi:", adi)
            return f"[WEB_ARAMA] '{adi}' hatasi: {e}"

    def engine_listele(self) -> str:
        """Kayitli engine'leri listele."""
        satirlar = ["[WEB_ARAMA] Kayitli engine'ler:"]
        default_adi = self.varsayilan_ad
        for ad, eng in sorted(self._engines.items()):
            durum = "hazir" if eng.hazir else "bagimlilik eksik"
            isaret = " >" if ad == default_adi else "  "
            satirlar.append(f"  {isaret} {ad} ({durum})")
        backend_info = self._resolve_backend_from_config()
        if backend_info:
            satirlar.append(f"\n[Config] web.backend/search_backend: {backend_info}")
        else:
            satirlar.append("\n[Config] Backend secimi: auto-detect")
        return "\n".join(satirlar)


# ═══════════════════════════════════════════════════════════════════════════════
# WebSearchRegistry — Eski isim, geriye uyumluluk alias'ı
# ═══════════════════════════════════════════════════════════════════════════════

class WebSearchRegistry(SearchDispatcher):
    """Geriye uyumluluk için eski isim. Yeni kod SearchDispatcher kullanmalı."""
    pass


# ── Global dispatcher singleton ────────────────────────────────────────────────

_dispatcher: Optional[SearchDispatcher] = None


def _load_config_for_registry() -> dict:
    """Config dosyasını oku — varsa web.backend/web.search_backend için.

    Öncelik sırası:
      1. reymen_cli.config / ReYMeN_cli.config (CLI yapılandırması)
      2. Proje kökündeki config.yaml (doğrudan YAML okuma)
      3. .ReYMeN/config.yaml (ikincil config)
    """
    # 1. CLI config
    try:
        from reymen_cli.config import load_config
        cfg = load_config() or {}
        if cfg.get("web"):
            return cfg
    except Exception as _e:
        __import__("logging").getLogger(__name__).warning(
            "[SessizExcept] %s: %s", type(_e).__name__, _e
        )
    try:
        from ReYMeN_cli.config import load_config
        cfg = load_config() or {}
        if cfg.get("web"):
            return cfg
    except Exception as _e:
        __import__("logging").getLogger(__name__).warning(
            "[SessizExcept] %s: %s", type(_e).__name__, _e
        )

    # 2. Proje kökü config.yaml
    import yaml
    for cfg_yolu in [
        os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml"),
        os.path.join(os.path.dirname(__file__), "..", "..", "config.yml"),
    ]:
        try:
            with open(os.path.abspath(cfg_yolu)) as f:
                cfg = yaml.safe_load(f) or {}
                if cfg.get("web"):
                    return cfg
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

    # 3. .ReYMeN/config.yaml
    try:
        dot_reymen = os.path.join(os.path.dirname(__file__), "..", "..", ".ReYMeN", "config.yaml")
        with open(os.path.abspath(dot_reymen)) as f:
            cfg = yaml.safe_load(f) or {}
            return cfg
    except Exception as _e:
        __import__("logging").getLogger(__name__).warning(
            "[SessizExcept] %%s: %%s", type(_e).__name__, _e
        )

    return {}


def _get_registry() -> SearchDispatcher:
    global _dispatcher
    if _dispatcher is None:
        config = _load_config_for_registry()
        _dispatcher = SearchDispatcher(config=config)
        _dispatcher.kaydet(DuckDuckGoEngine())
        _dispatcher.kaydet(GoogleEngine())
        _dispatcher.kaydet(BingEngine())
        _dispatcher.kaydet(FirecrawlEngine())
        _dispatcher.kaydet(BraveSearchEngine())
        _dispatcher.kaydet(SearXNGEngine())
        _dispatcher.kaydet(ExaEngine())
    return _dispatcher


def reset_registry() -> None:
    """Dispatcher'i sıfırla (test / yeniden yapılandırma için)."""
    global _dispatcher
    _dispatcher = None


# ═══════════════════════════════════════════════════════════════════════════════
# Tool Fonksiyonu
# ═══════════════════════════════════════════════════════════════════════════════

def web_arama(sorgu: str, backend: str = "duckduckgo", max_sonuc: int = 5) -> str:
    """WEB_ARAMA tool'u — backend parametresi ile çoklu arama motoru.

    Args:
        sorgu: Arama sorgusu.
        backend: Kullanilacak engine adi (duckduckgo, google, bing,
                 firecrawl, brave, searxng, exa, auto).
                 "auto" veya boş: config/auto-detect ile en iyi engine seçilir.
        max_sonuc: Maksimum sonuc sayisi.

    Returns:
        Formatli arama sonuclari veya hata mesaji.
    """
    reg = _get_registry()
    return reg.ara(sorgu, engine=backend, max_sonuc=max_sonuc)


def web_search_engine_listele() -> str:
    """Kayitli engine'leri listele."""
    reg = _get_registry()
    return reg.engine_listele()


# ═══════════════════════════════════════════════════════════════════════════════
# Motor Kayit
# ═══════════════════════════════════════════════════════════════════════════════

def motor_kaydet(motor) -> None:
    """Motor tarafindan otomatik cagrilir. WEB_ARAMA tool'unu kaydeder."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    try:
        motor._plugin_arac_kaydet(
            "WEB_ARAMA",
            lambda ham="": (
                # Parametre: sorgu, backend
                _web_arama_ayristir_ve_calistir(ham)
            ),
            "Web aramasi yapar (coklu back-end)."
            " Kullanim: WEB_ARAMA(sorgu=\"...\", backend=\"duckduckgo|google|bing|firecrawl|brave|searxng|exa|auto\")\n"
            "Varsayilan backend: auto-detect (config veya env var'larina gore en iyisi).\n"
            "DuckDuckGo API key gerekmez. Firecrawl icin FIRECRAWL_API_KEY, Brave icin BRAVE_API_KEY,\n"
            "SearXNG icin SEARXNG_URL, Exa icin EXA_API_KEY gerekli.",
        )
        motor._plugin_arac_kaydet(
            "WEB_ARAMA_BACKEND_LISTELE",
            lambda: web_search_engine_listele(),
            "Kullanilabilir web arama engine'lerini listeler.",
        )
    except Exception as e:
        log.warning("[WebSearchEngine] Motor kayit hatasi: %s", e)


def _web_arama_ayristir_ve_calistir(ham: str) -> str:
    """WEB_ARAMA(ham) -> sorgu, backend ayristir."""
    import re as _re
    # Pattern: WEB_ARAMA(sorgu="...", backend="...")
    sorgu = ""
    backend = "auto"
    s_match = _re.search(r'sorgu\s*=\s*"([^"]*)"', ham)
    if s_match:
        sorgu = s_match.group(1)
    b_match = _re.search(r'backend\s*=\s*"([^"]*)"', ham)
    if b_match:
        backend = b_match.group(1)
    if not sorgu:
        # Fallback: tüm string'i sorgu olarak al
        sorgu = ham.strip().strip('"').strip("'")
    return web_arama(sorgu, backend)


# ═══════════════════════════════════════════════════════════════════════════════
# Test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    print(web_search_engine_listele())
    sorgu = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "python asyncio nedir"
    print("\n--- DuckDuckGo ---")
    print(web_arama(sorgu, backend="duckduckgo"))
    print("\n--- Firecrawl (varsa) ---")
    print(web_arama(sorgu, backend="firecrawl"))
    print("\n--- Brave (varsa) ---")
    print(web_arama(sorgu, backend="brave"))
    print("\n--- SearXNG (varsa) ---")
    print(web_arama(sorgu, backend="searxng"))
    print("\n--- Exa (varsa) ---")
    print(web_arama(sorgu, backend="exa"))
    print("\n--- Auto ---")
    print(web_arama(sorgu, backend="auto"))
    print("\n--- Google (stub) ---")
    print(web_arama(sorgu, backend="google"))
