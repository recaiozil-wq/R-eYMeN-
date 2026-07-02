# -*- coding: utf-8 -*-
"""vision_tools.py — ReYMeN Vision Tool (motor.py import'i icin wrapper).

conversation_loop.py'deki VisionAdapter + _vision_analiz() fonksiyonunu motor'a acar.

Kullanim (motor uzerinden):
    GORUNTU_ANALIZ("https://ornek.com/resim.jpg", "Bu resimde ne var?")
    GORUNTU_ANALIZ("C:\\Users\\...\\foto.png", "Analiz et")

Mimari:
    1. motor.py -> _plugin_moduller_yukle() -> tools.vision_tools -> motor_kaydet()
    2. motor_kaydet() -> Motor._plugin_arac_kaydet("GORUNTU_ANALIZ", ...)
    3. LLM "GORUNTU_ANALIZ(...)" dediginde -> Motor.calistir() -> ToolRegistry -> vision_tools.goruntu_analiz_tool()
"""

from __future__ import annotations

import base64
import logging
import os
import re as _re
from typing import Optional

logger = logging.getLogger(__name__)

# VisionAdapter conversation_loop'dan (opsiyonel — loop baglantisiz da calisir)
try:
    from reymen.cereyan.conversation_loop import VisionAdapter
    VISION_HAZIR = True
except ImportError:
    VisionAdapter = None
    VISION_HAZIR = False


# ── Global conversation_loop referansi (motor_kaydet ile set edilir) ──
_GLOBAL_LOOP_REF = None


def motor_kaydet(motor) -> None:
    """Motor tarafindan cagrilir. GORUNTU_ANALIZ aracini registry'e kaydeder.

    Plugin pattern'i: motor._plugin_moduller_yukle() -> import ->
    hasattr(mod, 'motor_kaydet') -> mod.motor_kaydet(self)
    """
    global _GLOBAL_LOOP_REF
    try:
        # Motor uzerinden conversation_loop'a ulasmaya calis
        if hasattr(motor, '_provider_ref'):
            _GLOBAL_LOOP_REF = getattr(motor, '_provider_ref', None)

        motor._plugin_arac_kaydet(
            "GORUNTU_ANALIZ",
            goruntu_analiz_tool,
            "Gorsel/resim analizi. Parametreler: gorsel_yolu (str) — "
            "gorsel URL'si veya dosya yolu; soru (str, opsiyonel) — "
            "analiz sorusu (varsayilan: 'Bu gorseli analiz et.'). "
            "Once DeepSeek V4 Flash (multimodal) dener, basarisizsa "
            "OpenRouter Qwen-VL fallback kullanir.",
        )
        logger.info("[VisionTools] GORUNTU_ANALIZ motor'a kaydedildi")
    except Exception as e:
        logger.warning("[VisionTools] motor_kaydet hatasi: %s", e)


def goruntu_analiz_tool(gorsel_yolu: str = "", soru: str = "") -> str:
    """GORUNTU_ANALIZ motor tool ana fonksiyonu.

    conversation_loop baglantisi varsa onun _vision_analiz'ini kullanir,
    yoksa dogrudan OpenRouter/DeepSeek API ile calisir.

    Args:
        gorsel_yolu: Gorsel URL'si veya dosya yolu
        soru: Analiz icin ek soru (opsiyonel)

    Returns:
        Analiz sonucu metin
    """
    # 1. VisionAdapter uzerinden conversation_loop'a baglanmayi dene
    if VISION_HAZIR and VisionAdapter is not None:
        try:
            adapter = VisionAdapter()
            if adapter._loop_ref is not None:
                # Loop baglantisi var -> loop'un kendi vision'ini kullan
                soru = soru or "Bu gorseli Turkce analiz et, detayli acikla."
                sorgu = f"{gorsel_yolu} {soru}" if gorsel_yolu else soru
                return adapter._vision_analiz(sorgu)
        except Exception as e:
            logger.debug("[VisionTools] VisionAdapter baglantisi basarisiz: %s (standalone mod)", e)

    # 2. Dosya yolunu/sorguyu hazirla
    if not gorsel_yolu:
        return "[GORUNTU_ANALIZ] Gorsel yolu veya URL gerekli."

    soru_metin = soru or "Bu gorseli Turkce analiz et, detayli acikla."

    try:
        from openai import OpenAI

        # URL veya dosya yolunu belirle
        resim_url = ""
        if gorsel_yolu.startswith(("http://", "https://", "data:")):
            resim_url = gorsel_yolu
        else:
            # Dosya yolunu base64'e cevir
            if os.path.exists(gorsel_yolu):
                with open(gorsel_yolu, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                # Format belirle
                ext = os.path.splitext(gorsel_yolu)[1].lower().lstrip(".")
                mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png",
                           "gif": "gif", "webp": "webp", "bmp": "bmp"}
                mime = mime_map.get(ext, "jpeg")
                resim_url = f"data:image/{mime};base64,{img_b64}"
            else:
                return f"[GORUNTU_ANALIZ] Dosya bulunamadi: {gorsel_yolu}"

        # 3. Once DeepSeek V4 Flash dene
        ds_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if ds_key:
            try:
                client = OpenAI(api_key=ds_key, base_url="https://api.deepseek.com")
                r = client.chat.completions.create(
                    model="deepseek-v4-flash",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": soru_metin},
                            {"type": "image_url", "image_url": {"url": resim_url}},
                        ],
                    }],
                    max_tokens=1024,
                )
                content = r.choices[0].message.content
                return content.strip() if content else "[GORUNTU_ANALIZ] Bos yanit (DeepSeek)"
            except Exception as e:
                logger.debug("[VisionTools] DeepSeek vision basarisiz: %s (OpenRouter fallback)", e)

        # 4. Fallback: OpenRouter (Qwen-VL)
        or_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not or_key:
            if ds_key:
                return f"[GORUNTU_ANALIZ] DeepSeek vision hatasi. OpenRouter API key de bulunamadi."
            return "[GORUNTU_ANALIZ] Ne DEEPSEEK_API_KEY ne de OPENROUTER_API_KEY .env'de var."

        client = OpenAI(api_key=or_key, base_url="https://openrouter.ai/api/v1")
        r = client.chat.completions.create(
            model="qwen/qwen-vl-plus:free",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": soru_metin},
                    {"type": "image_url", "image_url": {"url": resim_url}},
                ],
            }],
            max_tokens=1024,
        )
        content = r.choices[0].message.content
        return content.strip() if content else "[GORUNTU_ANALIZ] Bos yanit (OpenRouter)"

    except Exception as e:
        logger.exception("[VisionTools] goruntu_analiz_tool hatasi:")
        return f"[GORUNTU_ANALIZ] Hata: {e}"


def vision_analiz(gorsel_yolu: str = "", soru: str = "Bu gorseli analiz et.") -> Optional[str]:
    """Geriye uyumlu: dogrudan cagrilabilir vision fonksiyonu.

    Args:
        gorsel_yolu: Gorsel dosya yolu veya URL
        soru: Analiz sorusu

    Returns:
        Analiz sonucu metin veya None
    """
    return goruntu_analiz_tool(gorsel_yolu, soru)
