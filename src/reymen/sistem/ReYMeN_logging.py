# -*- coding: utf-8 -*-
"""ReYMeN_logging.py — Merkezi log sistemi.

Rotating file handler ile log yonetimi.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "ReYMeN.log"


def kur(seviye=logging.INFO, dosya_yolu=None):
    """Loglama sistemini kur.

    Args:
        seviye: Log seviyesi (default: INFO)
        dosya_yolu: Ozel log dosyasi yolu

    Returns:
        logging.Logger
    """
    logger = logging.getLogger("ReYMeN")
    logger.setLevel(seviye)

    # Dosyaya yaz (rotating, max 5MB, 3 yedek)
    dosya = dosya_yolu or LOG_FILE
    handler = RotatingFileHandler(
        dosya, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)

    # Konsola yaz
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console)

    return logger


# Varsayilan logger
logger = kur()


def get_logger(ad: str) -> logging.Logger:
    """Alt modul icin logger al.

    Args:
        ad: Modul adi (ornek: "motor", "beyin")

    Returns:
        logging.Logger
    """
    return logging.getLogger(f"ReYMeN.{ad}")


# ReYMeN uyumluluk fonksiyonlari
_session_context = {}

def set_session_context(session_id: str, **kwargs):
    """ReYMeN uyumluluk: session baglamini ayarla."""
    _session_context.clear()
    _session_context["session_id"] = session_id
    _session_context.update(kwargs)

def get_session_context() -> dict:
    """ReYMeN uyumluluk: session baglamini getir."""
    return dict(_session_context)


if __name__ == "__main__":
    log = kur()
    log.info("Log sistemi test ediliyor...")
    log.warning("Bu bir uyari mesaji")
    log.error("Bu bir hata mesaji")
    print(f"Log dosyasi: {LOG_FILE}")
