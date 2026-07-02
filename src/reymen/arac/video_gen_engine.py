# -*- coding: utf-8 -*-
"""Video Generation Engine - ReYMeN video uretme motoru.

Desteklenen backends:
  1. moviepy (image+audio -> slideshow) - her zaman calisir
  2. FAL.ai AI video - API key varsa
  3. HyperFrames - kuruluysa
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

PROJE_KOKU = Path(__file__).resolve().parent.parent
VIDEO_CACHE = PROJE_KOKU / "video_cache"
VIDEO_CACHE.mkdir(parents=True, exist_ok=True)


# ── Engine Secimi ────────────────────────────────────────────────────────────

def _fal_mevcut() -> bool:
    """FAL.ai API key ve kutuphanesi var mi?"""
    try:
        import fal_client
        api_key = os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY") or ""
        return bool(api_key)
    except ImportError:
        return False


def _hyperframes_mevcut() -> bool:
    """HyperFrames kurulu mu?"""
    try:
        import hyperframes
        return True
    except ImportError:
        return False


# ── moviepy ile Slayt Gosterisi Videosu ──────────────────────────────────────

def _moviepy_slayt(
    resimler: list[str],
    ses_yolu: str = "",
    fps: int = 24,
    gecis_suresi: float = 2.0,
    cikti: str = "",
) -> str:
    """Resimlerden slayt gosterisi videosu olustur.

    Args:
        resimler: Resim dosya yollari.
        ses_yolu: Opsiyonel arka plan muzigi/ses dosyasi.
        fps: Kare hizi (varsayilan: 24).
        gecis_suresi: Her resim icin gosterim suresi (saniye).
        cikti: Cikti dosya yolu (bos=otomatik).

    Returns:
        Video dosyasi yolu.
    """
    try:
        from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
    except ImportError:
        # moviepy v1 fallback
        try:
            from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
        except ImportError:
            return "[HATA] moviepy kurulu degil."

    if not resimler:
        return "[HATA] En az bir resim gerekli."

    klipler = []
    for resim_yolu in resimler:
        if not os.path.exists(resim_yolu):
            logger.warning("[VideoGen] Resim bulunamadi: %s", resim_yolu)
            continue
        try:
            clip = ImageClip(resim_yolu, duration=gecis_suresi)
            klipler.append(clip)
        except Exception as e:
            logger.warning("[VideoGen] Resim eklenemedi: %s: %s", resim_yolu, e)

    if not klipler:
        return "[HATA] Hicbir resim eklenemedi."

    try:
        video = concatenate_videoclips(klipler, method="compose")

        # Ses ekle
        if ses_yolu and os.path.exists(ses_yolu):
            try:
                audio = AudioFileClip(ses_yolu)
                # Ses suresini video suresine gore ayarla
                if audio.duration > video.duration:
                    audio = audio.subclipped(0, video.duration)
                video = video.with_audio(audio)
            except Exception as e:
                logger.warning("[VideoGen] Ses eklenemedi: %s", e)

        # Cikti
        if not cikti:
            zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
            cikti = str(VIDEO_CACHE / f"slayt_{zaman}.mp4")

        video.write_videofile(
            cikti,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )

        video.close()
        for c in klipler:
            c.close()

        if os.path.exists(cikti) and os.path.getsize(cikti) > 0:
            logger.info("[VideoGen] Slayt videosu olusturuldu: %s (%d bytes)",
                         cikti, os.path.getsize(cikti))
            return cikti
        return "[HATA] Video dosyasi olusturulamadi."

    except Exception as e:
        logger.exception("[VideoGen] Slayt olusturma hatasi: %s", e)
        return f"[HATA] {type(e).__name__}: {e}"


# ── FAL.ai ile AI Video Uretimi ─────────────────────────────────────────────

def _fal_video(
    prompt: str,
    model: str = "fal-ai/runway-gen3/turbo",
    sure: int = 5,
    resim_yolu: str = "",
) -> str:
    """FAL.ai uzerinden AI video uret.

    Args:
        prompt: Video promptu.
        model: FAL model adi.
        sure: Video suresi (saniye).
        resim_yolu: Opsiyonel baslangic resmi (image-to-video).

    Returns:
        Video URL'si veya hata mesaji.
    """
    if not _fal_mevcut():
        return "[HATA] FAL API key bulunamadi."

    try:
        import fal_client

        # Prompt hazirla
        args = {"prompt": prompt}

        if resim_yolu and os.path.exists(resim_yolu):
            # Image-to-video
            import base64
            with open(resim_yolu, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            args["image_url"] = f"data:image/jpeg;base64,{img_b64}"

        # Model secimi
        if "stable-video" in model:
            args["video_length"] = sure
        elif "image-to-video" in model:
            args["duration"] = sure

        logger.info("[VideoGen] FAL video istegi: model=%s, prompt=%s", model, prompt[:50])

        # Async gonder
        sonuc = fal_client.subscribe(
            model,
            arguments=args,
        )

        video_url = ""
        if isinstance(sonuc, dict):
            video_url = sonuc.get("video", {}).get("url", "") or sonuc.get("output", {}).get("video_url", "")

        if video_url:
            logger.info("[VideoGen] FAL video uretildi: %s", video_url[:80])
            return video_url
        return f"[HATA] Video URL alinamadi: {str(sonuc)[:100]}"

    except ImportError:
        return "[HATA] fal_client kurulu degil."
    except Exception as e:
        logger.exception("[VideoGen] FAL video hatasi: %s", e)
        return f"[HATA] {type(e).__name__}: {e}"


# ── HyperFrames ile Video ────────────────────────────────────────────────────

def _hyperframes_video(html_kodu: str, cikti: str = "") -> str:
    """HyperFrames ile HTML'den video olustur.

    Args:
        html_kodu: HyperFrames HTML kodu (CSS animasyonlari).
        cikti: Cikti dosya yolu.

    Returns:
        Video dosyasi yolu.
    """
    if not _hyperframes_mevcut():
        return "[HATA] HyperFrames kurulu degil."

    try:
        import hyperframes

        if not cikti:
            zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
            cikti = str(VIDEO_CACHE / f"hyper_{zaman}.mp4")

        sonuc = hyperframes.render(html_kodu, output=cikti)
        if os.path.exists(cikti) and os.path.getsize(cikti) > 0:
            return cikti
        return f"[HATA] HyperFrames basarisiz: {sonuc}"

    except Exception as e:
        return f"[HATA] HyperFrames: {type(e).__name__}: {e}"


# ── Ana API ──────────────────────────────────────────────────────────────────

def video_uret(
    prompt: str = "",
    resimler: Optional[list[str]] = None,
    ses_yolu: str = "",
    sure: int = 5,
    model: str = "moviepy",
    cikti: str = "",
) -> str:
    """Video uret.

    Parametreler:
        prompt: Video promptu (AI video icin).
        resimler: Resim dosya yollari (slayt icin).
        ses_yolu: Opsiyonel ses dosyasi.
        sure: Video suresi (saniye).
        model: Video motoru (moviepy, fal, hyperframes).
        cikti: Cikti dosya yolu.

    Doner:
        Video dosyasi yolu veya URL.
    """
    if model == "fal":
        return _fal_video(prompt, sure=sure, resim_yolu=resimler[0] if resimler else "")

    elif model == "hyperframes":
        return _hyperframes_video(prompt, cikti=cikti)

    else:  # moviepy (varsayilan)
        return _moviepy_slayt(
            resimler or [],
            ses_yolu=ses_yolu,
            gecis_suresi=max(1.0, sure / max(1, len(resimler or [1]))),
            cikti=cikti,
        )


def video_durum() -> str:
    """Video gen sistem durumu."""
    satirlar = [
        "=== Video Generation Durumu ===",
        f"moviepy: {'✅' if _moviepy_mevcut() else '❌'}",
        f"FAL.ai: {'✅' if _fal_mevcut() else '❌'}",
        f"HyperFrames: {'✅' if _hyperframes_mevcut() else '❌'}",
        f"Video cache: {VIDEO_CACHE}",
    ]
    if VIDEO_CACHE.exists():
        vids = list(VIDEO_CACHE.glob("*.mp4"))
        satirlar.append(f"Onbellekteki videolar: {len(vids)}")
    return "\n".join(satirlar)


def _moviepy_mevcut() -> bool:
    try:
        import moviepy
        return True
    except ImportError:
        return False


# ── Motor Kayit ──────────────────────────────────────────────────────────────

def motor_kaydet(motor: Any) -> None:
    """Motor'a video gen araclaini kaydet."""

    def _video_uret(
        prompt: str = "",
        resimler: str = "",
        ses_yolu: str = "",
        sure: int = 5,
        model: str = "moviepy",
    ) -> str:
        """VIDEO_OLUSTUR: Video uret.

        Parametreler:
            prompt (str) — AI video promptu veya HyperFrames HTML kodu.
            resimler (str) — Virgulle ayrilmis resim yollari (slayt icin).
            ses_yolu (str) — Opsiyonel arka plan ses dosyasi.
            sure (int) — Video suresi (saniye, varsayilan: 5).
            model (str) — Video motoru: 'moviepy' (varsayilan), 'fal', 'hyperframes'.

        Doner: Video dosyasi yolu veya URL.
        """
        resim_list = [r.strip() for r in resimler.split(",") if r.strip()] if resimler else []
        return video_uret(prompt, resim_list, ses_yolu, sure, model)

    def _video_durum() -> str:
        """VIDEO_DURUM: Video gen sistem durumu."""
        return video_durum()

    def _video_test() -> str:
        """VIDEO_TEST: Video gen sistemini test et.

        Basit bir slayt videosu olusturur.
        """
        # Test resmi olarak PIL ile basit bir goruntu olustur
        import PIL.Image
        import PIL.ImageDraw

        img = PIL.Image.new("RGB", (640, 480), (30, 30, 50))
        draw = PIL.ImageDraw.Draw(img)
        draw.text((100, 200), "ReYMeN Video Test", fill=(255, 255, 255))
        test_img = VIDEO_CACHE / "test_frame.png"
        img.save(str(test_img))

        sonuc = _moviepy_slayt([str(test_img)], gecis_suresi=2.0)
        # Temizlik
        if test_img.exists():
            test_img.unlink()

        if os.path.exists(sonuc) and not sonuc.startswith("[HATA]"):
            return f"✅ Video test basarili: {sonuc}"
        return f"❌ Video test basarisiz: {sonuc}"

    if hasattr(motor, "_plugin_arac_kaydet"):
        motor._plugin_arac_kaydet("VIDEO_OLUSTUR", _video_uret,
            "Video uretir. Parametreler: prompt=str (AI prompt), "
            "resimler=str (virgulle ayrilmis resim yollari), "
            "ses_yolu=str (opsiyonel), sure=int (saniye), "
            "model=str (moviepy/fal/hyperframes). "
            "Doner: video dosyasi yolu veya URL.")
        motor._plugin_arac_kaydet("VIDEO_DURUM", _video_durum,
            "Video gen sistem durumu: moviepy/FAL/HyperFrames durumu.")
        motor._plugin_arac_kaydet("VIDEO_TEST", _video_test,
            "Video gen sistemini test eder. Basit bir slayt videosu olusturur.")

        logger.info("[VideoGen] Motor araclari kaydedildi: VIDEO_OLUSTUR, VIDEO_DURUM, VIDEO_TEST")


if __name__ == "__main__":
    print(video_durum())
    print(video_uret("Test", ["test.png"] if os.path.exists("test.png") else []))
