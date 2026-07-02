# -*- coding: utf-8 -*-
"""
ortak_watchdog.py — ReYMeN Otonom Degisiklik Izleyici.

Projedeki .py dosyalarini izler, degisiklik algilayinca
otomatik olarak ortak_komut.guncelle() ve durum.json'u tetikler.

Tum botlar tarafindan ortak kullanilir. Ayri bir thread'de calisir.

Kullanim:
    from reymen.sistem.ortak_watchdog import watchdog_baslat
    watchdog_baslat()  # Bot baslangicinda tek satir
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Sabitler ──────────────────────────────────────────────────────────────

PROJE_KOK = Path(__file__).resolve().parent.parent.parent
HASH_DOSYASI = PROJE_KOK / ".ReYMeN" / "watchdog_hash.json"
SCAN_ARALIGI = 120  # saniye (30sn cok agresif, disk I/O patlamasi engelle)
POLLUTION_DOSYALARI = {"__pycache__", ".git", ".venv", "venv", "node_modules"}

# ── Hash Islemleri ────────────────────────────────────────────────────────

def _dosya_hash(dosya: Path) -> str:
    """Bir dosyanin hizli hash'ini hesapla (isim + boyut + mtime)."""
    try:
        stat = dosya.stat()
        h = hashlib.md5()
        h.update(dosya.name.encode())
        h.update(str(stat.st_size).encode())
        h.update(str(stat.st_mtime).encode())
        return h.hexdigest()[:12]
    except Exception:
        return ""


def _proje_hash() -> str:
    """Projedeki tum .py dosyalarinin toplu hash'i."""
    hasher = hashlib.md5()
    for py in sorted(PROJE_KOK.rglob("*.py")):
        if any(p in py.parts for p in POLLUTION_DOSYALARI):
            continue
        hasher.update(_dosya_hash(py).encode())
    return hasher.hexdigest()[:16]


def _hash_kaydet(h: str) -> None:
    HASH_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    HASH_DOSYASI.write_text(
        json.dumps({"hash": h, "zaman": datetime.now().isoformat()},
                    indent=2), encoding="utf-8"
    )


def _hash_oku() -> str:
    if HASH_DOSYASI.exists():
        try:
            return json.loads(HASH_DOSYASI.read_text(encoding="utf-8")).get("hash", "")
        except Exception as _e:
            logger.warning("[OrtakWatchdog] except Exception (L73): %s", Exception)
            pass
    return ""


# ── Ana Fonksiyon ─────────────────────────────────────────────────────────

def degisiklik_kontrol() -> bool:
    """Projede degisiklik var mi? Varsa durum.json'u guncelle.

    Returns:
        True = degisiklik bulundu ve guncellendi
    """
    yeni_hash = _proje_hash()
    eski_hash = _hash_oku()

    if yeni_hash == eski_hash and eski_hash:
        return False  # Degisiklik yok

    try:
        from reymen.sistem.ortak_komut import guncelle
        guncelle()
        _hash_kaydet(yeni_hash)
        logger.info("[Watchdog] ✅ Degisiklik algilandi, durum.json guncellendi")
        return True
    except Exception as e:
        # Henuz ortak_komut yuklenemiyorsa sadece hash kaydet
        _hash_kaydet(yeni_hash)
        logger.info("[Watchdog] Hash guncellendi (ortak_komut yuklenemedi: %s)", e)
        return False


# ── Watchdog Thread ───────────────────────────────────────────────────────

def _watchdog_dongu(interval: int = SCAN_ARALIGI) -> None:
    """Her N saniyede bir degisiklik kontrolu yap."""
    while True:
        try:
            degisiklik_kontrol()
        except Exception as e:
            logger.warning("[Watchdog] Kontrol hatasi: %s", e)
        time.sleep(interval)


_watchdog_thread: Optional[threading.Thread] = None


def watchdog_baslat(interval: int = SCAN_ARALIGI) -> None:
    """Watchdog thread'ini baslat.

    Args:
        interval: Kac saniyede bir kontrol (varsayilan: 30)
    """
    global _watchdog_thread
    if _watchdog_thread and _watchdog_thread.is_alive():
        return

    _watchdog_thread = threading.Thread(
        target=_watchdog_dongu,
        args=(interval,),
        daemon=True,
        name="reymen-watchdog",
    )
    _watchdog_thread.start()
    logger.info("[Watchdog] ✅ Baslatildi (her %s sn kontrol)", interval)


# ── CLI Test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ReYMeN Otonom Watchdog")
    parser.add_argument("--check", action="store_true", help="Tek seferlik kontrol")
    parser.add_argument("--watch", type=int, nargs="?", const=30, default=0,
                        help="Watchdog baslat (opsiyonel: interval sn)")
    args = parser.parse_args()

    if args.check:
        sonuc = degisiklik_kontrol()
        print(f"{'✅ Degisiklik bulundu' if sonuc else 'ℹ️  Degisiklik yok'}")
    if args.watch > 0:
        print(f"Watchdog baslatiliyor (her {args.watch} sn)...")
        watchdog_baslat(args.watch)
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\nDurduruldu")
