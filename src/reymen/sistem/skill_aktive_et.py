# -*- coding: utf-8 -*-
"""
skill_aktive_et.py — Motor baslangicinda skill'leri otomatik yukler.
"""

from __future__ import annotations
import json, logging, os, sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJE_KOK = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = PROJE_KOK / ".ReYMeN" / "skill_registry.json"


def aktif_skill_sayisi() -> int:
    """Kayitli skill sayisi."""
    if not REGISTRY_PATH.exists():
        return 0
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return len(json.load(f))
    except Exception:
        return 0


def skill_aktif_et(ad: str) -> Optional[str]:
    """Bir skill'in icerigini dondur (aktif et)."""
    if not REGISTRY_PATH.exists():
        return None
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            reg = json.load(f)
        path = reg.get(ad)
        if not path:
            return None
        p = Path(path)
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")
    except Exception as _e:
        __import__("logging").getLogger(__name__).warning(
            "[SessizExcept] %%s: %%s", type(_e).__name__, _e
        )
    return None


def motor_kaydet(motor) -> None:
    """Motor tarafindan cagrilir. SKILL_AKTIF tool'unu kaydeder."""
    if not hasattr(motor, "_plugin_arac_kaydet"):
        return
    try:
        sayi = aktif_skill_sayisi()
        motor._plugin_arac_kaydet(
            "SKILL_AKTIF",
            lambda ad: skill_aktif_et(ad.strip()) or f"[SKILL] '{ad}' bulunamadi.",
            f"Bir skill'in icerigini getirir. {sayi} skill kayitli. Kullanim: SKILL_AKTIF(ad=\"skill_adi\")"
        )
        motor._plugin_arac_kaydet(
            "SKILL_LISTE",
            lambda: f"{sayi} skill kayitli. DURUM_OKU() ile detay gorebilirsin.",
            "Aktif skill sayisini gosterir."
        )
        logger.info("[SkillAktif] %d skill kayitli, tool'lar kaydedildi", sayi)
    except Exception as e:
        logger.warning("[SkillAktif] Motor kayit hatasi: %s", e)
