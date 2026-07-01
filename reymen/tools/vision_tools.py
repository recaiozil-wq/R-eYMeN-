"""ReYMeN tools.vision_tools shim — Hermes vision fonksiyonlarını ReYMeN'e yönlendirir."""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def vision_analyze_tool(
    image_url: str,
    question: Optional[str] = None,
    **kwargs,
) -> str:
    """Hermes vision_analyze_tool — ReYMeN vision engine'e yönlendirir.

    Görsel analizi için LLM'in vision yeteneğini kullanır.
    """
    try:
        from reymen.arac.araclar_goruntu import gorsel_analiz
        result = gorsel_analiz(image_url, question or "")
        return json.dumps({"success": True, "analysis": result})
    except ImportError:
        # Fallback: dosyayı oku ve döndür
        try:
            if image_url.startswith(("http://", "https://")):
                import urllib.request
                import tempfile
                with urllib.request.urlopen(image_url, timeout=10) as resp:
                    data = resp.read()
                return json.dumps({
                    "success": True,
                    "image_size": len(data),
                    "note": "Vision analysis not available (araclar_goruntu not found)",
                })
        except Exception as _e:
            logger.warning("[VisionTools] except Exception (L37): %s", Exception)
            pass
        return json.dumps({
            "success": False,
            "error": f"Vision analysis unavailable: {image_url}",
        })
