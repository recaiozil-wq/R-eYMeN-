# -*- coding: utf-8 -*-
"""
reymen/sistem/hata_topla.py — Merkezi Hata Toplama ve Bildirim Sistemi.

Özellikler:
  - sys.excepthook ile yakalanamayan hataları yakalar
  - logging.Handler ile tüm log'ları toplar
  - JSONL formatında ~/.hermes/errors/ klasörüne kaydeder
  - Kritik hatalarda Telegram/webhook bildirimi gönderir
  - Web UI üzerinden görüntüleme ve yönetim

Kullanım:
    from reymen.sistem.hata_topla import hata_topla
    hata_topla.baslat()  # Uygulama başlangıcında çağır
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Varsayılan yapılandırma ───────────────────────────────────────
HATA_DIZINI = Path.home() / ".ReYMeN" / "errors"
HATA_DOSYASI = HATA_DIZINI / "errors.jsonl"
AZAMI_KAYIT = 500  # maksimum kayıt sayısı
SEVIYE_SIRASI = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "ERROR": 3,
    "CRITICAL": 4,
}

# ── Bildirim kanalları ───────────────────────────────────────────
_bildirim_kanallari: list[dict] = []


def bildirim_kanal_ekle(
    tur: str,
    hedef: str,
    esik: str = "ERROR",
    token: str = "",
) -> None:
    """Bildirim kanalı ekle.

    Args:
        tur: "telegram", "webhook", "log"
        hedef: Telegram chat_id veya webhook URL
        esik: Minimum seviye (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        token: Telegram bot token (telegram için)
    """
    _bildirim_kanallari.append({
        "tur": tur,
        "hedef": hedef,
        "esik": esik,
        "token": token,
        "aktif": True,
    })


# ═══════════════════════════════════════════════════════════════════
# Hata Deposu
# ═══════════════════════════════════════════════════════════════════

class HataDeposu:
    """JSONL dosyasına hata kayıtlarını yaz/oku."""

    def __init__(self, dosya_yolu: Path = HATA_DOSYASI):
        self.dosya = dosya_yolu
        self._kilit = threading.Lock()

    def kaydet(self, kayit: dict) -> None:
        """Tek kaydı JSONL'e ekle (thread-safe)."""
        with self._kilit:
            self.dosya.parent.mkdir(parents=True, exist_ok=True)
            with open(self.dosya, "a", encoding="utf-8") as f:
                f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
            # Eşik aşıldıysa temizle
            self._boyut_kontrol()

    def listele(
        self,
        limit: int = 50,
        offset: int = 0,
        seviye: str = "",
        kaynak: str = "",
    ) -> list[dict]:
        """Kayıtları listele (en yeni en üstte)."""
        if not self.dosya.exists():
            return []

        kayitlar = []
        with open(self.dosya, "r", encoding="utf-8") as f:
            for satir in f:
                satir = satir.strip()
                if satir:
                    try:
                        kayitlar.append(json.loads(satir))
                    except json.JSONDecodeError:
                        continue

        # Filtrele
        if seviye:
            min_sev = SEVIYE_SIRASI.get(seviye, 0)
            kayitlar = [k for k in kayitlar if SEVIYE_SIRASI.get(k.get("seviye", "INFO"), 0) >= min_sev]
        if kaynak:
            kayitlar = [k for k in kayitlar if kaynak.lower() in k.get("kaynak", "").lower()]

        # Ters sırala (en yeni ilk)
        kayitlar.reverse()
        return kayitlar[offset:offset + limit]

    def temizle(self) -> int:
        """Tüm kayıtları sil."""
        say = 0
        if self.dosya.exists():
            # Say
            with open(self.dosya, "r") as f:
                for _ in f:
                    say += 1
            # Sil
            self.dosya.unlink(missing_ok=True)
        return say

    def ozet(self) -> dict:
        """Özet istatistikler."""
        if not self.dosya.exists():
            return {"toplam": 0, "error": 0, "critical": 0, "warning": 0, "info": 0}

        sayac = {"toplam": 0, "ERROR": 0, "CRITICAL": 0, "WARNING": 0, "INFO": 0}
        with open(self.dosya, "r") as f:
            for satir in f:
                satir = satir.strip()
                if satir:
                    try:
                        k = json.loads(satir)
                        sayac["toplam"] += 1
                        sev = k.get("seviye", "INFO")
                        if sev in sayac:
                            sayac[sev] += 1
                    except json.JSONDecodeError:
                        continue
        return sayac

    def _boyut_kontrol(self) -> None:
        """AZAMI_KAYIT aşıldıysa eski kayıtları sil."""
        if not self.dosya.exists():
            return
        with open(self.dosya, "r") as f:
            satirlar = f.readlines()
        if len(satirlar) > AZAMI_KAYIT:
            # Son AZAMI_KAYIT satırı tut
            with open(self.dosya, "w") as f:
                f.writelines(satirlar[-AZAMI_KAYIT:])


# ═══════════════════════════════════════════════════════════════════
# Log Handler (logging modülü için)
# ═══════════════════════════════════════════════════════════════════

class HataLogHandler(logging.Handler):
    """Log kayıtlarını HataDeposu'na yönlendirir."""

    def __init__(self, depo: HataDeposu, seviye: int = logging.WARNING):
        super().__init__(seviye)
        self.depo = depo

    def emit(self, record: logging.LogRecord) -> None:
        try:
            kayit = {
                "zaman": datetime.fromtimestamp(record.created).isoformat(),
                "seviye": record.levelname,
                "kaynak": record.name,
                "mesaj": self.format(record),
                "traceback": "",
                "thread": record.threadName,
            }
            if record.exc_info and record.exc_info[1]:
                kayit["traceback"] = "".join(
                    traceback.format_exception(*record.exc_info)
                )
            self.depo.kaydet(kayit)
            # Kritik hatalarda bildirim
            if record.levelno >= logging.ERROR:
                _bildirim_gonder(kayit)
        except Exception:
            self.handleError(record)


# ═══════════════════════════════════════════════════════════════════
# Exception Hook (sys.excepthook)
# ═══════════════════════════════════════════════════════════════════

_eski_excepthook: Optional[Any] = None


def _excepthook(tip, deger, tb):
    """Yakalanamayan istisnaları kaydet."""
    try:
        kayit = {
            "zaman": datetime.now().isoformat(),
            "seviye": "CRITICAL",
            "kaynak": "sys.excepthook",
            "mesaj": f"{tip.__name__}: {deger}",
            "traceback": "".join(traceback.format_exception(tip, deger, tb)),
            "thread": threading.current_thread().name,
        }
        depo = HataDeposu()
        depo.kaydet(kayit)
        _bildirim_gonder(kayit)
    except Exception as _e:
        __import__("logging").getLogger(__name__).warning(
            "[SessizExcept] %%s: %%s", type(_e).__name__, _e
        )
    finally:
        if _eski_excepthook:
            _eski_excepthook(tip, deger, tb)


# ═══════════════════════════════════════════════════════════════════
# Bildirim Gönderme
# ═══════════════════════════════════════════════════════════════════

def _bildirim_gonder(kayit: dict) -> None:
    """Kayıtlı kanallara bildirim gönder."""
    seviye = kayit.get("seviye", "INFO")
    for kanal in _bildirim_kanallari:
        if not kanal.get("aktif", True):
            continue
        esik = kanal.get("esik", "ERROR")
        if SEVIYE_SIRASI.get(seviye, 0) < SEVIYE_SIRASI.get(esik, 3):
            continue

        try:
            tur = kanal["tur"]
            hedef = kanal["hedef"]

            if tur == "telegram":
                _bildirim_telegram(
                    kanal.get("token", ""),
                    hedef,
                    kayit,
                )
            elif tur == "webhook":
                _bildirim_webhook(hedef, kayit)
        except Exception as e:
            logger.debug("Bildirim hatası (%s): %s", kanal["tur"], e)


def _bildirim_telegram(token: str, chat_id: str, kayit: dict) -> None:
    """Telegram'a hata bildirimi gönder."""
    import urllib.request
    import urllib.parse

    seviye = kayit.get("seviye", "INFO")
    ikon = "🔴" if seviye == "CRITICAL" else "🟠" if seviye == "ERROR" else "🟡"
    mesaj = (
        f"{ikon} *HATA BİLDİRİMİ*\n"
        f"Seviye: {seviye}\n"
        f"Kaynak: {kayit.get('kaynak', '?')}\n"
        f"Zaman: {kayit.get('zaman', '?')}\n"
        f"Mesaj: {kayit.get('mesaj', '?')[:200]}"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": mesaj,
        "parse_mode": "Markdown",
    }).encode()

    req = urllib.request.Request(url, data=data, method="POST")
    urllib.request.urlopen(req, timeout=10)


def _bildirim_webhook(url: str, kayit: dict) -> None:
    """Webhook'a hata bildirimi gönder."""
    import urllib.request
    import json

    data = json.dumps(kayit).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=10)


# ═══════════════════════════════════════════════════════════════════
# Ana Sınıf (Singleton)
# ═══════════════════════════════════════════════════════════════════

class HataToplayici:
    """Merkezi hata toplama sistemi.

    Singleton: hata_topla() ile erişilir.
    """

    def __init__(self):
        self.depo = HataDeposu()
        self._handler: Optional[HataLogHandler] = None
        self._basladi = False

    def baslat(
        self,
        log_seviye: int = logging.WARNING,
        telegram_token: str = "",
        telegram_chat: str = "",
        webhook_url: str = "",
    ) -> None:
        """Hata toplamayı başlat.

        Args:
            log_seviye: Minimum log seviyesi
            telegram_token: Telegram bot token
            telegram_chat: Telegram chat ID
            webhook_url: Webhook URL
        """
        if self._basladi:
            return

        global _eski_excepthook
        _eski_excepthook = sys.excepthook
        sys.excepthook = _excepthook

        # Log handler
        self._handler = HataLogHandler(self.depo, log_seviye)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        self._handler.setFormatter(formatter)

        # Root logger'a ekle
        root_logger = logging.getLogger()
        root_logger.addHandler(self._handler)
        root_logger.setLevel(logging.WARNING)

        # Bildirim kanalları
        if telegram_token and telegram_chat:
            bildirim_kanal_ekle("telegram", telegram_chat, "ERROR", telegram_token)
        if webhook_url:
            bildirim_kanal_ekle("webhook", webhook_url, "ERROR")

        self._basladi = True
        logger.info("HataToplayici başlatıldı")

    def durdur(self) -> None:
        """Hata toplamayı durdur."""
        if self._basladi:
            sys.excepthook = _eski_excepthook
            if self._handler:
                logging.getLogger().removeHandler(self._handler)
            self._basladi = False

    def manuel_kaydet(
        self,
        seviye: str = "ERROR",
        kaynak: str = "",
        mesaj: str = "",
        traceback_str: str = "",
    ) -> dict:
        """Elle hata kaydı ekle."""
        kayit = {
            "zaman": datetime.now().isoformat(),
            "seviye": seviye,
            "kaynak": kaynak,
            "mesaj": mesaj,
            "traceback": traceback_str,
            "thread": threading.current_thread().name,
        }
        self.depo.kaydet(kayit)
        if seviye in ("ERROR", "CRITICAL"):
            _bildirim_gonder(kayit)
        return kayit


# ── Singleton erişimcisi ─────────────────────────────────────────
_hata_topla_instance: Optional[HataToplayici] = None


def hata_topla() -> HataToplayici:
    global _hata_topla_instance
    if _hata_topla_instance is None:
        _hata_topla_instance = HataToplayici()
    return _hata_topla_instance
