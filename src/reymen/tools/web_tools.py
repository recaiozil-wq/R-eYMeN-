#!/usr/bin/env python3
"""
ReYMeN Web Tools — Bağımsız web_search_tool ve web_extract_tool.

Hermes Agent'tan bağımsızlaştırılmıştır. Provider'ları reymen.web_search_registry
üzerinden çözümler, SSRF koruması için reymen.tools.url_safety kullanır.

Env vars:
  REYMEN_SEARCH_BACKEND / REYMEN_EXTRACT_BACKEND / REYMEN_WEB_BACKEND
  FIRECRAWL_API_KEY, TAVILY_API_KEY, EXA_API_KEY, PARALLEL_API_KEY,
  BRAVE_SEARCH_API_KEY, SEARXNG_URL
  WEB_TOOLS_DEBUG=true  (debug log)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ReYMeN-native imports — Hermes bağımlılığı yok
# ---------------------------------------------------------------------------
from src.reymen.tools.url_safety import async_is_safe_url, normalize_url_for_request
from src.reymen.tools.debug_helpers import DebugSession
from src.reymen.tools.website_policy import check_website_access

# ---------------------------------------------------------------------------
# Backend selection helpers
# ---------------------------------------------------------------------------

DEFAULT_MIN_LENGTH_FOR_SUMMARIZATION = 5000


def _has_env(name: str) -> bool:
    return bool((os.getenv(name) or "").strip())


def _get_backend() -> str:
    """Backend seçimi: REYMEN_WEB_BACKEND env var veya env var'dan otomatik."""
    configured = (os.getenv("REYMEN_WEB_BACKEND") or "").lower().strip()
    if configured in ("parallel", "firecrawl", "tavily", "exa", "searxng", "brave-free", "ddgs", "xai"):
        return configured

    backends = (
        ("tavily", _has_env("TAVILY_API_KEY")),
        ("exa", _has_env("EXA_API_KEY")),
        ("parallel", _has_env("PARALLEL_API_KEY")),
        ("firecrawl", _has_env("FIRECRAWL_API_KEY") or _has_env("FIRECRAWL_API_URL")),
        ("searxng", _has_env("SEARXNG_URL")),
        ("brave-free", _has_env("BRAVE_SEARCH_API_KEY")),
    )
    for backend, available in backends:
        if available:
            return backend
    return "firecrawl"


def _get_capability_backend(capability: str) -> str:
    """Per-capability backend: REYMEN_{cap}_BACKEND veya shared."""
    key = f"REYMEN_{capability.upper()}_BACKEND"
    specific = (os.getenv(key) or "").lower().strip()
    if specific and _is_backend_available(specific):
        return specific
    return _get_backend()


def _get_search_backend() -> str:
    return _get_capability_backend("search")


def _get_extract_backend() -> str:
    return _get_capability_backend("extract")


def _is_backend_available(backend: str) -> bool:
    if backend == "exa":
        return _has_env("EXA_API_KEY")
    if backend == "parallel":
        return _has_env("PARALLEL_API_KEY")
    if backend == "firecrawl":
        return _has_env("FIRECRAWL_API_KEY") or _has_env("FIRECRAWL_API_URL")
    if backend == "tavily":
        return _has_env("TAVILY_API_KEY")
    if backend == "searxng":
        return _has_env("SEARXNG_URL")
    if backend == "brave-free":
        return _has_env("BRAVE_SEARCH_API_KEY")
    if backend == "ddgs":
        try:
            import ddgs  # noqa: F401
            return True
        except ImportError:
            return False
    return False


# ---------------------------------------------------------------------------
# LLM summarization — opsiyonel (auxiliary client yoksa atlanır)
# ---------------------------------------------------------------------------

async def _try_summarize(content: str, url: str = "", title: str = "",
                          min_length: int = DEFAULT_MIN_LENGTH_FOR_SUMMARIZATION) -> Optional[str]:
    """LLM ile özetleme dene. auxiliary client yoksa None döner."""
    if len(content) < min_length:
        return None
    if len(content) > 2_000_000:
        return f"[Content too large: {len(content)/1_000_000:.1f}MB]"

    try:
        # Opsiyonel: auxiliary LLM client varsa kullan
        from reymen.auxiliary import async_web_extract_summarize
        return await async_web_extract_summarize(content, url, title)
    except ImportError:
        logger.debug("reymen.auxiliary mevcut değil, LLM özetleme atlanıyor")
        return None
    except Exception as exc:
        logger.warning("LLM summarization failed: %s", exc)
        truncated = content[:5000]
        if len(content) > 5000:
            truncated += f"\n\n[Content truncated — first 5,000 of {len(content):,} chars]"
        return truncated


# ---------------------------------------------------------------------------
# Basit tool_error / tool_result yardımcıları
# ---------------------------------------------------------------------------

def tool_error(message: str, **extra) -> str:
    result = {"error": str(message)}
    if extra:
        result.update(extra)
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Debug session
# ---------------------------------------------------------------------------

_debug = DebugSession("web_tools", env_var="WEB_TOOLS_DEBUG")


# ---------------------------------------------------------------------------
# Provider'ları yükle (ensure_web_plugins_loaded)
# ---------------------------------------------------------------------------

def _ensure_web_plugins_loaded() -> None:
    """Plugin'leri yükle — providers register olur. Idempotent."""
    try:
        from reymen.web_search_registry import get_provider

        # Sadece bir kere kontrol et: eğer firecrawl kayıtlıysa tamamdır
        if get_provider("firecrawl") is not None:
            return

        # Provider'ları doğrudan register et
        _import_all_providers()
    except Exception as exc:
        logger.warning("Web plugin registration failed (non-fatal): %s", exc)


def _import_all_providers() -> None:
    """Tüm built-in web provider'larını ReYMeN registry'ye kaydet."""
    from reymen.web_search_registry import register_provider

    # Her provider'ın class'ını import et ve register et
    provider_classes = [
        ("plugins.web.firecrawl.provider", "FirecrawlWebSearchProvider"),
        ("plugins.web.ddgs.provider", "DDGSWebSearchProvider"),
        ("plugins.web.brave_free.provider", "BraveFreeWebSearchProvider"),
        ("plugins.web.searxng.provider", "SearXNGWebSearchProvider"),
        ("plugins.web.exa.provider", "ExaWebSearchProvider"),
        ("plugins.web.parallel.provider", "ParallelWebSearchProvider"),
        ("plugins.web.tavily.provider", "TavilyWebSearchProvider"),
        ("plugins.web.xai.provider", "XAIWebSearchProvider"),
    ]
    for mod_name, class_name in provider_classes:
        try:
            mod = __import__(mod_name, fromlist=[class_name])
            cls = getattr(mod, class_name, None)
            if cls is not None:
                register_provider(cls())
        except Exception as exc:
            logger.debug("Provider %s.%s yüklenemedi: %s", mod_name, class_name, exc)


# ---------------------------------------------------------------------------
# web_search_tool
# ---------------------------------------------------------------------------

def web_search_tool(query: str, limit: int = 5) -> str:
    """Web'de arama yap. Provider registry üzerinden dispatch eder.

    Args:
        query: Arama sorgusu
        limit: Sonuç sayısı (1-100)

    Returns:
        JSON: {"success": bool, "data": {"web": [...]} veya "error": str}
    """
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 5
    limit = min(max(limit, 1), 100)

    debug_data = {"query": query, "limit": limit, "error": None, "results_count": 0}

    try:
        _ensure_web_plugins_loaded()
        from reymen.web_search_registry import get_active_search_provider, get_provider as _get_provider

        backend = _get_search_backend()
        provider = _get_provider(backend) if backend else None
        if provider is None or not provider.supports_search():
            provider = get_active_search_provider()

        if provider is None:
            response_data = {
                "success": False,
                "error": "No web search provider configured. Set FIRECRAWL_API_KEY "
                         "or another search API key in .env",
            }
        else:
            logger.info("Web search via %s: '%s' (limit: %d)", provider.name, query, limit)
            response_data = provider.search(query, limit)

        debug_data["results_count"] = len(response_data.get("data", {}).get("web", []))
        result_json = json.dumps(response_data, indent=2, ensure_ascii=False)
        _debug.log_call("web_search_tool", debug_data)
        _debug.save()
        return result_json

    except Exception as e:
        error_msg = f"Error searching web: {e}"
        logger.debug("%s", error_msg)
        debug_data["error"] = error_msg
        _debug.log_call("web_search_tool", debug_data)
        _debug.save()
        return tool_error(error_msg)


# ---------------------------------------------------------------------------
# web_extract_tool
# ---------------------------------------------------------------------------

async def web_extract_tool(
    urls: List[str],
    format: str = None,
    use_llm_processing: bool = True,
    model: Optional[str] = None,
    min_length: int = DEFAULT_MIN_LENGTH_FOR_SUMMARIZATION,
) -> str:
    """Web sayfalarından içerik çek. Provider registry üzerinden dispatch.

    Args:
        urls: Çekilecek URL listesi
        format: Çıktı formatı ("markdown" veya "html")
        use_llm_processing: LLM özetleme kullanılsın mı
        model: Kullanılacak model (opsiyonel)
        min_length: LLM özetleme için minimum karakter (default: 5000)

    Returns:
        JSON: {"results": [...]} veya {"success": False, "error": str}
    """
    if isinstance(urls, str):
        urls = [urls]

    # Normalize + secret check
    normalized_urls: List[str] = []
    for _url in urls:
        if not isinstance(_url, str):
            continue
        # Basit secret pattern kontrolü (api key vs)
        _secret_pattern = re.compile(
            r"(?i)(sk-[a-z0-9]{20,}|ghp_[a-zA-Z0-9]{36,}|"
            r"AIza[0-9A-Za-z_-]{35}|xox[bpras]-[0-9a-zA-Z-]{10,})"
        )
        from urllib.parse import unquote
        decoded = unquote(_url)
        if _secret_pattern.search(_url) or _secret_pattern.search(decoded):
            return json.dumps({
                "success": False,
                "error": "Blocked: URL contains what appears to be an API key or token.",
            })
        normalized_urls.append(normalize_url_for_request(_url))

    debug_data = {
        "urls": normalized_urls, "format": format,
        "use_llm_processing": use_llm_processing,
        "error": None, "pages_extracted": 0,
    }

    try:
        logger.info("Extracting content from %d URL(s)", len(normalized_urls))

        # SSRF protection
        safe_urls = []
        ssrf_blocked: List[Dict[str, Any]] = []
        for url in normalized_urls:
            if not await async_is_safe_url(url):
                ssrf_blocked.append({
                    "url": url, "title": "", "content": "",
                    "error": "Blocked: URL targets a private or internal network address",
                })
            else:
                safe_urls.append(url)

        results = []
        if safe_urls:
            _ensure_web_plugins_loaded()
            from reymen.web_search_registry import get_active_extract_provider, get_provider as _get_provider

            backend = _get_extract_backend()
            provider = _get_provider(backend) if backend else None
            if provider is None or not provider.supports_extract():
                if provider is not None and not provider.supports_extract():
                    return json.dumps({
                        "success": False,
                        "error": f"{provider.display_name} is search-only. "
                                 f"Set extract to firecrawl, tavily, exa, or parallel.",
                    })
                provider = get_active_extract_provider()
                if provider is None:
                    return json.dumps({
                        "success": False,
                        "error": "No web extract provider configured. "
                                 "Set FIRECRAWL_API_KEY or another extract API key.",
                    })

            logger.info("Web extract via %s: %d URL(s)", provider.name, len(safe_urls))

            import inspect
            if inspect.iscoroutinefunction(provider.extract):
                results = await provider.extract(safe_urls, format=format)
            else:
                results = await asyncio.to_thread(provider.extract, safe_urls, format=format)

        if ssrf_blocked:
            results = ssrf_blocked + results

        response = {"results": results}
        pages_extracted = len(response.get("results", []))
        logger.info("Extracted content from %d pages", pages_extracted)
        debug_data["pages_extracted"] = pages_extracted

        # LLM processing
        if use_llm_processing and results:
            logger.info("Processing extracted content with LLM...")

            async def process_result(result):
                url = result.get("url", "")
                title = result.get("title", "")
                raw = result.get("raw_content", "") or result.get("content", "")
                if not raw:
                    return result
                processed = await _try_summarize(raw, url, title, min_length)
                if processed:
                    result["content"] = processed
                    result["raw_content"] = raw
                return result

            processed = [await process_result(r) for r in results]
            response = {"results": processed}
            debug_data["llm_processing_applied"] = True

        result_json = json.dumps(response, indent=2, ensure_ascii=False)
        _debug.log_call("web_extract_tool", debug_data)
        _debug.save()
        return result_json

    except Exception as e:
        error_msg = f"Error extracting web content: {e}"
        logger.debug("%s", error_msg)
        debug_data["error"] = error_msg
        _debug.log_call("web_extract_tool", debug_data)
        _debug.save()
        return tool_error(error_msg)
