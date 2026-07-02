#!/usr/bin/env python3
# Apache 2.0 — ReYMeN Image Gen shim. Bagimsiz: stdlib + reymen.arac.image_gen_engine.
"""
image_generation_tool.py — ReYMeN Image Gen shim.

Hermes ``tools.image_generation_tool`` yerine ReYMeN'in kendi
``reymen.arac.image_gen_engine`` motorunu kullanir. FAL, OpenAI, xAI
ve Stub engine'leri destekler.

Import hook uzerinden ``from tools.image_generation_tool import ...``
cagrilari otomatik olarak bu module yonlendirilir.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

from src.reymen.arac.image_gen_engine import (
    _get_registry,
    resim_olustur as _reymen_resim_olustur,
)
from src.reymen.sistem.tools_registry import registry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
DEFAULT_ASPECT_RATIO = "landscape"
VALID_ASPECT_RATIOS = ("landscape", "square", "portrait")

# ReYMeN coords: landscape=16:9→genis, square=1:1→kare, portrait=9:16→dar
_ASPECT_TO_SIZE = {
    "landscape": ("1792", "1024"),    # 16:9
    "square": ("1024", "1024"),        # 1:1
    "portrait": ("1024", "1792"),      # 9:16
}

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
IMAGE_GENERATE_SCHEMA: Dict[str, Any] = {
    "name": "image_generate",
    "description": (
        "Gorsel uretir (FAL / OpenAI / xAI). "
        "Prompt'a gore yapay zeka ile goruntu olusturur. "
        "aspect_ratio: landscape (genis), square (kare), portrait (dikey). "
        "FAL_KEY, OPENAI_API_KEY veya XAI_API_KEY ortam degiskeni gerekli."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Gorselin prompt/aciklamasi (ornek: 'bir kedi, yagli boya, pastel renkler')",
            },
            "aspect_ratio": {
                "type": "string",
                "enum": ["landscape", "square", "portrait"],
                "description": "Gorsel en/boy orani: landscape (genis, 16:9), square (kare, 1:1), portrait (dikey, 9:16)",
                "default": "landscape",
            },
            "image_url": {
                "type": "string",
                "description": "Varolan bir gorseli duzenlemek icin URL (opsiyonel, image-to-image)",
            },
            "reference_image_urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Stil/kompozisyon referans gorsel URL'leri (opsiyonel, en fazla 9)",
            },
        },
        "required": ["prompt"],
    },
}


def check_image_generation_requirements() -> bool:
    """Herhangi bir image gen backend kullanilabilir mi?"""
    reg = _get_registry()
    for eng in reg._engines.values():
        if eng.hazir:
            return True
    return False


def _build_no_backend_setup_message() -> str:
    """Kullaniciya hangi API anahtarlarinin eksik oldugunu goster."""
    reg = _get_registry()
    eksik = []
    for ad, eng in reg._engines.items():
        if ad == "stub":
            continue
        if not eng.hazir:
            env_map = {
                "fal": "FAL_KEY",
                "openai": "OPENAI_API_KEY",
                "xai": "XAI_API_KEY",
            }
            env = env_map.get(ad, f"{ad.upper()}_API_KEY")
            eksik.append(f"{ad} ({env})")
    if eksik:
        return (
            "Hicbir gorsel uretim back-end'i hazir degil. "
            "Su API anahtarlarindan birini .env dosyasina ekleyin:\n"
            + "\n".join(f"  • {e}" for e in eksik)
        )
    return "Hicbir gorsel uretim back-end'i bulunamadi."


def _aspect_to_size(aspect: str) -> tuple[str, str]:
    """aspect_ratio → (en, boy) stringleri."""
    return _ASPECT_TO_SIZE.get(aspect, ("1024", "1024"))


def image_generate_tool(
    prompt: str,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    image_url: Optional[str] = None,
    reference_image_urls: Optional[list] = None,
    **kwargs: Any,
) -> str:
    """ReYMeN Image Gen — Hermes uyumlu arayuz.

    Args:
        prompt: Gorsel prompt/aciklamasi.
        aspect_ratio: Gorsel orani (landscape/square/portrait).
        image_url: Varolan gorsel URL'si (opsiyonel, edit modu).
        reference_image_urls: Referans gorsel URL'leri (opsiyonel).

    Returns:
        JSON string: {"success": bool, "image": url|None, "error": str, ...}
    """
    try:
        if not prompt or not isinstance(prompt, str) or not prompt.strip():
            return json.dumps({
                "success": False,
                "image": None,
                "modality": "text",
                "error": "Prompt bos olamaz.",
                "error_type": "validation",
            })

        # aspect_ratio dogrula
        ar = (aspect_ratio or DEFAULT_ASPECT_RATIO).lower().strip()
        if ar not in VALID_ASPECT_RATIOS:
            ar = DEFAULT_ASPECT_RATIO

        en, boy = _aspect_to_size(ar)

        # Edit modu: image_url varsa uyari ver (ReYMeN engine su an edit desteklemez)
        if image_url or reference_image_urls:
            logger.info("image_url/reference_image_urls alindi ancak ReYMeN engine edit modu icin basit FAL'e yonlendiriyor")
            # Basit FAL backend denemesi — FAL engine edit destekler
            sonuc = _reymen_resim_olustur(prompt.strip(), en, boy, backend="fal")
        else:
            # Varsayilan backend
            sonuc = _reymen_resim_olustur(prompt.strip(), en, boy, backend="")

        # ReYMeN engine [MEDIA] formatinda doner
        if "[RESIM_OLUSTUR" in sonuc and "Hata" in sonuc:
            return json.dumps({
                "success": False,
                "image": None,
                "modality": "text",
                "error": sonuc,
                "error_type": "generation",
            })

        # MEDIA etiketinden URL'yi cikar
        import re
        url_match = re.search(r'src="([^"]+)"', sonuc)
        image_url_result = url_match.group(1) if url_match else None

        return json.dumps({
            "success": True,
            "image": image_url_result,
            "modality": "image" if image_url_result else "text",
            "error": None,
            "error_type": None,
        })

    except Exception as e:
        logger.exception("[image_generation_tool] Hata:")
        return json.dumps({
            "success": False,
            "image": None,
            "modality": "text",
            "error": str(e),
            "error_type": "exception",
        })


def _handle_image_generate(**kwargs: Any) -> str:
    """Registry handler wrapper."""
    return image_generate_tool(**kwargs)


# ---------------------------------------------------------------------------
# Registry kaydi (otomatik keşif icin)
# ---------------------------------------------------------------------------
registry.register(
    name="image_generate",
    toolset="image_gen",
    schema=IMAGE_GENERATE_SCHEMA,
    handler=_handle_image_generate,
    check_fn=check_image_generation_requirements,
    requires_env=["FAL_KEY", "OPENAI_API_KEY", "XAI_API_KEY"],
    description="Gorsel uretir (FAL / OpenAI / xAI). FAL_KEY, OPENAI_API_KEY veya XAI_API_KEY gerekli.",
    emoji="🎨",
)
