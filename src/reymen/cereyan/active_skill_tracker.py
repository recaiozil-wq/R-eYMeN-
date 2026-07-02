# -*- coding: utf-8 -*-
"""
active_skill_tracker.py — Aktif skill takibi ve LLM context enjeksiyonu.

SKILL_AKTIVAT araci skill icerigini yukler ama LLM context'ine otomatik
eklemez. Bu modul, aktif skill'i takip eder ve conversation_loop'un
sistem prompt'una enjekte edilmesini saglar.

Kullanim:
    from reymen.cereyan.active_skill_tracker import (
        aktif_skill_ayarla, aktif_skill_temizle,
        aktif_skill_al, aktif_skill_context_ekle
    )

    # Bir skill aktive edildiginde:
    aktif_skill_ayarla("test-driven-development", "=== SKILL: TDD ===\\n...")

    # Sistem prompt'u olusturulurken:
    ek_context = aktif_skill_context_ekle()
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Modul seviyesinde aktif skill state
_aktif_skill_adi: Optional[str] = None
_aktif_skill_icerik: Optional[str] = None


def aktif_skill_ayarla(ad: str, icerik: str) -> None:
    """Aktif skill'i ayarla (SKILL_AKTIVAT tarafindan cagrilir).

    Args:
        ad: Skill adi
        icerik: SKILL_AKTIVAT'in dondurdugu tam icerik
    """
    global _aktif_skill_adi, _aktif_skill_icerik
    _aktif_skill_adi = ad
    _aktif_skill_icerik = icerik
    logger.info("[SkillTracker] Skill aktive edildi: %s (%d chars)", ad, len(icerik or ""))


def aktif_skill_temizle() -> None:
    """Aktif skill'i temizle."""
    global _aktif_skill_adi, _aktif_skill_icerik
    _aktif_skill_adi = None
    _aktif_skill_icerik = None
    logger.info("[SkillTracker] Skill temizlendi")


def aktif_skill_al() -> Optional[dict]:
    """Aktif skill bilgisini al.

    Returns:
        {"ad": str, "icerik": str} veya None
    """
    if _aktif_skill_adi and _aktif_skill_icerik:
        return {"ad": _aktif_skill_adi, "icerik": _aktif_skill_icerik}
    return None


def aktif_skill_context_ekle() -> str:
    """Aktif skill varsa, sistem prompt'una eklenecek metni uret.

    ConversationLoop._sistem_promptu_olustur() icinde cagrilir.

    Returns:
        str: Skill context metni (bos olabilir)
    """
    aktif = aktif_skill_al()
    if not aktif:
        return ""

    ad = aktif["ad"]
    icerik = aktif["icerik"]

    # Icerigi kisalt (ilk 2000 karakter context'e eklenir)
    kisaltilmis = icerik[:2000]
    if len(icerik) > 2000:
        kisaltilmis += f"\n... [{len(icerik)} karakter, ilk 2000 gosterildi]"

    return (
        f"\n\n=== AKTIF SKILL: {ad} ===\n"
        f"{kisaltilmis}\n"
        f"=== SKILL SONU ===\n"
    )


# ── Motor / Plugin sistemi uyumlulugu ─────────────────────────────

def motor_kaydet(motor) -> bool:
    """Motor sistemi tarafindan otomatik cagrilir.

    SKILL_AKTIVAT hook'unu ekler ve aktif skill sorgulama araci ekler.
    """
    try:
        # Aktif skill sorgulama araci ekle
        motor._plugin_arac_kaydet(
            "SKILL_AKTIF_SORGULA",
            lambda: str(aktif_skill_al() or {"durum": "aktif_skill_yok"}),
            "Su anda aktif olan skill'i sorgula",
        )
        motor._plugin_arac_kaydet(
            "SKILL_AKTIF_TEMIZLE",
            lambda: (aktif_skill_temizle(), "Aktif skill temizlendi.")[1],
            "Aktif skill'i context'ten kaldir",
        )
        return True
    except Exception as e:
        logger.warning("[SkillTracker] motor_kaydet hatasi: %s", e)
        return False
