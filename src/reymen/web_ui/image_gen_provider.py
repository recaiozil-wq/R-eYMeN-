"""
🎨 ReYMeN Image Gen Provider — Görsel üretme katmanı.

API key gerektirmeyen, konfigürasyondan beslenen,
plugins/image_gen/ altındaki provider'ları otomatik keşfeder.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

PROJE_KOK = Path(__file__).resolve().parent.parent.parent
IMAGE_CACHE = PROJE_KOK / "reymen" / "web_ui" / "static" / "generated_images"
HISTORY_FILE = PROJE_KOK / "reymen" / "web_ui" / "image_gen_history.json"

# Varsayılan aspect ratio
DEFAULT_ASPECT_RATIO = "1:1"

# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------


def success_response(
    image_url: str,
    model: str = "",
    provider: str = "",
    metadata: Dict[str, Any] = None,
) -> Dict[str, Any]:
    return {
        "success": True,
        "image_url": image_url,
        "model": model,
        "provider": provider,
        "metadata": metadata or {},
    }


def error_response(
    message: str,
    provider: str = "",
    model: str = "",
) -> Dict[str, Any]:
    return {
        "success": False,
        "error": message,
        "provider": provider,
        "model": model,
    }


def save_url_image(url: str, provider: str, prompt: str) -> Tuple[str, str]:
    """URL'den görsel indir ve cache'e kaydet. (url, local_path) döndür."""
    import requests
    import hashlib

    IMAGE_CACHE.mkdir(parents=True, exist_ok=True)
    hash_str = hashlib.md5(f"{provider}_{prompt}_{time.time()}".encode()).hexdigest()[:12]
    ext = ".png"
    local_name = f"{provider}_{hash_str}{ext}"
    local_path = IMAGE_CACHE / local_name

    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        local_path.write_bytes(r.content)
        return url, str(local_path)
    except Exception as e:
        logger.warning(f"[IMG] URL indirme hatası: {e}")
        return url, ""


def save_b64_image(b64_data: str, provider: str, prompt: str) -> Tuple[str, str]:
    """Base64'ten görsel kaydet. (data_uri, local_path) döndür."""
    import base64
    import hashlib

    IMAGE_CACHE.mkdir(parents=True, exist_ok=True)
    hash_str = hashlib.md5(f"{provider}_{prompt}_{time.time()}".encode()).hexdigest()[:12]
    ext = ".png"
    local_name = f"{provider}_{hash_str}{ext}"
    local_path = IMAGE_CACHE / local_name

    try:
        # Base64 verisini temizle (data:image/...;base64, önekini kaldır)
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]
        image_bytes = base64.b64decode(b64_data)
        local_path.write_bytes(image_bytes)
        data_uri = f"data:image/png;base64,{b64_data}"
        return data_uri, str(local_path)
    except Exception as e:
        logger.warning(f"[IMG] Base64 kaydetme hatası: {e}")
        return "", ""


# ---------------------------------------------------------------------------
# Provider keşfi
# ---------------------------------------------------------------------------


def discover_providers() -> List[Dict[str, str]]:
    """plugins/image_gen/ altındaki provider'ları keşfet.

    Her bir __init__.py dosyası olan klasör bir provider'dır.
    """
    plugins_dir = PROJE_KOK / "plugins" / "image_gen"
    providers = []

    if not plugins_dir.exists():
        logger.warning(f"[IMG] Plugin dizini bulunamadı: {plugins_dir}")
        return providers

    for entry in sorted(plugins_dir.iterdir()):
        if entry.is_dir() and (entry / "__init__.py").exists():
            provider_id = entry.name
            # İsim formatı: fal → FAL, openai-codex → OpenAI Codex
            display = provider_id.replace("-", " ").title().replace(" ", " ")
            if provider_id == "xai":
                display = "xAI (Grok)"
            elif provider_id == "fal":
                display = "FAL.ai"
            providers.append({
                "id": provider_id,
                "name": display,
                "path": str(entry),
            })

    # Fallback: provider bulunamazsa varsayılan listeyi döndür
    if not providers:
        providers = [
            {"id": "fal", "name": "FAL.ai", "path": ""},
            {"id": "krea", "name": "Krea AI", "path": ""},
            {"id": "openai", "name": "OpenAI", "path": ""},
            {"id": "openai-codex", "name": "OpenAI Codex", "path": ""},
            {"id": "xai", "name": "xAI (Grok)", "path": ""},
        ]

    return providers


# ---------------------------------------------------------------------------
# Basit provider implementasyonu (API key gerektirmez - demo/simüle)
# ---------------------------------------------------------------------------


def generate_image_simple(
    prompt: str,
    provider_id: str = "fal",
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    model: str = "",
) -> Dict[str, Any]:
    """API key gerektirmeyen, basit görsel üretme.

    1. Önce plugins/image_gen/{provider_id} import'ını dene
    2. Olmazsa gerçek API'leri dene (ortam değişkenlerinden key al)
    3. Hiçbiri çalışmazsa simüle edilmiş görsel döndür
    """
    # Önce eklenti üzerinden dene
    result = _try_plugin_provider(prompt, provider_id, aspect_ratio, model)
    if result.get("success"):
        return result

    # Eklenti yoksa veya çalışmazsa, provider tipine göre dene
    result = _try_direct_api(prompt, provider_id, aspect_ratio, model)
    if result.get("success"):
        return result

    # Hiçbiri çalışmazsa placeholder görsel oluştur
    return _generate_placeholder(prompt, provider_id, model)


def _try_plugin_provider(
    prompt: str, provider_id: str, aspect_ratio: str, model: str
) -> Dict[str, Any]:
    """plugins/image_gen/ altındaki provider'ı import etmeyi dene."""
    try:
        import importlib

        module_path = f"plugins.image_gen.{provider_id}"
        mod = importlib.import_module(module_path)

        if hasattr(mod, "get_provider"):
            provider = mod.get_provider()
        elif hasattr(mod, "ImageGenProvider"):
            provider_cls = None
            for name in dir(mod):
                obj = getattr(mod, name)
                if isinstance(obj, type) and name != "ImageGenProvider":
                    from agent.image_gen_provider import ImageGenProvider as BaseProvider
                    if issubclass(obj, BaseProvider):
                        provider_cls = obj
                        break
            if provider_cls:
                provider = provider_cls()
            else:
                return error_response("Provider sınıfı bulunamadı", provider_id)
        else:
            return error_response("Provider formatı tanınmadı", provider_id)

        # Provider'ın generate metodu var mı?
        if hasattr(provider, "generate"):
            result = provider.generate(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                model=model or None,
            )
            return result if isinstance(result, dict) else success_response(str(result))

        return error_response("Provider'da generate metodu yok", provider_id)

    except ImportError as e:
        logger.debug(f"[IMG] Plugin import hatası ({provider_id}): {e}")
        return error_response(f"Plugin yüklenemedi: {e}", provider_id)
    except Exception as e:
        logger.debug(f"[IMG] Plugin çalışma hatası ({provider_id}): {e}")
        return error_response(f"Plugin hatası: {e}", provider_id)


def _try_direct_api(
    prompt: str, provider_id: str, aspect_ratio: str, model: str
) -> Dict[str, Any]:
    """Gerçek API'leri dene — ortam değişkenlerinden key oku."""
    import requests

    # Aspect ratio'yu API parametresine çevir
    size_map = {
        "1:1": "1024x1024",
        "16:9": "1792x1024",
        "9:16": "1024x1792",
        "4:3": "1152x896",
        "3:4": "896x1152",
        "21:9": "1920x896",
    }
    size = size_map.get(aspect_ratio, "1024x1024")

    if provider_id == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return error_response("OPENAI_API_KEY bulunamadı", provider_id)
        try:
            resp = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model or "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": size,
                },
                timeout=120,
            )
            data = resp.json()
            if resp.ok and "data" in data:
                url = data["data"][0]["url"]
                _, local = save_url_image(url, provider_id, prompt)
                return success_response(
                    image_url=url,
                    model=model or "dall-e-3",
                    provider=provider_id,
                    metadata={"local_path": local},
                )
            return error_response(f"API hatası: {data}", provider_id)
        except Exception as e:
            return error_response(f"OpenAI hatası: {e}", provider_id)

    elif provider_id == "xai":
        api_key = os.environ.get("XAI_API_KEY", "")
        if not api_key:
            return error_response("XAI_API_KEY bulunamadı", provider_id)
        try:
            resp = requests.post(
                "https://api.x.ai/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model or "grok-image-2",
                    "prompt": prompt,
                    "n": 1,
                },
                timeout=120,
            )
            data = resp.json()
            if resp.ok and "data" in data:
                url = data["data"][0]["url"]
                _, local = save_url_image(url, provider_id, prompt)
                return success_response(
                    image_url=url,
                    model=model or "grok-image-2",
                    provider=provider_id,
                    metadata={"local_path": local},
                )
            return error_response(f"API hatası: {data}", provider_id)
        except Exception as e:
            return error_response(f"xAI hatası: {e}", provider_id)

    return error_response(f"Bilinen provider değil veya API key yok: {provider_id}", provider_id)


def _generate_placeholder(prompt: str, provider_id: str, model: str) -> Dict[str, Any]:
    """API key yoksa placeholder/SVG görsel oluştur."""
    IMAGE_CACHE.mkdir(parents=True, exist_ok=True)

    import hashlib
    hash_str = hashlib.md5(prompt.encode()).hexdigest()[:8]
    local_name = f"{provider_id}_placeholder_{hash_str}.html"
    local_path = IMAGE_CACHE / local_name

    # SVG placeholder — görselin ne olacağını göster
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <rect width="512" height="512" fill="#1a1a2e"/>
  <rect x="32" y="32" width="448" height="448" rx="16" fill="#16213e" stroke="#0f3460" stroke-width="2"/>
  <text x="256" y="200" text-anchor="middle" font-family="Arial" font-size="48" fill="#e94560">🎨</text>
  <text x="256" y="270" text-anchor="middle" font-family="Arial" font-size="14" fill="#a0a0b0">{_escape_svg(prompt[:60])}</text>
  <text x="256" y="300" text-anchor="middle" font-family="Arial" font-size="12" fill="#606080">{provider_id.upper()}</text>
  <text x="256" y="340" text-anchor="middle" font-family="Arial" font-size="10" fill="#404060">⚠️ API anahtarı bulunamadı — placeholder gösteriliyor</text>
</svg>"""

    # SVG'yi data URI olarak kullan
    import base64
    b64 = base64.b64encode(svg.encode()).decode()
    data_uri = f"data:image/svg+xml;base64,{b64}"

    return success_response(
        image_url=data_uri,
        model=model or "placeholder",
        provider=provider_id,
        metadata={
            "note": "API key bulunamadı — placeholder görsel",
            "prompt": prompt,
            "local_path": str(local_path),
        },
    )


def _escape_svg(text: str) -> str:
    """SVG içinde kullanılmak üzere metni kaçır."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


# ---------------------------------------------------------------------------
# Geçmiş yönetimi
# ---------------------------------------------------------------------------


def get_history(limit: int = 50) -> List[Dict[str, Any]]:
    """JSON geçmiş dosyasından son kayıtları oku."""
    if not HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        data.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return data[:limit]
    except Exception as e:
        logger.warning(f"[IMG] Geçmiş okuma hatası: {e}")
        return []


def add_history(entry: Dict[str, Any]) -> None:
    """JSON geçmiş dosyasına kayıt ekle."""
    history = get_history(limit=500)
    history.insert(0, entry)
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(
            json.dumps(history[:500], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning(f"[IMG] Geçmiş yazma hatası: {e}")


def clear_history() -> None:
    """Geçmişi temizle."""
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
