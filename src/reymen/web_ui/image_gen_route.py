#!/usr/bin/env python3
# Apache 2.0 — ReYMeN Web UI Image Gen Route
"""
image_gen_route.py — FastAPI route for image generation.

GET  /image-gen  → HTML form
POST /image-gen  → Generate image via ReYMeN engine

Uses ``src.reymen.tools.image_generation_tool.image_generate_tool``
which delegates to the ReYMeN image_gen_engine (FAL / OpenAI / xAI).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# ReYMeN image gen engine
from src.reymen.tools.image_generation_tool import image_generate_tool

logger = logging.getLogger(__name__)

router = APIRouter(tags=["image-gen"])

# Templates — parent dir'deki templates/ klasörü
from pathlib import Path
_TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


@router.get("/image-gen", response_class=HTMLResponse)
async def image_gen_form(request: Request):
    """GET — Görsel üretme formu."""
    return templates.TemplateResponse(
        request, "image_gen.html", {}
    )


@router.post("/image-gen")
async def image_gen_generate(
    request: Request,
    prompt: str = Form(...),
    provider: str = Form("auto"),
    aspect_ratio: str = Form("square"),
):
    """POST — Görsel üret.

    Form fields:
        prompt (str): Görsel prompt'u.
        provider (str): Backend (auto/fal/openai/xai/stub).
        aspect_ratio (str): landscape / square / portrait.

    Returns JSON:
        success, image (url), provider, model, duration, error
    """
    start = time.time()

    if not prompt or not prompt.strip():
        return JSONResponse({
            "success": False,
            "error": "Prompt boş olamaz.",
        })

    try:
        # Provider'a göre davran
        if provider == "stub":
            # Stub: her zaman place holder döndür
            result = _stub_generate(prompt, aspect_ratio)
        else:
            # ReYMeN engine (auto-selection)
            result_raw = image_generate_tool(
                prompt=prompt.strip(),
                aspect_ratio=aspect_ratio or "square",
            )
            result = json.loads(result_raw)

        duration = time.time() - start

        if result.get("success"):
            return JSONResponse({
                "success": True,
                "image": result.get("image"),
                "provider": result.get("provider", provider),
                "model": result.get("model", ""),
                "duration": round(duration, 2),
                "error": None,
            })

        # Hata durumu
        return JSONResponse({
            "success": False,
            "image": result.get("image"),
            "provider": provider,
            "model": result.get("model", ""),
            "duration": round(duration, 2),
            "error": result.get("error", "Görsel üretilemedi."),
        })

    except Exception as e:
        logger.exception("[image_gen_route] Hata:")
        duration = time.time() - start
        return JSONResponse({
            "success": False,
            "image": None,
            "provider": provider,
            "error": str(e),
            "duration": round(duration, 2),
        })


def _stub_generate(prompt: str, aspect_ratio: str) -> dict[str, Any]:
    """Stub/fallback — SVG placeholder üret."""
    import hashlib
    import base64

    w, h = {"landscape": (640, 360), "square": (512, 512), "portrait": (360, 640)}.get(aspect_ratio, (512, 512))

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <rect width="{w}" height="{h}" fill="#1a1a2e"/>
  <rect x="16" y="16" width="{w-32}" height="{h-32}" rx="12" fill="#16213e" stroke="#0f3460" stroke-width="2"/>
  <text x="{w//2}" y="{h//2-20}" text-anchor="middle" font-family="Arial" font-size="36" fill="#e94560">🎨</text>
  <text x="{w//2}" y="{h//2+30}" text-anchor="middle" font-family="Arial" font-size="11" fill="#a0a0b0">{_esc(prompt[:50])}</text>
  <text x="{w//2}" y="{h//2+55}" text-anchor="middle" font-family="Arial" font-size="10" fill="#606080">STUB — placeholder</text>
</svg>"""

    b64 = base64.b64encode(svg.encode()).decode()
    data_uri = f"data:image/svg+xml;base64,{b64}"

    return {
        "success": True,
        "image": data_uri,
        "provider": "stub",
        "model": "placeholder",
        "error": None,
    }


def _esc(text: str) -> str:
    """SVG-escape text."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
