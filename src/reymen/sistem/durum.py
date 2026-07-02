# -*- coding: utf-8 -*-
"""
durum.py — ReYMeN merkezi durum dosyasi (durum.json) okuyucu.

Herkesin kullandigi tek context dosyasi.
Motor tarafindan yuklenir, DURUM tool'unu kaydeder.

Kullanim (CLI):
    reymen durum          → ozet
    reymen durum detay    → detayli
    reymen durum json     → ham JSON

Kullanim (motor):
    DURUM_OKU()           → ozet
    DURUM_OKU(detay=1)    → detayli
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Proje kokunu bul ────────────────────────────────────────────────────

PROJE_KOK: Path = Path(__file__).resolve().parent.parent.parent
DURUM_DOSYASI: Path = PROJE_KOK / "durum.json"


def _durum_yolu_bul() -> Path:
    """durum.json dosyasini bul (once .ReYMeN/, sonra kok)."""
    adaylar = [
        PROJE_KOK / ".ReYMeN" / "durum.json",
        PROJE_KOK / "durum.json",
    ]
    for aday in adaylar:
        if aday.exists():
            return aday
    return adaylar[0]


def _yukle() -> dict[str, Any]:
    """durum.json dosyasini okuyup dict olarak dondur."""
    if not DURUM_DOSYASI.exists():
        # Fallback: .ReYMeN/ altinda dene
        reymen_yol = PROJE_KOK / ".ReYMeN" / "durum.json"
        if reymen_yol.exists():
            return json.loads(reymen_yol.read_text(encoding="utf-8"))
        return {"hata": f"durum.json bulunamadi: {DURUM_DOSYASI}"}
    try:
        with open(DURUM_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error("durum.json JSON hatasi: %s", e)
        return {"hata": f"durum.json bozuk JSON: {e}"}
    except Exception as e:
        logger.error("durum.json okuma hatasi: %s", e)
        return {"hata": str(e)}


def _ozet(veri: dict[str, Any]) -> str:
    """Insan okunabilir ozet rapor."""
    satirlar: list[str] = []
    satirlar.append("=" * 50)
    satirlar.append(f"  ReYMeN Durum Raporu")
    satirlar.append(f"  Son Guncelleme: {veri.get('son_guncelleme', '?')}")
    satirlar.append(f"  Guncelleyen:    {veri.get('guncelleyen_bot', '?')}")
    satirlar.append("=" * 50)
    satirlar.append("")

    top = veri.get("toplam_ozellik", 0)
    tam = veri.get("tamam", 0)
    islenen = veri.get("isleniyor", 0)
    satirlar.append(f"📊 Toplam: {top}  |  ✅ Tamam: {tam}  |  ⏳ Isleniyor: {islenen}")
    satirlar.append("")

    # 1. Cozulen 8 (onceki)
    coz8 = veri.get("cozulen_8_onceki", {})
    satirlar.append(f"📋 Cozulen 8 — {coz8.get('tamam', 0)}/{coz8.get('toplam', 0)} tamam")
    for ad, oz in coz8.get("maddeler", {}).items():
        emoji = "✅"
        satirlar.append(f"  {emoji} {ad.replace('_', ' ')}: {oz.get('detay', '')[:80]}")

    # 2. Cozulen 10 (ikinci dalga)
    coz10 = veri.get("cozulen_10_ikinci_dalga", {})
    satirlar.append(f"\n📋 Cozulen 10 — {coz10.get('tamam', 0)}/{coz10.get('toplam', 0)} tamam")
    for ad, oz in coz10.get("maddeler", {}).items():
        emoji = "✅"
        oncelik = oz.get("oncelik", "?")
        satirlar.append(f"  {emoji} [{oncelik}] {ad.replace('_', ' ')}: {oz.get('detay', '')[:80]}")

    # 3. Cozulen 4 (kismen cozulmus)
    coz4 = veri.get("cozulen_4_kismen", {})
    satirlar.append(f"\n📋 Cozulen 4 — {coz4.get('tamam', 0)}/{coz4.get('toplam', 0)} tamam")
    for ad, oz in coz4.get("maddeler", {}).items():
        emoji = "✅"
        oncelik = oz.get("oncelik", "?")
        satirlar.append(f"  {emoji} [{oncelik}] {ad.replace('_', ' ')}: {oz.get('detay', '')[:80]}")

    # 4. Mevcut Eksikler (canli liste)
    eksikler = veri.get("mevcut_eksikler", {})
    if isinstance(eksikler, dict):
        satirlar.append(f"\n📋 Mevcut Eksikler — {eksikler.get('tamam', 0)}/{eksikler.get('toplam', 0)} tamam")
        for ad, oz in eksikler.get("maddeler", {}).items():
            durum = oz.get("durum", "eksik")
            oncelik = oz.get("oncelik", "?")
            coz = "⏳" if oz.get("cozuluyor") else ""
            if durum == "tamam":
                emoji = "✅"
            elif durum == "kismen":
                emoji = "🔶"
            elif durum == "stub":
                emoji = "📦"
            else:
                emoji = "❌"
            satirlar.append(f"  {emoji}{coz}[{oncelik}] {ad.replace('_', ' ')}: {oz.get('detay', '')[:80]}")
    elif isinstance(eksikler, list) and eksikler:
        satirlar.append(f"\n📋 Mevcut Eksikler ({len(eksikler)}):")
        for m in eksikler:
            satirlar.append(f"  • {str(m)[:100]}")

    # Diger cozulenler
    diger = veri.get("cozulen_diger", {})
    md = diger.get("maddeler", [])
    if md:
        satirlar.append(f"\n🔧 Diger Cozulenler ({len(md)}):")
        for m in md[:8]:
            satirlar.append(f"  • {m[:100]}")

    # Uyari
    if veri.get("_meta", {}).get("bot_yanlis_liste_var"):
        satirlar.append(f"\n⚠️ NOT: Bot'un listesi guncel degil. DURUM_OKU() ile canli veri alinir.")

    # ReYMeN karsilastirmasi (ana kaynak)
    ReYMeN = veri.get("ReYMeN_karsilastirma")
    if ReYMeN:
        satirlar.append(f"\n📊 ReYMeN > ReYMeN Karsilastirmasi:")
        satirlar.append(f"   Toplam: {ReYMeN.get('toplam_ozellik', 0)} ozellik")
        satirlar.append(f"   Tamam: {ReYMeN.get('tamam', 0)} | Eksik: {ReYMeN.get('eksik', 0)}")
        satirlar.append(f"   {ReYMeN.get('aciklama', '')[:100]}")
        detay = ReYMeN.get("detaylar", {})
        for ad, oz in detay.items():
            if isinstance(oz, dict) and "durum" in oz:
                dur = "✅" if oz["durum"] == "tamam" else ("🔶" if oz["durum"] == "kismen" else "❌")
                satirlar.append(f"  {dur} {ad}: {oz.get('not', '')[:80]}")

    # Pasa_38 karsilastirmasi (varsa)
    pasa = veri.get("pasa_38_karsilastirmasi")
    if pasa:
        satirlar.append(f"\n📊 Pasa_38 Karsilastirmasi — {pasa.get('aciklama', '')[:80]}")
        satirlar.append(f"   Seviye: {veri.get('tahmini_seviye', '?')}")
        for m in pasa.get("maddeler", []):
            dur = {"evet": "✅", "kismen": "🔶", "hayir": "❌"}.get(m.get("cozuldu_mu", ""), "❓")
            satirlar.append(f"  {dur} {m.get('eksik', '?')}: ReYMeN={m.get('ReYMeN', '?')}")

    # YENI FORMAT: ozellikler objesi (23 ozellik, hermes>reymen karsilastirma)
    # Sadece eski anahtarlar yoksa calisir
    ozellikler = veri.get("ozellikler")
    if ozellikler and not veri.get("cozulen_8_onceki"):
        satirlar.append(f"\n📋 Ozellikler ({len(ozellikler)}):")
        for ad, oz in ozellikler.items():
            dur = oz.get("durum", "?")
            emoji = "✅" if dur == "tamam" else ("🔶" if dur == "kismen" else "❌")
            satirlar.append(f"  {emoji} {ad}: {oz.get('detay', '')[:100]}")
        # Aktif ajanlar
        ajanlar = veri.get("aktif_ajanlar", {})
        if ajanlar:
            satirlar.append(f"\n🤖 Aktif Botlar ({len(ajanlar)}):")
            for ad, oz in ajanlar.items():
                satirlar.append(f"  ● {ad}: {oz.get('profil', '?')} ({oz.get('provider', '?')})")

    return "\n".join(satirlar)


def _detayli(veri: dict[str, Any]) -> str:
    """Detayli JSON bilgisi duzgun formatta."""
    satirlar: list[str] = []
    satirlar.append(json.dumps(veri, indent=2, ensure_ascii=False))
    return "\n".join(satirlar)


# ── Ortak Degisiklik Kaydi ────────────────────────────────────────────

_DEGISIKLIK_DOSYASI: Path = PROJE_KOK / "durum.json"


def degisiklik_ekle(bot_adi: str, degisiklik: str, kategori: str = "genel") -> None:
    """Ortak degisiklik kaydina yeni bir girdi ekler.

    Args:
        bot_adi: Degisikligi yapan bot/agent adi
        degisiklik: Yapilan degisiklik aciklamasi
        kategori: Kategori (yetki/config/kod/entegrasyon vb.)
    """
    try:
        veri = _yukle()
        kayitlar = veri.setdefault("degisiklikler", [])
        yeni_kayit = {
            "zaman": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
            "bot": bot_adi,
            "kategori": kategori,
            "degisiklik": degisiklik,
        }
        kayitlar.insert(0, yeni_kayit)  # En yeni en ustte
        # Maks 50 kayit tut
        if len(kayitlar) > 50:
            kayitlar[:] = kayitlar[:50]
        veri["son_guncelleme"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
        veri["guncelleyen_bot"] = bot_adi
        with open(DURUM_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(veri, f, indent=2, ensure_ascii=False)
    except Exception as _e:
        logger.warning("[degisiklik_ekle] Hata: %s", _e)


def _son_degisiklikler(adet: int = 5) -> str:
    """Son N degisikligi metin olarak dondur."""
    try:
        veri = _yukle()
        kayitlar = veri.get("degisiklikler", [])
        if not kayitlar:
            return "Henuz degisiklik kaydi yok."
        satirlar = [f"Son {min(adet, len(kayitlar))} degisiklik:"]
        for k in kayitlar[:adet]:
            satirlar.append(f"  [{k['zaman']}] {k['bot']} ({k['kategori']}): {k['degisiklik'][:100]}")
        return "\n".join(satirlar)
    except Exception as _e:
        return f"[degisiklik] Hata: {_e}"


# ── Tool API ────────────────────────────────────────────────────────────

def durum_oku(detay: str = "0") -> str:
    """Merkezi durum.json dosyasini okur.

    Args:
        detay: "0" = ozet, "1" = detayli JSON, "json" = ham JSON

    Returns:
        Formatli durum raporu.
    """
    veri = _yukle()
    if detay in ("1", "detay", "detayli"):
        return _detayli(veri)
    elif detay in ("json", "raw", "ham"):
        return json.dumps(veri, indent=2, ensure_ascii=False)
    else:
        return _ozet(veri)


# ── Motor kayit ─────────────────────────────────────────────────────────

def motor_kaydet(motor) -> None:
    """Motor tarafindan otomatik cagrilir."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    try:
        motor._plugin_arac_kaydet(
            "DURUM_OKU",
            lambda ham="0": durum_oku(ham.strip() or "0"),
            "ReYMeN merkezi durum raporu. "
            "Kullanim: DURUM_OKU() → ozet, DURUM_OKU(detay=1) → detayli, DURUM_OKU(json) → ham JSON"
        )
        motor._plugin_arac_kaydet(
            "DURUM_DEGISIKLIK",
            lambda bot="", degisiklik="", kategori="genel": (
                degisiklik_ekle(bot, degisiklik, kategori) if bot and degisiklik
                else _son_degisiklikler()
            ),
            "Degisiklik kaydi. Kullanim: DURUM_DEGISIKLIK(bot='pasa_38', degisiklik='...')"
        )
        logger.info("[Durum] DURUM_OKU tool'u kaydedildi. Durum: %s", DURUM_DOSYASI)
    except Exception as e:
        logger.warning("[Durum] Motor kayit hatasi: %s", e)


# ── CLI (dogrudan calistirma) ───────────────────────────────────────────

if __name__ == "__main__":
    import sys
    detay = sys.argv[1] if len(sys.argv) > 1 else "0"
    print(durum_oku(detay))
