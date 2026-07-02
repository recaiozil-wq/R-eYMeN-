# -*- coding: utf-8 -*-
"""
image_gen.py — ReYMeN tool arayüzü: Görsel üretim araçları.

Bu modül, reymen.arac.image_gen_engine motorunu ReYMeN'in tool
sistemine bağlar. Motor tarafından otomatik kaydedilir.

Kullanım:
  RESIM_OLUSTUR(prompt="bir kedi", en="1024", boy="1024", backend="fal")
  RESIM_OLUSTUR_BACKEND_LISTELE()
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

try:
    from reymen.arac.image_gen_engine import (
        motor_kaydet,
        resim_olustur,
        image_gen_engine_listele,
    )
except ImportError as e:
    log.warning("[arac/image_gen] image_gen_engine yuklenemedi: %s", e)
    motor_kaydet = lambda motor: None
    resim_olustur = lambda prompt, en="1024", boy="1024", backend="": (
        f"[RESIM_OLUSTUR] Motor yuklenemedi: {prompt}"
    )
    image_gen_engine_listele = lambda: "[RESIM_OLUSTUR] Motor yuklenemedi."


__all__ = [
    "motor_kaydet",
    "resim_olustur",
    "image_gen_engine_listele",
]
