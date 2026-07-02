# -*- coding: utf-8 -*-
"""Olay-güdümlü hook dispatcher.

ReYMeN'in ``invoke_hook`` sisteminden adapte edilmiştir. Konuşma döngüsü
belirli noktalarda hook'ları ateşler; yüklü plugin'ler bunları dinler.

Desteklenen hook olayları:
    on_session_start    — Oturum başlarken
    on_session_end      — Oturum biterken
    on_turn_start       — Her tur başında
    on_turn_end         — Her tur sonunda
    on_tool_call        — Araç çağrılmadan önce
    on_tool_result      — Araç sonucu alındıktan sonra
    on_error            — Hata oluştuğunda
    on_context_compress — Context sıkıştırılmadan önce
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("conversation_loop")

# Hook kayıt defteri: olay_adı → [callback_listesi]
_HOOK_KAYDI: Dict[str, List[Callable]] = {}

# Desteklenen olay adları
GECERLI_OLAYLAR = frozenset({
    "on_session_start",
    "on_session_end",
    "on_turn_start",
    "on_turn_end",
    "on_tool_call",
    "on_tool_result",
    "on_error",
    "on_context_compress",
})


def hook_kaydet(olay: str, callback: Callable) -> None:
    """Bir hook callback'i kaydet.

    Args:
        olay:     Hook olay adı (ör. "on_session_start").
        callback: Çağrılacak fonksiyon. Kwargs ile çağrılır.

    Raises:
        ValueError: Bilinmeyen olay adı.
    """
    if olay not in GECERLI_OLAYLAR:
        raise ValueError(f"Bilinmeyen hook olayı: {olay!r}. Geçerliler: {sorted(GECERLI_OLAYLAR)}")
    if olay not in _HOOK_KAYDI:
        _HOOK_KAYDI[olay] = []
    if callback not in _HOOK_KAYDI[olay]:
        _HOOK_KAYDI[olay].append(callback)
        log.debug("Hook kayıt: olay=%s callback=%s", olay, getattr(callback, "__name__", repr(callback)))


def hook_kaldir(olay: str, callback: Callable) -> bool:
    """Kayıtlı bir hook'u kaldır. Başarıyla kaldırıldıysa True döner."""
    if olay in _HOOK_KAYDI and callback in _HOOK_KAYDI[olay]:
        _HOOK_KAYDI[olay].remove(callback)
        return True
    return False


def hook_cagir(olay: str, **kwargs: Any) -> List[Any]:
    """Bir olayın tüm kayıtlı hook'larını ateşle.

    Her hook ayrı try/except ile korunur — biri çökmesi diğerlerini
    durdurmaz. Hata durumunda log.warning yazar ve devam eder.

    Args:
        olay:    Hook olay adı.
        **kwargs: Hook'a iletilecek named argümanlar.

    Returns:
        Hook return değerlerinin listesi (None'lar dahil).
    """
    callback_ler = _HOOK_KAYDI.get(olay, [])
    if not callback_ler:
        return []

    sonuclar: List[Any] = []
    for cb in callback_ler:
        t0 = time.monotonic()
        try:
            sonuc = cb(olay=olay, **kwargs)
            sonuclar.append(sonuc)
        except Exception as e:
            gecen = time.monotonic() - t0
            log.warning(
                "Hook başarısız: olay=%s callback=%s sure=%.3fs hata=%s",
                olay,
                getattr(cb, "__name__", repr(cb)),
                gecen,
                e,
            )
            sonuclar.append(None)
    return sonuclar


# ReYMeN uyumluluğu için alias
invoke_hook = hook_cagir
register_hook = hook_kaydet


def tum_hooklari_temizle() -> None:
    """Tüm kayıtlı hook'ları temizle (test izolasyonu için)."""
    _HOOK_KAYDI.clear()


def kayitli_hooklar() -> Dict[str, List[str]]:
    """Kayıtlı hook'ların okunabilir özetini döndür."""
    return {
        olay: [getattr(cb, "__name__", repr(cb)) for cb in cblar]
        for olay, cblar in _HOOK_KAYDI.items()
        if cblar
    }


# ── Decorator tabanlı kayıt ──────────────────────────────────────────────────

def hook(olay: str) -> Callable:
    """Hook kaydı için decorator.

    Örnek::

        @hook("on_session_start")
        def oturum_basladi(session_id: str, **kwargs):
            print(f"Oturum başladı: {session_id}")
    """
    def _decorator(fn: Callable) -> Callable:
        hook_kaydet(olay, fn)
        return fn
    return _decorator


# ── Sık kullanılan olay ateşleyicileri ──────────────────────────────────────

def oturum_baslat_tetikle(session_id: str, agent_adi: str = "", **kw) -> None:
    hook_cagir("on_session_start", session_id=session_id, agent_adi=agent_adi, **kw)


def oturum_bitir_tetikle(session_id: str, tur_sayisi: int = 0, **kw) -> None:
    hook_cagir("on_session_end", session_id=session_id, tur_sayisi=tur_sayisi, **kw)


def tur_baslat_tetikle(tur: int, task_id: str = "", **kw) -> None:
    hook_cagir("on_turn_start", tur=tur, task_id=task_id, **kw)


def tur_bitir_tetikle(tur: int, basarili: bool = True, **kw) -> None:
    hook_cagir("on_turn_end", tur=tur, basarili=basarili, **kw)


def arac_cagri_tetikle(arac_adi: str, argumanlar: dict, **kw) -> None:
    hook_cagir("on_tool_call", arac_adi=arac_adi, argumanlar=argumanlar, **kw)


def arac_sonuc_tetikle(arac_adi: str, sonuc: str, sure_sn: float = 0.0, **kw) -> None:
    hook_cagir("on_tool_result", arac_adi=arac_adi, sonuc=sonuc, sure_sn=sure_sn, **kw)


def hata_tetikle(hata: Exception, olay_baglami: str = "", **kw) -> None:
    hook_cagir("on_error", hata=hata, olay_baglami=olay_baglami, **kw)


def context_sikistirma_tetikle(mesaj_sayisi: int, token_tahmini: int = 0, **kw) -> None:
    hook_cagir("on_context_compress", mesaj_sayisi=mesaj_sayisi, token_tahmini=token_tahmini, **kw)
