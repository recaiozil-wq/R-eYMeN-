# -*- coding: utf-8 -*-
"""
marketplace.py — ReYMeN Plugin Marketplacesi.

Plugin katalogu + uzaktan yukleme + arama + yayinlama.
Mevcut plugin_manager.py uzerine insa edilmistir.

Kullanim (motor):
    PLUGIN_MARKET_LISTE()         → katalogdaki tum pluginler
    PLUGIN_MARKET_ARAMA( sorgu ) → katalogda ara
    PLUGIN_MARKET_YUKLE( ad )    → plugin'i katalogdan indir + yukle
    PLUGIN_MARKET_BILGI( ad )    → plugin detayi
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Varsayilan katalog kaynagi ──────────────────────────────────────────
# GitHub'daki plugin katalog repomuz
KATALOG_URL = "https://raw.githubusercontent.com/Watcher-ReYMeN/ReYMeN-Ajan-v2/main/plugin_katalog.json"

# Yerel katalog yolu (cache)
KATALOG_DOSYASI = Path(__file__).resolve().parent / "plugin_katalog.json"

# Plugin yukleme dizini
PLUGIN_DIZINI = Path(__file__).resolve().parent / "plugins"


def _katalog_yukle() -> list[dict]:
    """Katalog JSON'unu yukle (once yerel, sonra uzak)."""
    # 1. Yerel cache dene
    if KATALOG_DOSYASI.exists():
        try:
            with open(KATALOG_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Yerel katalog okunamadi: %s", e)

    # 2. Uzaktan indir
    try:
        req = urllib.request.Request(
            KATALOG_URL,
            headers={"User-Agent": "ReYMeN-Marketplace/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            veri = json.loads(r.read().decode("utf-8"))
            # Cache'e kaydet
            with open(KATALOG_DOSYASI, "w", encoding="utf-8") as f:
                json.dump(veri, f, indent=2, ensure_ascii=False)
            return veri
    except Exception as e:
        logger.error("Uzak katalog yuklenemedi: %s", e)
        return []


def liste() -> str:
    """Katalogdaki tum pluginleri listele."""
    plugins = _katalog_yukle()
    if not plugins:
        return "❌ Katalog bos veya yuklenemedi."

    satirlar = ["📦 ReYMeN Plugin Katalogu", "=" * 50, ""]
    for p in plugins:
        ad = p.get("ad", "?")
        versiyon = p.get("versiyon", "?")
        aciklama = p.get("aciklama", "")[:80]
        yazar = p.get("yazar", "?")
        satirlar.append(f"  📌 {ad} v{versiyon}")
        satirlar.append(f"     {aciklama}")
        yuklu = "(YUKLU)" if _yuklu_mi(ad) else ""
        satirlar.append(f"     Yazar: {yazar}  {yuklu}")
        satirlar.append("")

    satirlar.append(f"Toplam: {len(plugins)} plugin")
    return "\n".join(satirlar)


def ara(sorgu: str) -> str:
    """Katalogda isme/aciklamaya gore ara."""
    plugins = _katalog_yukle()
    if not plugins:
        return "❌ Katalog bos."

    sorgu = sorgu.lower().strip()
    sonuc = []
    for p in plugins:
        ad = p.get("ad", "").lower()
        aciklama = p.get("aciklama", "").lower()
        etiketler = " ".join(p.get("etiketler", [])).lower()
        if sorgu in ad or sorgu in aciklama or sorgu in etiketler:
            sonuc.append(p)

    if not sonuc:
        return f"🔍 \"{sorgu}\" icin sonuc bulunamadi."

    satirlar = [f"🔍 \"{sorgu}\" icin {len(sonuc)} sonuc:", ""]
    for p in sonuc:
        yuklu = "✅" if _yuklu_mi(p.get("ad", "")) else "⬇️"
        satirlar.append(f"  {yuklu} {p['ad']} v{p.get('versiyon', '?')} — {p.get('aciklama', '')[:70]}")
    return "\n".join(satirlar)


def bilgi(ad: str) -> str:
    """Plugin detayini goster."""
    plugins = _katalog_yukle()
    p = None
    for x in plugins:
        if x.get("ad", "").lower() == ad.lower():
            p = x
            break
    if not p:
        return f"❌ \"{ad}\" katalogda bulunamadi."

    yuklu = "✅ Evet" if _yuklu_mi(ad) else "❌ Hayir"
    satirlar = [
        f"📌 {p['ad']} v{p.get('versiyon', '?')}",
        f"   Yazar: {p.get('yazar', '?')}",
        f"   Lisans: {p.get('lisans', '?')}",
        f"   Yuklu: {yuklu}",
        f"   Aciklama: {p.get('aciklama', '?')}",
        "",
        "   Bagimliliklar:",
    ]
    for dep in p.get("bagimliliklar", []):
        satirlar.append(f"     • {dep}")
    satirlar.append("")
    satirlar.append(f"   Kaynak: {p.get('kaynak', '?')}")
    satirlar.append(f"   Dokuman: {p.get('dokuman', '?')}")
    return "\n".join(satirlar)


def yukle(ad: str) -> str:
    """Plugin'i katalogdan indir ve yukle."""
    plugins = _katalog_yukle()
    p = None
    for x in plugins:
        if x.get("ad", "").lower() == ad.lower():
            p = x
            break
    if not p:
        return f"❌ \"{ad}\" katalogda bulunamadi."

    if _yuklu_mi(ad):
        return f"ℹ️ \"{ad}\" zaten yuklu."

    kaynak = p.get("kaynak", "")
    if not kaynak:
        return f"❌ \"{ad}\" icin kaynak URL belirtilmemis."

    hedef = PLUGIN_DIZINI / ad
    try:
        hedef.mkdir(parents=True, exist_ok=True)

        if kaynak.startswith("http"):
            # URL'den indir
            zip_url = kaynak
            with tempfile.TemporaryDirectory() as tmp:
                zip_yol = Path(tmp) / "plugin.zip"
                urllib.request.urlretrieve(zip_url, zip_yol)
                shutil.unpack_archive(str(zip_yol), str(hedef), "zip")
        elif kaynak.startswith("git:"):
            # Git'ten clone
            git_url = kaynak[4:]
            subprocess.run(
                ["git", "clone", git_url, str(hedef)],
                check=True, capture_output=True, timeout=60
            )
        elif kaynak.startswith("file:"):
            # Yerel dosyadan kopyala
            yerel = Path(kaynak[5:])
            if yerel.exists():
                shutil.copytree(str(yerel), str(hedef), dirs_exist_ok=True)
            else:
                return f"❌ Yerel kaynak bulunamadi: {yerel}"
        else:
            return f"❌ Bilinmeyen kaynak formati: {kaynak}"

        # plugin.yaml olustur (yoksa)
        yaml_yol = hedef / "plugin.yaml"
        if not yaml_yol.exists():
            _varsayilan_yaml_olustur(hedef, p)

        # Motor'a yeniden yukle
        _motora_kaydet(ad)

        return f"✅ \"{ad}\" basariyla yuklendi ve aktif."
    except Exception as e:
        logger.error("Plugin yukleme hatasi: %s", e)
        # Temizlik
        if hedef.exists():
            shutil.rmtree(str(hedef), ignore_errors=True)
        return f"❌ Yukleme basarisiz: {e}"


def paylas(ad: str, kaynak: str, aciklama: str = "", yazar: str = "") -> str:
    """Yerel bir plugin'i katalog icin paketle.

    Katalog JSON'una yeni bir girdi ekler.
    """
    plugin_yolu = PLUGIN_DIZINI / ad
    if not plugin_yolu.exists():
        return f"❌ \"{ad}\" plugin dizini bulunamadi."

    plugins = _katalog_yukle()
    for p in plugins:
        if p.get("ad", "").lower() == ad.lower():
            return f"ℹ️ \"{ad}\" zaten katalogda."

    # plugin.yaml'dan bilgi al
    yaml_yol = plugin_yolu / "plugin.yaml"
    versiyon = "1.0.0"
    if yaml_yol.exists():
        try:
            import yaml
            with open(yaml_yol, "r", encoding="utf-8") as f:
                yaml_veri = yaml.safe_load(f)
            versiyon = yaml_veri.get("version", "1.0.0")
            if not aciklama:
                aciklama = yaml_veri.get("description", "")
            if not yazar:
                yazar = yaml_veri.get("author", "")
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )

    yeni = {
        "ad": ad,
        "versiyon": versiyon,
        "aciklama": aciklama or "aciklama yok",
        "yazar": yazar or "bilinmiyor",
        "kaynak": kaynak,
        "lisans": "MIT",
        "etiketler": ["plugin"],
        "bagimliliklar": [],
        "dokuman": ""
    }
    plugins.append(yeni)

    with open(KATALOG_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(plugins, f, indent=2, ensure_ascii=False)

    return f"✅ \"{ad}\" katalog'a eklendi. Katalog JSON: {KATALOG_DOSYASI}"


# ── Yardimci fonksiyonlar ──────────────────────────────────────────────

def _yuklu_mi(ad: str) -> bool:
    """Plugin yerel dizinde var mi kontrol et."""
    return (PLUGIN_DIZINI / ad).exists()


def _varsayilan_yaml_olustur(dizin: Path, p: dict) -> None:
    """Plugin icin varsayilan plugin.yaml olustur."""
    yaml_icerik = f"""# plugin.yaml — {p.get('ad', '?')}
name: "{p.get('ad', '?')}"
version: "{p.get('versiyon', '1.0.0')}"
description: "{p.get('aciklama', '')}"
author: "{p.get('yazar', 'bilinmiyor')}"
license: "{p.get('lisans', 'MIT')}"
enabled: true
type: tool
"""
    with open(dizin / "plugin.yaml", "w", encoding="utf-8") as f:
        f.write(yaml_icerik)


def _motora_kaydet(ad: str) -> None:
    """Motor'a plugin yeniden yukleme sinyali gonder.

    Dogrudan motor'a erisemiyorsak, hot_reload modulune devredelim.
    """
    try:
        from reymen.sistem.hot_reload import HotReloader
        # HotReloader sinifi import edilebiliyorsa, bir sonraki
        # turda algilanacak. Simdilik sadece log.
        logger.info("[Marketplace] Plugin '%s' yuklendi, hot-reload bekliyor.", ad)
    except ImportError:
        logger.warning("[Marketplace] HotReloader yok, elle yeniden baslatma gerekebilir.")


# ── Motor tool'lari ────────────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    """Motor tarafindan otomatik cagrilir."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    try:
        motor._plugin_arac_kaydet(
            "PLUGIN_MARKET_LISTE",
            lambda: liste(),
            "ReYMeN Plugin Katalogu: tum mevcut pluginleri listeler."
        )
        motor._plugin_arac_kaydet(
            "PLUGIN_MARKET_ARAMA",
            lambda sorgu="": ara(sorgu),
            "Katalogda plugin ara. Kullanim: PLUGIN_MARKET_ARAMA(sorgu)"
        )
        motor._plugin_arac_kaydet(
            "PLUGIN_MARKET_YUKLE",
            lambda ad="": yukle(ad),
            "Plugin'i katalogdan indir ve yukle. Kullanim: PLUGIN_MARKET_YUKLE(ad)"
        )
        motor._plugin_arac_kaydet(
            "PLUGIN_MARKET_BILGI",
            lambda ad="": bilgi(ad),
            "Plugin detayini goster. Kullanim: PLUGIN_MARKET_BILGI(ad)"
        )
        logger.info("[Marketplace] 4 tool kaydedildi.")
    except Exception as e:
        logger.warning("[Marketplace] Motor kayit hatasi: %s", e)


# ── CLI (dogrudan calistirma) ──────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Kullanim: marketplace.py [liste|ara|yukle|bilgi|paylas] [args]")
        sys.exit(1)

    komut = sys.argv[1]
    if komut == "liste":
        print(liste())
    elif komut == "ara" and len(sys.argv) > 2:
        print(ara(sys.argv[2]))
    elif komut == "yukle" and len(sys.argv) > 2:
        print(yukle(sys.argv[2]))
    elif komut == "bilgi" and len(sys.argv) > 2:
        print(bilgi(sys.argv[2]))
    elif komut == "paylas" and len(sys.argv) > 3:
        print(paylas(sys.argv[2], sys.argv[3]))
    else:
        print("Gecersiz komut.")
