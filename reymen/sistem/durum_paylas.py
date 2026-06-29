# -*- coding: utf-8 -*-
"""
durum_paylas.py — Botlar Arası Paylaşımlı Durum Sistemi.

Tüm botların (R>eYMeN_¥, Kral_38, Paşa_38 vb.) aynı
durum.json dosyasını okuyup yazmasını sağlar. Böylece
her bot güncel proje durumunu görür.

Kullanım:
    from reymen.sistem.durum_paylas import durum_oku, durum_guncelle

    # Durumu oku
    durum = durum_oku()

    # Durumu güncelle
    durum_guncelle(bot_adi="Kral_38", ozellik="provider_sistemi", durum="tamam")

    # CLI: python -m reymen.sistem.durum_paylas --oku
    # CLI: python -m reymen.sistem.durum_paylas --guncelle --bot Kral_38 --ozellik provider_sistemi --durum tamam
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import logging
logger = logging.getLogger(__name__)

# ── Sabitler ──────────────────────────────────────────────────────────────────

# durum.json proje kökünde — tüm botlar erişebilir
# Ortak yol: her bot aynı proje dizininden çalışıyorsa
_PROJE_KOKU = Path(__file__).resolve().parent.parent.parent  # reymen/sistem/ -> reymen/ -> proje/
_DURUM_DOSYASI = _PROJE_KOKU / "durum.json"

# Varsayılan durum şablonu (dosya yoksa kullanılır)
VARSAYILAN_DURUM: Dict[str, Any] = {
    "proje": "ReYMeN Ajan",
    "surum": datetime.now().strftime("%Y-%m-%d"),
    "son_guncelleme": "",
    "guncelleyen_bot": "",
    "ozellikler": {},
    "aktif_ajanlar": {},
    "toplam_ozellik": 0,
    "tamam": 0,
    "isleniyor": 0,
}


# ── Ana Fonksiyonlar ───────────────────────────────────────────────────────────

def _kilitle():
    """Basit dosya kilidi — aynı anda yazma çakışmasını önler."""
    kilit_dosyasi = _DURUM_DOSYASI.with_suffix(".json.lock")
    max_bekle = 5  # saniye
    baslangic = time.monotonic()
    while time.monotonic() - baslangic < max_bekle:
        try:
            fd = os.open(str(kilit_dosyasi), os.O_CREAT | os.O_EXCL)
            os.close(fd)
            return True
        except FileExistsError:
            time.sleep(0.1)
    logger.warning(f"Kilit alınamadı (>{max_bekle}s): {kilit_dosyasi}")
    return False


def _kilidi_ac():
    """Dosya kilidini kaldır."""
    kilit_dosyasi = _DURUM_DOSYASI.with_suffix(".json.lock")
    try:
        kilit_dosyasi.unlink()
    except FileNotFoundError:
        pass


def durum_oku() -> Dict[str, Any]:
    """durum.json dosyasını oku.

    Returns:
        Durum sözlüğü. Dosya yoksa varsayılan şablon döner.
    """
    if not _DURUM_DOSYASI.exists():
        return dict(VARSAYILAN_DURUM)

    try:
        with open(_DURUM_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"durum.json okunamadı: {e}")
        return dict(VARSAYILAN_DURUM)


def durum_yaz(durum: Dict[str, Any], bot_adi: str = ""):
    """durum.json dosyasına yaz.

    Args:
        durum: Yazılacak durum sözlüğü
        bot_adi: Güncelleyen bot adı (opsiyonel)
    """
    durum["son_guncelleme"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    if bot_adi:
        durum["guncelleyen_bot"] = bot_adi

    kilitli = _kilitle()
    try:
        with open(_DURUM_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(durum, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error(f"durum.json yazılamadı: {e}")
    finally:
        if kilitli:
            _kilidi_ac()


def durum_guncelle(
    bot_adi: str,
    ozellik: str,
    durum: str,
    detay: str = "",
    dosyalar: Optional[List[str]] = None,
    aktif_ajan: bool = False,
) -> Dict[str, Any]:
    """Tek bir özellik durumunu güncelle.

    Args:
        bot_adi: Güncelleyen bot adı (örn: "R>eYMeN_¥", "Kral_38")
        ozellik: Özellik adı (örn: "provider_sistemi")
        durum: Yeni durum ("tamam", "isleniyor", "eksik")
        detay: Açıklama (opsiyonel)
        dosyalar: İlgili dosya listesi (opsiyonel)
        aktif_ajan: True ise aktif_ajanlar listesine ekle

    Returns:
        Güncellenmiş durum sözlüğü
    """
    mevcut = durum_oku()

    # Özellik bilgilerini güncelle
    mevcut.setdefault("ozellikler", {})
    guncel = mevcut["ozellikler"].get(ozellik, {})
    guncel["durum"] = durum
    guncel["son_guncelleme"] = datetime.now().strftime("%H:%M")
    guncel["guncelleyen"] = bot_adi
    if detay:
        guncel["detay"] = detay
    if dosyalar:
        guncel["dosyalar"] = dosyalar
    mevcut["ozellikler"][ozellik] = guncel

    # Aktif ajan listesini güncelle
    if aktif_ajan and durum == "isleniyor":
        mevcut.setdefault("aktif_ajanlar", {})
        mevcut["aktif_ajanlar"][ozellik] = "calisiyor"
    elif aktif_ajan and durum == "tamam":
        mevcut.setdefault("aktif_ajanlar", {})
        mevcut["aktif_ajanlar"].pop(ozellik, None)
    elif aktif_ajan and durum == "eksik":
        mevcut.setdefault("aktif_ajanlar", {})
        mevcut["aktif_ajanlar"].pop(ozellik, None)

    # İstatistikleri yeniden hesapla
    ozellikler = mevcut.get("ozellikler", {})
    mevcut["toplam_ozellik"] = len(ozellikler)
    mevcut["tamam"] = sum(1 for o in ozellikler.values() if o.get("durum") == "tamam")
    mevcut["isleniyor"] = sum(1 for o in ozellikler.values() if o.get("durum") == "isleniyor")

    durum_yaz(mevcut, bot_adi)
    return mevcut


def durum_raporu() -> str:
    """İnsan tarafından okunabilir durum raporu üret.

    Returns:
        Formatlı metin raporu
    """
    durum = durum_oku()
    satirlar = [
        f"📊 ReYMeN Proje Durumu",
        f"   Son Güncelleme: {durum.get('son_guncelleme', '?')}",
        f"   Güncelleyen: {durum.get('guncelleyen_bot', '?')}",
        f"   İstatistik: {durum.get('tamam', 0)}/{durum.get('toplam_ozellik', 0)} tamam, {durum.get('isleniyor', 0)} işleniyor",
        "",
    ]

    # Aktif ajanlar
    aktif = durum.get("aktif_ajanlar", {})
    if aktif:
        satirlar.append("🟢 Aktif Ajanlar:")
        for ajan, durum_str in aktif.items():
            satirlar.append(f"   • {ajan}: {durum_str}")
        satirlar.append("")

    # Özellik listesi
    satirlar.append("Özellikler:")
    for ad, bilgi in durum.get("ozellikler", {}).items():
        durum_simge = {"tamam": "✅", "isleniyor": "🔄", "eksik": "❌"}.get(
            bilgi.get("durum", ""), "❓"
        )
        satirlar.append(f"  {durum_simge} {ad}: {bilgi.get('detay', '')}")
        dosyalar = bilgi.get("dosyalar", [])
        if dosyalar:
            for d in dosyalar[:3]:  # En fazla 3 dosya göster
                satirlar.append(f"      📄 {d}")

    return "\n".join(satirlar)


# ── CLI Entry ──────────────────────────────────────────────────────────────────

def _cli():
    """Komut satırından kullanım: python -m reymen.sistem.durum_paylas --oku"""
    import argparse

    parser = argparse.ArgumentParser(description="Botlar Arası Paylaşımlı Durum")
    parser.add_argument("--oku", action="store_true", help="Durumu oku ve göster")
    parser.add_argument("--rapor", action="store_true", help="İnsan-okunabilir rapor göster")
    parser.add_argument("--guncelle", action="store_true", help="Durum güncelle")
    parser.add_argument("--bot", default="cli", help="Güncelleyen bot adı")
    parser.add_argument("--ozellik", help="Özellik adı")
    parser.add_argument("--durum", choices=["tamam", "isleniyor", "eksik"], help="Yeni durum")
    parser.add_argument("--detay", default="", help="Açıklama")

    args = parser.parse_args()

    if args.oku:
        print(json.dumps(durum_oku(), ensure_ascii=False, indent=2))
    elif args.rapor:
        print(durum_raporu())
    elif args.guncelle:
        if not args.ozellik or not args.durum:
            print("Hata: --guncelle için --ozellik ve --durum gerekli")
            sys.exit(1)
        durum_guncelle(args.bot, args.ozellik, args.durum, args.detay)
        print(f"✅ {args.ozellik} → {args.durum} olarak güncellendi (bot: {args.bot})")
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
