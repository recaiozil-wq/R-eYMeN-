"""ReYMeN tools.delegate_tool shim — gerçek implementasyon için delegate_task_tool'a yönlendirir."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_max_concurrent_children() -> int:
    """Hermes _get_max_concurrent_children — maksimum paralel alt ajan sayısı."""
    return int(__import__("os").environ.get("DELEGATE_MAX_PARALEL", "5"))


def delegate_task(*args, **kwargs) -> Any:
    """Hermes delegate_task — reymen.tools.delegate_task_tool'a yönlendirir.

    Gerçek ThreadPoolExecutor tabanlı implementasyon için
    reymen.tools.delegate_task_tool.delegate_task() kullanılır.
    """
    try:
        from reymen.tools.delegate_task_tool import delegate_task as _real_delegate
        return _real_delegate(*args, **kwargs)
    except ImportError as _e:
        logger.warning("delegate_task_tool yüklenemedi, stub kullanılıyor: %s", _e)
        return []


def motor_kaydet(motor) -> None:
    """DELEGATE_TASK tool'unu motor'a kaydet.

    Gerçek tool kaydı delegate_task_tool.py üzerinden yapılır.
    Bu fonksiyon sadece eski referanslar için tutulmaktadır.
    """
    try:
        from reymen.tools.delegate_task_tool import motor_kaydet as _real_kaydet
        _real_kaydet(motor)
    except ImportError as _e:
        logger.warning("delegate_task_tool yüklenemedi, tool kaydedilemedi: %s", _e)
