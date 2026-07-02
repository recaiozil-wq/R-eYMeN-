# -*- coding: utf-8 -*-
"""
image_gen_engine.py — Çok back-end'li görsel üretim motoru (ABC tabanlı).

ImageGenEngine ABC:
  - Soyut calistir(prompt, en, boy) → str

Engine'ler:
  - FALEngine       — fal.ai API (FAL_KEY ortam değişkeni)
  - OpenAIEngine    — DALL-E (OPENAI_API_KEY ortam değişkeni)
  - StubEngine      — local dummy (bağımlılık gerektirmez, simüle eder)

ImageGenRegistry:
  - engine kaydet / seç (ad ile) / calistir
  - Varsayılan engine: stub (FAL_KEY varsa FAL, OPENAI_API_KEY varsa OpenAI)

Motor tool:
  RESIM_OLUSTUR(prompt, en="1024", boy="1024", backend="stub") → str
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional
import logging
logger = logging.getLogger(__name__)

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Sabitler
# ═══════════════════════════════════════════════════════════════════════════════

# Modern FAL.ai endpoint — https://fal.run/<model_id>
# See https://fal.ai/docs for available models (flux-1-1-pro, flux-2-pro, flux-2/klein/9b, …)
_FAL_RUN_URL = "https://fal.run/fal-ai/flux-1-1-pro"
_FAL_RUN_PRO_URL = "https://fal.run/fal-ai/flux-2-pro"
_FAL_RUN_KLEIN_URL = "https://fal.run/fal-ai/flux-2/klein/9b"
_OPENAI_IMAGE_URL = "https://api.openai.com/v1/images/generations"
_XAI_IMAGE_URL = "https://api.x.ai/v1/images/generations"
_USER_AGENT = "ReYMeN-Ajan/1.0"


# ═══════════════════════════════════════════════════════════════════════════════
# Soyut Taban Sınıfı
# ═══════════════════════════════════════════════════════════════════════════════

class ImageGenEngine(ABC):
    """Tüm görsel üretim engine'leri için soyut taban sınıfı."""

    @property
    @abstractmethod
    def ad(self) -> str:
        """Engine'in benzersiz adı (küçük harf)."""

    @abstractmethod
    def calistir(self, prompt: str, en: str = "1024", boy: str = "1024") -> str:
        """Görsel üret, formatlı [MEDIA] metni döndür."""
        ...

    def __init__(self) -> None:
        self._hazir = self._bagimliliklari_kontrol_et()

    def _bagimliliklari_kontrol_et(self) -> bool:
        return True

    @property
    def hazir(self) -> bool:
        return self._hazir

    def _media(self, tip: str, kaynak: str, aciklama: str = "") -> str:
        blok = f'[MEDIA type="{tip}" src="{kaynak}"]'
        if aciklama:
            blok += f"\n{aciklama}"
        blok += "\n[/MEDIA]"
        return blok

    def _http_post_json(self, url: str, payload: dict, headers: dict = None, timeout: int = 90) -> dict:
        import urllib.request as _req
        data = json.dumps(payload).encode()
        req = _req.Request(
            url, data=data,
            headers={"Content-Type": "application/json", "User-Agent": _USER_AGENT, **(headers or {})},
        )
        with _req.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())


# ═══════════════════════════════════════════════════════════════════════════════
# FAL Engine (fal.ai FLUX)
# ═══════════════════════════════════════════════════════════════════════════════

class FALEngine(ImageGenEngine):
    """FAL.ai FLUX modeli ile görsel üretir. FAL_KEY ortam değişkeni gerekli."""

    @property
    def ad(self) -> str:
        return "fal"

    def _bagimliliklari_kontrol_et(self) -> bool:
        api_key = os.environ.get("FAL_KEY", "").strip()
        if not api_key:
            api_key = os.environ.get("FAL_API_KEY", "").strip()
        return bool(api_key)

    def _get_fal_model_url(self) -> str:
        """FAL model URL'sini environment/config'dan belirle.

        Sıra: FAL_MODEL env > FAL_IMAGE_MODEL env > varsayılan flux-1-1-pro.
        """
        model = os.environ.get("FAL_MODEL", "").strip()
        if not model:
            model = os.environ.get("FAL_IMAGE_MODEL", "").strip()
        if model:
            return f"https://fal.run/{model.lstrip('/')}"
        return _FAL_RUN_URL

    def _get_fal_model_name(self) -> str:
        """Kullanılan model adını döndür (log/teşhis için)."""
        model = os.environ.get("FAL_MODEL", "").strip()
        if not model:
            model = os.environ.get("FAL_IMAGE_MODEL", "").strip()
        return model or "fal-ai/flux-1-1-pro"

    def calistir(self, prompt: str, en: str = "1024", boy: str = "1024") -> str:
        api_key = os.environ.get("FAL_KEY", "").strip()
        if not api_key:
            api_key = os.environ.get("FAL_API_KEY", "").strip()
        if not api_key:
            return "[RESIM_OLUSTUR/FAL] Hata: FAL_KEY tanimli degil."

        try:
            en_i, boy_i = int(en), int(boy)
        except (TypeError, ValueError):
            en_i, boy_i = 1024, 1024

        model_url = self._get_fal_model_url()
        model_name = self._get_fal_model_name()

        try:
            sonuc = self._http_post_json(
                model_url,
                {"prompt": prompt.strip(), "image_size": {"width": en_i, "height": boy_i}},
                headers={"Authorization": f"Key {api_key}"},
                timeout=90,
            )
            url = None
            if isinstance(sonuc.get("images"), list) and sonuc["images"]:
                url = sonuc["images"][0].get("url")
            elif isinstance(sonuc.get("image"), dict):
                url = sonuc["image"].get("url")
            elif isinstance(sonuc.get("image"), str):
                url = sonuc["image"]
            elif isinstance(sonuc.get("output"), dict):
                # FLUX.1 dev/general modellerde output dict icinde olabilir
                output = sonuc["output"]
                if isinstance(output, list) and output:
                    url = output[0] if isinstance(output[0], str) else None

            if not url:
                return f"[RESIM_OLUSTUR/FAL] Hata: beklenmeyen cevap: {json.dumps(sonuc)[:300]}"
            return self._media("image", url, f"Prompt: {prompt.strip()} [FAL: {model_name}]")

        except Exception as e:
            log.exception("[FALEngine] FAL API hatasi:")
            # urllib.error.HTTPError durumunda body'yi oku
            import urllib.error as _ue
            if hasattr(e, "read"):
                try:
                    govde = e.read().decode(errors="replace")[:300]
                    return f"[RESIM_OLUSTUR/FAL] HTTP hatasi: {govde}"
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )
            return f"[RESIM_OLUSTUR/FAL] Hata: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# OpenAI Engine (DALL-E)
# ═══════════════════════════════════════════════════════════════════════════════

class OpenAIEngine(ImageGenEngine):
    """OpenAI DALL-E ile görsel üretir. OPENAI_API_KEY ortam değişkeni gerekli."""

    @property
    def ad(self) -> str:
        return "openai"

    def _bagimliliklari_kontrol_et(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY", "").strip())

    def calistir(self, prompt: str, en: str = "1024", boy: str = "1024") -> str:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return "[RESIM_OLUSTUR/OpenAI] Hata: OPENAI_API_KEY tanimli degil."

        # OpenAI DALL-E 3 desteklenen boyutlar: "1024x1024", "1792x1024", "1024x1792"
        size = f"{en}x{boy}"
        valid_sizes = {"1024x1024", "1792x1024", "1024x1792"}
        if size not in valid_sizes:
            size = "1024x1024"

        try:
            sonuc = self._http_post_json(
                _OPENAI_IMAGE_URL,
                {
                    "model": "dall-e-3",
                    "prompt": prompt.strip(),
                    "n": 1,
                    "size": size,
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=90,
            )
            data = sonuc.get("data", [])
            if not data:
                return f"[RESIM_OLUSTUR/OpenAI] Hata: beklenmeyen cevap: {json.dumps(sonuc)[:300]}"
            url = data[0].get("url", "")
            if not url:
                return "[RESIM_OLUSTUR/OpenAI] Hata: URL bulunamadi."
            return self._media("image", url, f"Prompt: {prompt.strip()} [OpenAI DALL-E]")

        except Exception as e:
            log.exception("[OpenAIEngine] OpenAI API hatasi:")
            import urllib.error as _ue
            if hasattr(e, "read"):
                try:
                    govde = e.read().decode(errors="replace")[:300]
                    return f"[RESIM_OLUSTUR/OpenAI] HTTP hatasi: {govde}"
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )
            return f"[RESIM_OLUSTUR/OpenAI] Hata: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# xAI Engine (Stub / dummy)
# ═══════════════════════════════════════════════════════════════════════════════

class xAIEngine(ImageGenEngine):
    """xAI / Grok görsel üretim engine'i. XAI_API_KEY ortam değişkeni gerekli.

    xAI görsel üretim API'sini kullanır (OpenAI DALL-E ile benzer formatta).
    Endpoint: https://api.x.ai/v1/images/generations
    Model: grok-imagine-image (varsayılan) veya grok-imagine-image-quality
    Desteklenen boyutlar: 1024x1024, 1024x1792, 1792x1024
    """

    @property
    def ad(self) -> str:
        return "xai"

    def _bagimliliklari_kontrol_et(self) -> bool:
        return bool(os.environ.get("XAI_API_KEY", "").strip())

    def calistir(self, prompt: str, en: str = "1024", boy: str = "1024") -> str:
        api_key = os.environ.get("XAI_API_KEY", "").strip()
        if not api_key:
            return "[RESIM_OLUSTUR/xAI] Hata: XAI_API_KEY tanimli degil."

        # Desteklenen boyut: "1024x1024", "1024x1792", "1792x1024"
        size = f"{en}x{boy}"
        valid_sizes = {"1024x1024", "1792x1024", "1024x1792"}
        if size not in valid_sizes:
            size = "1024x1024"

        try:
            # xAI model — FAL_MODEL tarzi env ile model secimi destegi
            model = os.environ.get("XAI_MODEL", "").strip()
            if not model:
                model = os.environ.get("XAI_IMAGE_MODEL", "").strip()
            if not model:
                model = "grok-imagine-image"

            valid_models = {"grok-imagine-image", "grok-imagine-image-quality", "grok-2-image"}
            if model not in valid_models:
                model = "grok-imagine-image"

            sonuc = self._http_post_json(
                _XAI_IMAGE_URL,
                {
                    "model": model,
                    "prompt": prompt.strip(),
                    "n": 1,
                    "size": size,
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=90,
            )
            data = sonuc.get("data", [])
            if not data:
                return (
                    f"[RESIM_OLUSTUR/xAI] Hata: beklenmeyen cevap: "
                    f"{json.dumps(sonuc)[:300]}"
                )
            url = data[0].get("url", "")
            if not url:
                # xAI bazen farkli formatta donebilir (revised_prompt, b64_json vb.)
                b64 = data[0].get("b64_json", "")
                if b64:
                    return self._media(
                        "image_b64", b64,
                        f"Prompt: {prompt.strip()} [xAI Grok]",
                    )
                return "[RESIM_OLUSTUR/xAI] Hata: URL bulunamadi."
            return self._media("image", url, f"Prompt: {prompt.strip()} [xAI Grok]")

        except Exception as e:
            log.exception("[xAIEngine] xAI API hatasi:")
            import urllib.error as _ue
            if hasattr(e, "read"):
                try:
                    govde = e.read().decode(errors="replace")[:300]
                    return f"[RESIM_OLUSTUR/xAI] HTTP hatasi: {govde}"
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )
            return f"[RESIM_OLUSTUR/xAI] Hata: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# Stub Engine (local dummy / simüle)
# ═══════════════════════════════════════════════════════════════════════════════

class StubEngine(ImageGenEngine):
    """Local dummy engine. API key gerekmez. Görsel üretmez, simüle eder."""

    @property
    def ad(self) -> str:
        return "stub"

    def calistir(self, prompt: str, en: str = "1024", boy: str = "1024") -> str:
        return (
            f"[RESIM_OLUSTUR/Stub] Simule edilen gorsel uretimi.\n"
            f"  Prompt: {prompt.strip()}\n"
            f"  Boyut: {en}x{boy}\n"
            f"  (Stub engine: gorsel uretimi icin FAL_KEY, OPENAI_API_KEY veya XAI_API_KEY ayarlayin)"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Image Gen Registry
# ═══════════════════════════════════════════════════════════════════════════════

class ImageGenRegistry:
    """Görsel üretim engine'lerini kaydet, seç ve çalıştır."""

    def __init__(self) -> None:
        self._engines: dict[str, ImageGenEngine] = {}
        self._varsayilan: Optional[str] = None

    def kaydet(self, engine: ImageGenEngine) -> None:
        adi = engine.ad
        self._engines[adi] = engine
        # Varsayılan: FAL > OpenAI > xAI > stub
        if self._varsayilan is None:
            self._varsayilan = adi
        elif adi == "fal" and engine.hazir:
            self._varsayilan = adi
        elif adi == "openai" and engine.hazir and self._varsayilan != "fal":
            self._varsayilan = adi
        elif adi == "xai" and engine.hazir and self._varsayilan not in ("fal", "openai"):
            self._varsayilan = adi
        log.info("[ImageGenRegistry] Engine kaydedildi: %s (varsayilan: %s)", adi, self._varsayilan)

    def sec(self, ad: str) -> Optional[ImageGenEngine]:
        eng = self._engines.get(ad)
        if eng is None and self._varsayilan:
            log.warning("[ImageGenRegistry] '%s' bulunamadi, varsayilana dusuluyor: %s", ad, self._varsayilan)
            return self._engines.get(self._varsayilan)
        return eng

    @property
    def varsayilan(self) -> Optional[ImageGenEngine]:
        return self._engines.get(self._varsayilan) if self._varsayilan else None

    def calistir(self, engine_adi: str, prompt: str, en: str = "1024", boy: str = "1024") -> str:
        if not prompt or not prompt.strip():
            return "[RESIM_OLUSTUR] Hata: 'prompt' bos olamaz."
        eng = self.sec(engine_adi)
        if eng is None:
            return f"[RESIM_OLUSTUR] '{engine_adi}' engine'i bulunamadi."
        if not eng.hazir:
            return f"[RESIM_OLUSTUR] '{engine_adi}' hazir degil (API anahtari eksik)."
        try:
            return eng.calistir(prompt.strip(), en, boy)
        except Exception as e:
            log.exception("[ImageGenRegistry] '%s' calistirma hatasi:", engine_adi)
            return f"[RESIM_OLUSTUR] '{engine_adi}' hatasi: {e}"


# ── Global registry singleton ──────────────────────────────────────────────────

_registry: Optional[ImageGenRegistry] = None


def _get_registry() -> ImageGenRegistry:
    global _registry
    if _registry is None:
        _registry = ImageGenRegistry()
        # Stub her zaman çalışır
        _registry.kaydet(StubEngine())
        # FAL
        try:
            _registry.kaydet(FALEngine())
        except Exception as e:
            log.warning("[ImageGenRegistry] FALEngine yuklenemedi: %s", e)
        # OpenAI
        try:
            _registry.kaydet(OpenAIEngine())
        except Exception as e:
            log.warning("[ImageGenRegistry] OpenAIEngine yuklenemedi: %s", e)
        # xAI
        try:
            _registry.kaydet(xAIEngine())
        except Exception as e:
            log.warning("[ImageGenRegistry] xAIEngine yuklenemedi: %s", e)
    return _registry


# ═══════════════════════════════════════════════════════════════════════════════
# Tool Fonksiyonu
# ═══════════════════════════════════════════════════════════════════════════════

def resim_olustur(prompt: str, en: str = "1024", boy: str = "1024", backend: str = "") -> str:
    """RESIM_OLUSTUR tool'u — backend parametresi ile çoklu görsel üretim.

    Args:
        prompt: Gorsel tanimi.
        en: Genislik (piksel).
        boy: Yukseklik (piksel).
        backend: Kullanilacak engine adi (fal, openai, xai, stub).
                 Bos birakilirsa varsayilan kullanilir.

    Returns:
        [MEDIA] formatinda gorsel veya hata mesaji.
    """
    reg = _get_registry()
    engine_adi = backend.strip() if backend.strip() else ""
    if not engine_adi:
        # Varsayilan engine'i kullan
        eng = reg.varsayilan
        if eng is None:
            return "[RESIM_OLUSTUR] Hata: hicbir engine kayitli degil."
        engine_adi = eng.ad
    return reg.calistir(engine_adi, prompt, en, boy)


def image_gen_engine_listele() -> str:
    """Kayitli engine'leri listele."""
    reg = _get_registry()
    satirlar = ["[RESIM_OLUSTUR] Kayitli engine'ler:"]
    for ad, eng in reg._engines.items():
        durum = "hazir" if eng.hazir else "API anahtari eksik"
        isaret = " >" if ad == reg._varsayilan else "  "
        satirlar.append(f"  {isaret} {ad} ({durum})")
    return "\n".join(satirlar)


# ═══════════════════════════════════════════════════════════════════════════════
# Motor Kayit
# ═══════════════════════════════════════════════════════════════════════════════

def motor_kaydet(motor) -> None:
    """Motor tarafindan otomatik cagrilir. RESIM_OLUSTUR tool'unu kaydeder."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    try:
        motor._plugin_arac_kaydet(
            "RESIM_OLUSTUR",
            lambda ham="": _resim_olustur_ayristir_ve_calistir(ham),
            "Prompt'tan gorsel uretir (coklu back-end)."
            " Kullanim: RESIM_OLUSTUR(prompt=\"...\", en=\"1024\", boy=\"1024\", backend=\"fal|openai|xai|stub\")\n"
            "Varsayilan: FAL (FAL_KEY) > OpenAI (OPENAI_API_KEY) > xAI (XAI_API_KEY) > stub\n"
            "FAL: FAL_KEY ortam degiskeni gerekli.\n"
            "OpenAI: OPENAI_API_KEY gerekli.\n"
            "xAI: XAI_API_KEY gerekli (Grok-imagine-image ile gorsel uretir).\n"
            "Stub: API key gerekmez, simulasyon yapar.",
        )
        motor._plugin_arac_kaydet(
            "RESIM_OLUSTUR_BACKEND_LISTELE",
            lambda: image_gen_engine_listele(),
            "Kullanilabilir gorsel uretim engine'lerini listeler.",
        )
    except Exception as e:
        log.warning("[ImageGenEngine] Motor kayit hatasi: %s", e)


def _resim_olustur_ayristir_ve_calistir(ham: str) -> str:
    """RESIM_OLUSTUR(ham) -> parametre ayristir."""
    import re as _re
    prompt = ""
    en = "1024"
    boy = "1024"
    backend = ""

    p_match = _re.search(r'prompt\s*=\s*"([^"]*)"', ham)
    if p_match:
        prompt = p_match.group(1)

    e_match = _re.search(r'en\s*=\s*"([^"]*)"', ham)
    if e_match:
        en = e_match.group(1)

    b_match = _re.search(r'boy\s*=\s*"([^"]*)"', ham)
    if b_match:
        boy = b_match.group(1)

    bk_match = _re.search(r'backend\s*=\s*"([^"]*)"', ham)
    if bk_match:
        backend = bk_match.group(1)

    if not prompt:
        prompt = ham.strip().strip('"').strip("'")

    return resim_olustur(prompt, en, boy, backend)


# ═══════════════════════════════════════════════════════════════════════════════
# Test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(image_gen_engine_listele())
    print("\n--- Stub Test ---")
    print(resim_olustur("kedi", backend="stub"))
