# -*- coding: utf-8 -*-
"""Varsayılan hook callback fonksiyonları — motor ve döngü olaylarını dinler.

Her fonksiyon ``hook_dispatcher.hook_kaydet()`` ile kaydedilir.
Ortak imza: fn(olay: str, **data) -> None
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

# ── Metrik toplama ──────────────────────────────────────────────────────────

_olay_sayaci: dict[str, int] = defaultdict(int)
_olay_suresi: dict[str, float] = defaultdict(float)
_son_olay_zamani: dict[str, float] = {}
_baslangic = time.time()


def _log_cb(olay: str, **data: Any) -> None:
    """Tüm hook'ları DEBUG seviyesinde logla. Hata ayıklama için."""
    logger.debug("[HOOK] %s -> %s", olay, {k: str(v)[:80] for k, v in data.items()})


def _metrik_cb(olay: str, **data: Any) -> None:
    """Hook olaylarını say ve süre tut. Hata ayıklama/metrik için."""
    _olay_sayaci[olay] += 1
    _son_olay_zamani[olay] = time.time()


def _session_izleme_cb(olay: str, **data: Any) -> None:
    """Session başlangıç/bitiş olaylarını logla."""
    if olay == "on_session_start":
        session_id = data.get("session_id", "?")
        logger.info("[HOOK] Session başladı: %s (task=%s)", session_id, data.get("task_id", "?"))
    elif olay == "on_session_end":
        session_id = data.get("session_id", "?")
        basarili = data.get("basarili", False)
        logger.info(
            "[HOOK] Session bitti: %s | basarili=%s | tur=%s",
            session_id, basarili, data.get("tur_sayisi", "?"),
        )


def _hata_izleme_cb(olay: str, **data: Any) -> None:
    """Hata olaylarını WARNING seviyesinde logla. Kritik hataları ayır."""
    if olay == "on_error":
        hata = data.get("hata", "?")
        baglam = data.get("olay_baglami", "")
        task_id = data.get("task_id", "?")
        logger.warning("[HOOK] HATA task=%s | baglam=%s | hata=%s", task_id, baglam, str(hata)[:150])


def _tool_izleme_cb(olay: str, **data: Any) -> None:
    """Tool çağrılarını izle. Hata durumunda uyar."""
    if olay == "on_tool_call":
        arac = data.get("arac_adi", "?")
        logger.debug("[HOOK] Tool çağrısı: %s", arac)
    elif olay == "on_tool_result":
        arac = data.get("arac_adi", "?")
        sure = data.get("sure_sn", 0)
        if sure > 10:
            logger.info("[HOOK] Yavaş tool: %s (%.1fs)", arac, sure)


def _context_izleme_cb(olay: str, **data: Any) -> None:
    """Context sıkıştırma olaylarını izle."""
    if olay == "on_context_compress":
        mesaj = data.get("mesaj_sayisi", "?")
        token = data.get("token_tahmini", "?")
        logger.info("[HOOK] Context sıkıştırma: %s mesaj, ~%s token", mesaj, token)


# ── Tüm varsayılan callback'leri kaydet ─────────────────────────────────────

def varsayilan_hooklari_kaydet(hook_sistemi: Any = None) -> None:
    """Tüm varsayılan hook callback'lerini kaydet.

    Args:
        hook_sistemi: Motor._hooks (AsynchronousHookDispatcher) veya None.
                      None ise cereyan.hook_dispatcher.hook_kaydet kullanılır.
    """
    from reymen.cereyan.hook_dispatcher import hook_kaydet as _kaydet_fonk

    callbacks = [
        ("on_session_start", _session_izleme_cb),
        ("on_session_start", _metrik_cb),
        ("on_session_end", _session_izleme_cb),
        ("on_session_end", _metrik_cb),
        ("on_turn_start", _metrik_cb),
        ("on_turn_end", _metrik_cb),
        ("on_tool_call", _tool_izleme_cb),
        ("on_tool_call", _metrik_cb),
        ("on_tool_result", _tool_izleme_cb),
        ("on_tool_result", _metrik_cb),
        ("on_error", _hata_izleme_cb),
        ("on_error", _metrik_cb),
        ("on_context_compress", _context_izleme_cb),
    ]

    kaydet = hook_sistemi.kaydet if hook_sistemi else _kaydet_fonk

    for olay, cb in callbacks:
        try:
            kaydet(olay, cb)
        except Exception as e:
            logger.warning("[HOOK] Kayit hatasi %s/%s: %s", olay, cb.__name__, e)

    logger.info("[HOOK] %d varsayılan hook callback kaydedildi", len(callbacks))


# ── Metrik görüntüleme ──────────────────────────────────────────────────────

def metrik_raporu() -> dict:
    """Hook metriklerini döndür: olay bazlı sayı ve süre."""
    return {
        "olay_sayaci": dict(_olay_sayaci),
        "calisma_suresi": round(time.time() - _baslangic, 1),
        "toplam_olay": sum(_olay_sayaci.values()),
    }
