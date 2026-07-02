# -*- coding: utf-8 -*-
"""
hyperframes_tool.py — HyperFrames Video Generation.

HTML + CSS + JS animasyonlarını, Playwright ile frame-frame render edip
FFmpeg ile video'ya birleştiren sistem.

3 temel template:
  - METIN_ANIMASYONU:  metin yazma / fade-in / scale efekti
  - GECIS_EFFEKTI:     slide / fade / zoom geçişleri
  - GRAFIK_ANIMASYONU: bar / çizgi grafiği animasyonu

Kullanım:
    from reymen.tools.hyperframes_tool import hyperframes_olustur
    sonuc = hyperframes_olustur(
        template="METIN_ANIMASYONU",
        params={"metin": "Merhaba Dünya!", "arkaplan": "#1a1a2e"},
        cikti="output.mp4",
        fps=30,
        sure=5,
    )

Bağımlılıklar:
    pip install playwright pillow numpy
    playwright install chromium
    ffmpeg sistemde kurulu olmalı
"""

import base64
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# ── Sabitler ─────────────────────────────────────────────────────────────
COKLU_VIDEO_KLASORU = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "hyperframes_output"
)
os.makedirs(COKLU_VIDEO_KLASORU, exist_ok=True)

# ── HTML Template Şablonları ─────────────────────────────────────────────


def _template_metin_animasyonu(params: dict) -> str:
    """
    Metin animasyonu template.
    Parametreler:
      - metin (str): gösterilecek metin
      - alt_metin (str, ops.): alt başlık
      - yazi_rengi (str, ops.): metin rengi (varsayılan: #ffffff)
      - arkaplan (str, ops.): arkaplan rengi/gradient (varsayılan: #1a1a2e)
      - font_boyut (int, ops.): ana font boyutu (varsayılan: 48)
      - efekt (str, ops.): fade | typewriter | scale | slide-up (varsayılan: fade)
      - arkaplan_resim (str, ops.): base64 veya URL arkaplan resmi
    """
    metin = params.get("metin", "HyperFrame")
    alt_metin = params.get("alt_metin", "")
    yazi_rengi = params.get("yazi_rengi", "#ffffff")
    arkaplan = params.get("arkaplan", "#1a1a2e")
    font_boyut = params.get("font_boyut", 48)
    efekt = params.get("efekt", "fade")
    arkaplan_resim = params.get("arkaplan_resim", "")

    # CSS animasyonları
    efekt_css = {
        "fade": """
            @keyframes animasyon {
                0% { opacity: 0; }
                100% { opacity: 1; }
            }
        """,
        "typewriter": """
            @keyframes animasyon {
                0% { width: 0; }
                100% { width: 100%; }
            }
        """,
        "scale": """
            @keyframes animasyon {
                0% { transform: scale(0.3); opacity: 0; }
                100% { transform: scale(1); opacity: 1; }
            }
        """,
        "slide-up": """
            @keyframes animasyon {
                0% { transform: translateY(50px); opacity: 0; }
                100% { transform: translateY(0); opacity: 1; }
            }
        """,
    }

    if efekt not in efekt_css:
        efekt = "fade"

    anim_css = efekt_css[efekt]
    typewriter_extra = ""
    if efekt == "typewriter":
        typewriter_extra = """
            .anim-metin {
                display: inline-block;
                overflow: hidden;
                white-space: nowrap;
                border-right: 3px solid %s;
                animation: animasyon 2s steps(30) forwards;
            }
        """ % yazi_rengi
    else:
        typewriter_extra = f"""
            .anim-metin {{
                animation: animasyon 1.5s ease-out forwards;
            }}
        """

    arkaplan_stil = f"background: {arkaplan};"
    if arkaplan_resim:
        if arkaplan_resim.startswith("data:"):
            arkaplan_stil = (
                f"background-image: url('{arkaplan_resim}'); "
                f"background-size: cover; background-position: center;"
            )
        elif arkaplan_resim.startswith(("http://", "https://")):
            arkaplan_stil = (
                f"background-image: url('{arkaplan_resim}'); "
                f"background-size: cover; background-position: center;"
            )

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1920px; height: 1080px;
    display: flex; flex-direction: column;
    justify-content: center; align-items: center;
    font-family: 'Segoe UI', Arial, sans-serif;
    {arkaplan_stil}
    overflow: hidden;
  }}
  {anim_css}
  {typewriter_extra}
  .alt-metin {{
    font-size: 24px; color: {yazi_rengi}; opacity: 0.7;
    margin-top: 20px;
    animation: animasyon 2s ease-out 0.5s both;
  }}
</style>
</head>
<body>
  <div class="anim-metin" style="font-size:{font_boyut}px; color:{yazi_rengi}; font-weight:bold; text-align:center; max-width:90%;">
    {metin}
  </div>
  {"<div class='alt-metin'>" + alt_metin + "</div>" if alt_metin else ""}
</body>
</html>"""


def _template_gecis_efekti(params: dict) -> str:
    """
    Geçiş efekti template.
    Parametreler:
      - onceki_metin (str): ilk kare metni
      - sonraki_metin (str): son kare metni
      - arkaplan (str, ops.): arkaplan rengi (varsayılan: #16213e)
      - yazi_rengi (str, ops.): metin rengi (varsayılan: #e94560)
      - gecis_tipi (str, ops.): slide-left | slide-right | fade | zoom | wipe (varsayılan: slide-left)
      - hiz (float, ops.): geçiş hızı (0.5-3, varsayılan: 1)
    """
    onceki = params.get("onceki_metin", "Önceki")
    sonraki = params.get("sonraki_metin", "Sonraki")
    arkaplan = params.get("arkaplan", "#16213e")
    yazi_rengi = params.get("yazi_rengi", "#e94560")
    gecis_tipi = params.get("gecis_tipi", "slide-left")
    hiz = float(params.get("hiz", 1))

    if gecis_tipi == "slide-left":
        gecis_css = """
            @keyframes onceki-anim {
                0% { transform: translateX(0); opacity: 1; }
                100% { transform: translateX(-100%); opacity: 0; }
            }
            @keyframes sonraki-anim {
                0% { transform: translateX(100%); opacity: 0; }
                100% { transform: translateX(0); opacity: 1; }
            }
        """
    elif gecis_tipi == "slide-right":
        gecis_css = """
            @keyframes onceki-anim {
                0% { transform: translateX(0); opacity: 1; }
                100% { transform: translateX(100%); opacity: 0; }
            }
            @keyframes sonraki-anim {
                0% { transform: translateX(-100%); opacity: 0; }
                100% { transform: translateX(0); opacity: 1; }
            }
        """
    elif gecis_tipi == "zoom":
        gecis_css = """
            @keyframes onceki-anim {
                0% { transform: scale(1); opacity: 1; }
                100% { transform: scale(1.5); opacity: 0; }
            }
            @keyframes sonraki-anim {
                0% { transform: scale(0.5); opacity: 0; }
                100% { transform: scale(1); opacity: 1; }
            }
        """
    elif gecis_tipi == "wipe":
        gecis_css = """
            @keyframes onceki-anim {
                0% { clip-path: inset(0 0 0 0); }
                100% { clip-path: inset(0 100% 0 0); }
            }
            @keyframes sonraki-anim {
                0% { clip-path: inset(0 0 0 100%); }
                100% { clip-path: inset(0 0 0 0); }
            }
        """
    else:  # fade
        gecis_css = """
            @keyframes onceki-anim {
                0% { opacity: 1; }
                100% { opacity: 0; }
            }
            @keyframes sonraki-anim {
                0% { opacity: 0; }
                100% { opacity: 1; }
            }
        """

    sure = 2.0 / max(hiz, 0.5)

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1920px; height: 1080px;
    display: flex; justify-content: center; align-items: center;
    font-family: 'Segoe UI', Arial, sans-serif;
    background: {arkaplan};
    color: {yazi_rengi};
    font-size: 48px; font-weight: bold;
    overflow: hidden;
    position: relative;
  }}
  .kare {{
    position: absolute;
    width: 100%; height: 100%;
    display: flex; justify-content: center; align-items: center;
  }}
  .onceki-kare {{
    animation: onceki-anim {sure}s ease-in-out forwards;
  }}
  .sonraki-kare {{
    animation: sonraki-anim {sure}s ease-in-out forwards;
  }}
  {gecis_css}
</style>
</head>
<body>
  <div class="kare onceki-kare">{onceki}</div>
  <div class="kare sonraki-kare">{sonraki}</div>
</body>
</html>"""


def _template_grafik_animasyonu(params: dict) -> str:
    """
    Bar/çizgi grafiği animasyonu template.
    Parametreler:
      - baslik (str): grafik başlığı
      - veri (list): [{"etiket": "...", "deger": sayi}, ...]
      - grafik_tipi (str): bar | horizontal-bar | line (varsayılan: bar)
      - renkler (list, ops.): renk listesi (hex)
      - arkaplan (str, ops.): arkaplan (varsayılan: #0f3460)
      - baslik_rengi (str, ops.): başlık rengi (varsayılan: #ffffff)
    """
    baslik = params.get("baslik", "Grafik")
    veri = params.get("veri", [
        {"etiket": "A", "deger": 80},
        {"etiket": "B", "deger": 60},
        {"etiket": "C", "deger": 90},
        {"etiket": "D", "deger": 45},
        {"etiket": "E", "deger": 70},
    ])
    grafik_tipi = params.get("grafik_tipi", "bar")
    varsayilan_renkler = ["#e94560", "#0f3460", "#533483", "#1a1a2e", "#16213e",
                          "#ff6b6b", "#48dbfb", "#ff9ff3", "#54a0ff", "#5f27cd"]
    renkler = params.get("renkler", varsayilan_renkler)
    arkaplan = params.get("arkaplan", "#0f3460")
    baslik_rengi = params.get("baslik_rengi", "#ffffff")

    max_deger = max((d.get("deger", 0) for d in veri), default=100)

    if grafik_tipi == "horizontal-bar":
        # Yatay bar
        bar_css_items = ""
        for i, d in enumerate(veri):
            etiket = d.get("etiket", f"Item {i+1}")
            deger = d.get("deger", 0)
            yuzde = (deger / max_deger) * 100 if max_deger > 0 else 0
            renk = renkler[i % len(renkler)]
            bar_css_items += f"""
            <div class="bar-satir">
                <div class="bar-etiket">{etiket}</div>
                <div class="bar-kapsayici">
                    <div class="bar-dolu" style="width:0%; background:{renk};"
                         data-genislik="{yuzde}">{deger}</div>
                </div>
            </div>
            """
        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1920px; height: 1080px;
    display: flex; flex-direction: column; align-items: center;
    font-family: 'Segoe UI', Arial, sans-serif;
    background: {arkaplan};
    padding: 60px;
    overflow: hidden;
  }}
  h1 {{ color: {baslik_rengi}; margin-bottom: 50px; font-size: 42px; }}
  .grafik-alani {{
    width: 100%; max-width: 1600px;
    display: flex; flex-direction: column; gap: 20px;
  }}
  .bar-satir {{
    display: flex; align-items: center; gap: 20px;
  }}
  .bar-etiket {{
    color: {baslik_rengi}; font-size: 22px; font-weight: bold;
    width: 120px; text-align: right;
  }}
  .bar-kapsayici {{
    flex: 1; height: 50px;
    background: rgba(255,255,255,0.1);
    border-radius: 8px; overflow: hidden;
    position: relative;
  }}
  .bar-dolu {{
    height: 100%;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: flex-end;
    padding-right: 15px;
    color: white; font-weight: bold; font-size: 18px;
    transition: width 2s ease-out;
  }}
</style>
</head>
<body>
  <h1>{baslik}</h1>
  <div class="grafik-alani">
    {bar_css_items}
  </div>
  <script>
    setTimeout(function() {{
      document.querySelectorAll('.bar-dolu').forEach(function(el) {{
        el.style.width = el.dataset.genislik + '%';
      }});
    }}, 100);
  </script>
</body>
</html>"""
    elif grafik_tipi == "line":
        # Çizgi grafiği — canvas kullan
        noktalar = [(i, d.get("deger", 0)) for i, d in enumerate(veri)]
        px = 150  # padding x
        py = 100  # padding y
        w, h = 1600, 700
        if len(noktalar) > 1:
            x_step = (w - 2 * px) / (len(noktalar) - 1)
            y_range = max_deger - 0 if max_deger > 0 else 1
            nokta_str = " ".join(
                f"{(px + i * x_step):.1f},{(h - py - ((d / y_range) * (h - 2 * py))):.1f}"
                for i, (_, d) in enumerate(noktalar)
            )
        else:
            nokta_str = f"{w/2},{h/2}"

        etiket_satirlari = "\n".join(
            f"<text x='{px + i * x_step if len(veri) > 1 else w/2}' y='{h - py + 40}' "
            f"text-anchor='middle' fill='{baslik_rengi}' font-size='18'>{d.get('etiket', '')}</text>"
            for i, d in enumerate(veri)
        )
        deger_satirlari_lines = []
        for i, d in enumerate(veri):
            deger = d.get("deger", 0)
            x_pos = px + i * x_step if len(veri) > 1 else w / 2
            y_pos = (h - py - ((deger / max_deger) * (h - 2 * py))) - 15
            renk = renkler[i % len(renkler)]
            deger_satirlari_lines.append(
                f"<text x='{x_pos}' y='{y_pos}' "
                f"text-anchor='middle' fill='{renk}' "
                f"font-size='20' font-weight='bold'>{deger}</text>"
            )
        deger_satirlari = "\n".join(deger_satirlari_lines)

        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1920px; height: 1080px;
    display: flex; flex-direction: column; align-items: center;
    font-family: 'Segoe UI', Arial, sans-serif;
    background: {arkaplan};
    padding: 60px;
    overflow: hidden;
  }}
  h1 {{ color: {baslik_rengi}; margin-bottom: 30px; font-size: 42px; }}
  svg {{ width: 100%; max-width: 1700px; }}
  .cizgi {{
    stroke-dasharray: 2000;
    stroke-dashoffset: 2000;
    animation: ciz 2s ease-out forwards;
  }}
  @keyframes ciz {{
    to {{ stroke-dashoffset: 0; }}
  }}
  .nokta {{
    opacity: 0;
    animation: nokta-gor 0.3s ease-out 2s forwards;
  }}
  @keyframes nokta-gor {{
    to {{ opacity: 1; }}
  }}
</style>
</head>
<body>
  <h1>{baslik}</h1>
  <svg viewBox="0 0 {w} {h}">
    <polyline class="cizgi" points="{nokta_str}"
              fill="none" stroke="{renkler[0]}" stroke-width="4" stroke-linecap="round"/>
    {deger_satirlari}
    {etiket_satirlari}
  </svg>
</body>
</html>"""
    else:
        # Dikey bar (varsayılan)
        bar_sayisi = len(veri)
        bar_genislik = min(120, int(1400 / max(bar_sayisi, 1)))
        toplam_genislik = bar_sayisi * (bar_genislik + 40)
        baslangic_x = max(50, int((1600 - toplam_genislik) / 2))

        bars = ""
        for i, d in enumerate(veri):
            etiket = d.get("etiket", f"Item {i+1}")
            deger = d.get("deger", 0)
            yuzde = (deger / max_deger) * 100 if max_deger > 0 else 0
            yukseklik = (deger / max_deger) * 600 if max_deger > 0 else 0
            renk = renkler[i % len(renkler)]
            x = baslangic_x + i * (bar_genislik + 40)
            bars += f"""
            <div class="bar-kapsayici" style="left:{x}px;">
                <div class="bar-deger">{deger}</div>
                <div class="bar" style="width:{bar_genislik}px; height:0px; background:{renk};"
                     data-yukseklik="{yukseklik}"></div>
                <div class="bar-etiket">{etiket}</div>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1920px; height: 1080px;
    display: flex; flex-direction: column; align-items: center;
    font-family: 'Segoe UI', Arial, sans-serif;
    background: {arkaplan};
    padding: 60px;
    overflow: hidden;
  }}
  h1 {{ color: {baslik_rengi}; margin-bottom: 40px; font-size: 42px; }}
  .grafik-alani {{
    position: relative;
    width: 1600px; height: 700px;
    display: flex; justify-content: flex-start; align-items: flex-end;
  }}
  .bar-kapsayici {{
    position: absolute;
    bottom: 0;
    display: flex; flex-direction: column;
    align-items: center;
  }}
  .bar {{
    border-radius: 6px 6px 0 0;
    transition: height 2s ease-out;
    min-width: 40px;
  }}
  .bar-deger {{
    color: {baslik_rengi}; font-size: 18px; font-weight: bold;
    margin-bottom: 5px;
  }}
  .bar-etiket {{
    color: {baslik_rengi}; font-size: 18px; margin-top: 10px;
    opacity: 0.8;
  }}
</style>
</head>
<body>
  <h1>{baslik}</h1>
  <div class="grafik-alani">
    {bars}
  </div>
  <script>
    setTimeout(function() {{
      document.querySelectorAll('.bar').forEach(function(el) {{
        el.style.height = el.dataset.yukseklik + 'px';
      }});
    }}, 100);
  </script>
</body>
</html>"""


# ── Template seçici ──────────────────────────────────────────────────────

_TEMPLATELER = {
    "METIN_ANIMASYONU": _template_metin_animasyonu,
    "GECIS_EFFEKTI": _template_gecis_efekti,
    "GRAFIK_ANIMASYONU": _template_grafik_animasyonu,
}


def html_olustur(template: str, params: dict) -> str:
    """Verilen template ve parametrelerle HTML çıktısı üretir."""
    template = template.upper().strip()
    if template not in _TEMPLATELER:
        raise ValueError(
            f"Bilinmeyen template: {template}. "
            f"Seçenekler: {', '.join(_TEMPLATELER.keys())}"
        )
    return _TEMPLATELER[template](params)


def template_listele() -> str:
    """Mevcut template'leri listeler."""
    satirlar = ["Mevcut HyperFrame Template'leri:", ""]
    for ad, fn in _TEMPLATELER.items():
        doc = getattr(fn, "__doc__", "") or ""
        ilk_satir = doc.strip().split("\n")[0] if doc else ""
        satirlar.append(f"  {ad:20s} — {ilk_satir}")
    satirlar.append("")
    satirlar.append(f"Toplam {len(_TEMPLATELER)} template.")
    return "\n".join(satirlar)


# ── Playwright Render Motoru ─────────────────────────────────────────────


def _frame_klasoru_olustur() -> str:
    """Geçici frame klasörü oluştur."""
    frame_dir = os.path.join(
        tempfile.gettempdir(),
        f"hyperframes_{uuid.uuid4().hex[:12]}"
    )
    os.makedirs(frame_dir, exist_ok=True)
    return frame_dir


def _html_render_playwright(
    html: str,
    cikti_resim: str,
    genislik: int = 1920,
    yukseklik: int = 1080,
) -> bool:
    """Playwright ile HTML render et → PNG screenshot al."""
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        logger.error("[HyperFrames] Playwright yuklu degil.")
        return False

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-gpu", "--disable-software-rasterizer"],
                )
                context = browser.new_context(
                    viewport={"width": genislik, "height": yukseklik},
                    device_scale_factor=1,
                )
                page = context.new_page()

                # HTML içeriğini data URL ile yükle
                page.goto(f"data:text/html;base64,{base64.b64encode(html.encode()).decode()}")
                page.wait_for_load_state("networkidle")

                # JS animasyonlarının başlaması için bekle
                time.sleep(0.5)

                page.screenshot(path=cikti_resim, full_page=False)
                browser.close()
                return os.path.exists(cikti_resim)
            except Exception as e:
                logger.error(f"[HyperFrames] Playwright render hatasi: {e}")
                return False
    except Exception as e:
        logger.error(f"[HyperFrames] Playwright baslatma hatasi: {e}")
        return False


def _frame_uretici(
    html: str,
    frame_dir: str,
    fps: int = 30,
    sure: float = 5.0,
    genislik: int = 1920,
    yukseklik: int = 1080,
) -> List[str]:
    """
    HTML sayfasını Playwright ile açıp belirtilen süre boyunca
    frame'leri PNG olarak kaydeder.

    JS animasyonlarının akışını yakalamak için:
    - Her frame'de sayfanın screenshot'ı alınır
    - requestAnimationFrame benzeri bir mantıkla belirli aralıklarla
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("[HyperFrames] Playwright yuklu degil.")
        return []

    toplam_frame = int(fps * sure)
    frame_araligi = 1.0 / fps
    frame_dosyalari = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu", "--disable-software-rasterizer"],
            )
            context = browser.new_context(
                viewport={"width": genislik, "height": yukseklik},
                device_scale_factor=1,
            )
            page = context.new_page()

            page.goto(f"data:text/html;base64,{base64.b64encode(html.encode()).decode()}")
            page.wait_for_load_state("networkidle")
            time.sleep(0.3)

            for i in range(toplam_frame):
                frame_yolu = os.path.join(frame_dir, f"frame_{i:06d}.png")
                page.screenshot(path=frame_yolu, full_page=False)
                frame_dosyalari.append(frame_yolu)

                # Bir sonraki frame'e geçmeden önce bekle
                if i < toplam_frame - 1:
                    time.sleep(frame_araligi)

            browser.close()
    except Exception as e:
        logger.error(f"[HyperFrames] Frame uretimi hatasi: {e}")
        return frame_dosyalari

    return frame_dosyalari


def _ffmpeg_video_birlestir(
    frame_dir: str,
    cikti: str,
    fps: int = 30,
) -> bool:
    """
    Frame'leri ffmpeg ile video'ya birleştir.
    """
    if not os.path.isdir(frame_dir):
        return False

    # Frame'lerin varlığını kontrol et
    frame_pattern = os.path.join(frame_dir, "frame_%06d.png")
    ilk_frame = os.path.join(frame_dir, "frame_000000.png")
    if not os.path.exists(ilk_frame):
        logger.error(f"[HyperFrames] Ilk frame bulunamadi: {ilk_frame}")
        return False

    os.makedirs(os.path.dirname(os.path.abspath(cikti)) if os.path.dirname(cikti) else ".", exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", frame_pattern,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "18",
        "-vf", f"scale={1920}:{1080}:force_original_aspect_ratio=decrease,pad={1920}:{1080}:(ow-iw)/2:(oh-ih)/2",
        cikti,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            logger.error(f"[HyperFrames] FFmpeg hatasi: {result.stderr[:500]}")
            return False
        return os.path.exists(cikti) and os.path.getsize(cikti) > 0
    except subprocess.TimeoutExpired:
        logger.error("[HyperFrames] FFmpeg zaman asimi (5 dk)")
        return False
    except FileNotFoundError:
        logger.error("[HyperFrames] ffmpeg sistemde bulunamadi")
        return False
    except Exception as e:
        logger.error(f"[HyperFrames] FFmpeg bilinmeyen hata: {e}")
        return False


# ── Birleştirme (Audio + Subtitle) ────────────────────────────────────────


def _audio_ekle(video_yolu: str, audio_yolu: str, cikti: Optional[str] = None) -> str:
    """Video'ya ses ekle. cikti yoksa mevcut video'nun üzerine yazar."""
    if cikti is None:
        cikti = video_yolu.replace(".mp4", "_sesli.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_yolu,
        "-i", audio_yolu,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        cikti,
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)
        return cikti
    except Exception as e:
        logger.warning(f"[HyperFrames] Ses ekleme hatasi: {e}")
        return video_yolu


# ── Ana API ────────────────────────────────────────────────────────────────


def hyperframes_olustur(
    template: str = "METIN_ANIMASYONU",
    params: Optional[dict] = None,
    cikti: Optional[str] = None,
    fps: int = 30,
    sure: float = 5.0,
    genislik: int = 1920,
    yukseklik: int = 1080,
    ses_yolu: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ana HyperFrames video oluşturma fonksiyonu.

    Args:
        template: Template adı (METIN_ANIMASYONU, GECIS_EFFEKTI, GRAFIK_ANIMASYONU)
        params: Template parametreleri (dict)
        cikti: Çıktı video yolu (None=otomatik)
        fps: Saniyedeki frame sayısı
        sure: Video süresi (saniye)
        genislik: Video genişliği (px)
        yukseklik: Video yüksekliği (px)
        ses_yolu: Eklenecek ses dosyası (opsiyonel)

    Returns:
        {"basarili": bool, "cikti": str, "hata": str, "frame_sayisi": int}
    """
    if params is None:
        params = {}

    try:
        # 1. HTML oluştur
        logger.debug(f"[HyperFrames] HTML olusturuluyor: {template}")
        html = html_olustur(template, params)

        # 2. Çıktı yolunu belirle
        if cikti is None:
            cikti = os.path.join(
                COKLU_VIDEO_KLASORU,
                f"hyperframe_{template.lower()}_{int(time.time())}.mp4"
            )
        os.makedirs(os.path.dirname(os.path.abspath(cikti)), exist_ok=True)

        # 3. Frame'leri oluştur
        frame_dir = _frame_klasoru_olustur()
        logger.debug(f"[HyperFrames] Frame'ler uretiliyor: {frame_dir}")

        frame_dosyalari = _frame_uretici(
            html=html,
            frame_dir=frame_dir,
            fps=fps,
            sure=sure,
            genislik=genislik,
            yukseklik=yukseklik,
        )

        frame_sayisi = len(frame_dosyalari)
        if frame_sayisi < 2:
            hata = "Yeterli frame uretilemedi"
            logger.error(f"[HyperFrames] {hata}")
            return {
                "basarili": False,
                "cikti": "",
                "hata": hata,
                "frame_sayisi": frame_sayisi,
            }

        # 4. FFmpeg ile video'ya birleştir
        logger.debug(f"[HyperFrames] Frame'ler video'ya birlestiriliyor: {cikti}")
        basarili = _ffmpeg_video_birlestir(
            frame_dir=frame_dir,
            cikti=cikti,
            fps=fps,
        )

        if not basarili:
            hata = "FFmpeg video birlestirme basarisiz"
            logger.error(f"[HyperFrames] {hata}")
            return {
                "basarili": False,
                "cikti": "",
                "hata": hata,
                "frame_sayisi": frame_sayisi,
            }

        # 5. Ses ekle (opsiyonel)
        if ses_yolu and os.path.exists(ses_yolu):
            logger.debug(f"[HyperFrames] Ses ekleniyor: {ses_yolu}")
            cikti = _audio_ekle(cikti, ses_yolu)

        # 6. Geçici frame klasörünü temizle
        try:
            shutil.rmtree(frame_dir, ignore_errors=True)
        except Exception:
            pass

        logger.info(f"[HyperFrames] Video basariyla olusturuldu: {cikti}")
        return {
            "basarili": True,
            "cikti": cikti,
            "hata": "",
            "frame_sayisi": frame_sayisi,
        }

    except ValueError as e:
        logger.error(f"[HyperFrames] Parametre hatasi: {e}")
        return {"basarili": False, "cikti": "", "hata": str(e), "frame_sayisi": 0}
    except Exception as e:
        logger.error(f"[HyperFrames] Beklenmeyen hata: {e}")
        return {"basarili": False, "cikti": "", "hata": str(e), "frame_sayisi": 0}


def hyperframes_hizli_metin(
    metin: str,
    alt_metin: str = "",
    cikti: Optional[str] = None,
    efekt: str = "fade",
    sure: float = 4.0,
    arkaplan: str = "#1a1a2e",
    yazi_rengi: str = "#ffffff",
) -> Dict[str, Any]:
    """Hızlı metin videosu oluştur."""
    return hyperframes_olustur(
        template="METIN_ANIMASYONU",
        params={
            "metin": metin,
            "alt_metin": alt_metin,
            "efekt": efekt,
            "arkaplan": arkaplan,
            "yazi_rengi": yazi_rengi,
        },
        cikti=cikti,
        sure=sure,
    )


def hyperframes_hizli_grafik(
    baslik: str,
    veri: list,
    grafik_tipi: str = "bar",
    cikti: Optional[str] = None,
    sure: float = 5.0,
) -> Dict[str, Any]:
    """Hızlı grafik videosu oluştur."""
    return hyperframes_olustur(
        template="GRAFIK_ANIMASYONU",
        params={
            "baslik": baslik,
            "veri": veri,
            "grafik_tipi": grafik_tipi,
        },
        cikti=cikti,
        sure=sure,
    )


def hyperframes_hizli_gecis(
    onceki_metin: str,
    sonraki_metin: str,
    gecis_tipi: str = "slide-left",
    cikti: Optional[str] = None,
    sure: float = 3.0,
) -> Dict[str, Any]:
    """Hızlı geçiş videosu oluştur."""
    return hyperframes_olustur(
        template="GECIS_EFFEKTI",
        params={
            "onceki_metin": onceki_metin,
            "sonraki_metin": sonraki_metin,
            "gecis_tipi": gecis_tipi,
        },
        cikti=cikti,
        sure=sure,
    )


# ── Motor Kayıt ──────────────────────────────────────────────────────────


def motor_kaydet(motor) -> None:
    """Motor'a HyperFrames araçlarını kaydet."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return

    k = lambda ad, fonk, aciklama="": motor._plugin_arac_kaydet(ad, fonk, aciklama)

    def hyperframes_video(ham: str) -> str:
        """
        HYPERFRAMES_VIDEO template,param_json,cikti_yolu
        HTML+CSS+JS animasyonu videosu oluşturur.
        Parametreler: template (METIN_ANIMASYONU|GECIS_EFFEKTI|GRAFIK_ANIMASYONU),
                       param_json (JSON string),
                       cikti_yolu (opsiyonel, .mp4)
        """
        import json
        params = ham.strip().split(",", 2)
        template = "METIN_ANIMASYONU"
        param_dict = {}
        cikti = None

        if len(params) >= 1 and params[0].strip():
            template = params[0].strip().upper()

        if len(params) >= 2 and params[1].strip():
            try:
                param_dict = json.loads(params[1].strip())
            except json.JSONDecodeError:
                return f"[HyperFrames] Hata: param_json gecersiz JSON: {params[1][:100]}"

        if len(params) >= 3 and params[2].strip():
            cikti = params[2].strip()

        sonuc = hyperframes_olustur(
            template=template,
            params=param_dict,
            cikti=cikti,
        )

        if sonuc["basarili"]:
            return (
                f"[HyperFrames] Video basariyla olusturuldu!\\n"
                f"  Çıktı: {sonuc['cikti']}\\n"
                f"  Frame sayısı: {sonuc['frame_sayisi']}\\n"
                f"  Template: {template}\\n"
                f"  Dosyayı göndermek için: [MEDIA:file=\"{sonuc['cikti']}\"]"
            )
        else:
            return f"[HyperFrames] Hata: {sonuc['hata']}"

    def hyperframes_template_list(ham: str) -> str:
        """HYPERFRAMES_TEMPLATES: mevcut template'leri listeler"""
        return template_listele()

    def hyperframes_hizli_metin_arac(ham: str) -> str:
        """
        HYPERFRAMES_METIN metin,alt_metin,efekt,sure
        Hızlı metin animasyonu.
        Parametreler: metin, alt_metin (ops.), efekt (fade|typewriter|scale|slide-up), sure (sn, ops.)
        """
        parts = [p.strip() for p in ham.split(",", 3)]
        metin = parts[0] if len(parts) > 0 else "HyperFrame"
        alt_metin = parts[1] if len(parts) > 1 else ""
        efekt = parts[2] if len(parts) > 2 else "fade"
        try:
            sure = float(parts[3]) if len(parts) > 3 else 4.0
        except ValueError:
            sure = 4.0

        sonuc = hyperframes_hizli_metin(
            metin=metin, alt_metin=alt_metin, efekt=efekt, sure=sure
        )
        if sonuc["basarili"]:
            return (
                f"[HyperFrames] Metin videosu hazır!\\n"
                f"  Çıktı: {sonuc['cikti']}\\n"
                f"  [MEDIA:file=\"{sonuc['cikti']}\"]"
            )
        return f"[HyperFrames] Hata: {sonuc['hata']}"

    def hyperframes_hizli_grafik_arac(ham: str) -> str:
        """
        HYPERFRAMES_GRAFIK baslik,grafik_tipi,veri_json
        Hızlı grafik animasyonu.
        Parametreler: baslik, grafik_tipi (bar|horizontal-bar|line),
                       veri_json (JSON array of {etiket, deger})
        """
        parts = [p.strip() for p in ham.split(",", 2)]
        baslik = parts[0] if len(parts) > 0 else "Grafik"
        grafik_tipi = parts[1] if len(parts) > 1 else "bar"
        veri = [{"etiket": "A", "deger": 80}, {"etiket": "B", "deger": 60}]
        if len(parts) > 2:
            try:
                import json
                veri = json.loads(parts[2])
            except json.JSONDecodeError:
                pass

        sonuc = hyperframes_hizli_grafik(
            baslik=baslik, veri=veri, grafik_tipi=grafik_tipi
        )
        if sonuc["basarili"]:
            return (
                f"[HyperFrames] Grafik videosu hazır!\\n"
                f"  Çıktı: {sonuc['cikti']}\\n"
                f"  [MEDIA:file=\"{sonuc['cikti']}\"]"
            )
        return f"[HyperFrames] Hata: {sonuc['hata']}"

    k("HYPERFRAMES_VIDEO", hyperframes_video,
      "HTML+CSS+JS animasyon videosu oluşturur. Parametreler: template, param_json (JSON), cikti_yolu (ops.)")
    k("HYPERFRAMES_TEMPLATES", hyperframes_template_list,
      "Mevcut HyperFrame template'lerini listeler.")
    k("HYPERFRAMES_METIN", hyperframes_hizli_metin_arac,
      "Hızlı metin animasyonu. Parametreler: metin, alt_metin, efekt (fade|typewriter|scale|slide-up), sure")
    k("HYPERFRAMES_GRAFIK", hyperframes_hizli_grafik_arac,
      "Hızlı grafik animasyonu. Parametreler: baslik, grafik_tipi (bar|horizontal-bar|line), veri_json (JSON)")

    print("[HyperFrames] 4 arac kayit edildi.")
    logger.info("[HyperFrames] 4 arac motor'a kaydedildi.")


# ── Test / Demo ──────────────────────────────────────────────────────────


def demo():
    """Tüm template'leri demo video olarak oluştur."""
    print("=== HyperFrames Demo ===")

    # 1. Metin animasyonu
    print("\n1/3: Metin animasyonu...")
    r1 = hyperframes_hizli_metin(
        "ReYMeN AI Agent",
        alt_metin="HyperFrames Video Motoru",
        efekt="scale",
        sure=4.0,
    )
    print(f"   Sonuc: {'BASARILI' if r1['basarili'] else 'HATA: ' + r1['hata']}")
    if r1["basarili"]:
        print(f"   Dosya: {r1['cikti']}")

    # 2. Geçiş efekti
    print("\n2/3: Gecis efekti...")
    r2 = hyperframes_hizli_gecis(
        "Önceki Sürüm",
        "Yeni Sürüm",
        gecis_tipi="slide-left",
        sure=3.0,
    )
    print(f"   Sonuc: {'BASARILI' if r2['basarili'] else 'HATA: ' + r2['hata']}")
    if r2["basarili"]:
        print(f"   Dosya: {r2['cikti']}")

    # 3. Grafik animasyonu
    print("\n3/3: Grafik animasyonu...")
    r3 = hyperframes_hizli_grafik(
        "Aylık Performans",
        veri=[
            {"etiket": "Ocak", "deger": 85},
            {"etiket": "Şubat", "deger": 92},
            {"etiket": "Mart", "deger": 78},
            {"etiket": "Nisan", "deger": 95},
            {"etiket": "Mayıs", "deger": 88},
        ],
        grafik_tipi="bar",
        sure=5.0,
    )
    print(f"   Sonuc: {'BASARILI' if r3['basarili'] else 'HATA: ' + r3['hata']}")
    if r3["basarili"]:
        print(f"   Dosya: {r3['cikti']}")

    print("\n=== Demo tamamlandı ===")


if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        demo()
    else:
        print(template_listele())
