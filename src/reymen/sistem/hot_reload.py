# -*- coding: utf-8 -*-
"""
hot_reload.py — Motor icin sicak yukleme (hot-reload) modulu.

Calisma zamaninda plugin/skill/modul degisikliklerini algilar
ve motor'a yeniden yukler. importlib.reload + watchdog ile.

Kullanim:
    from reymen.sistem.hot_reload import HotReloader
    reloader = HotReloader(motor)
    reloader.baslat()  # arka planda izlemeye baslar
    reloader.durum()   # durum raporu
"""

from __future__ import annotations

import importlib
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)


class HotReloader:
    """Motor tool'lari ve plugin'leri icin hot-reload yoneticisi.

    Ozellikler:
    - tools/ ve plugins/ klasorlerini izler
    - Dosya degisikliginde ilgili modulu reload eder
    - Motor'a yeniden kaydeder
    - Durum raporu verir
    """

    def __init__(self, motor: Any, aralik: int = 10):
        """
        Args:
            motor: Motor instance'i (plugin_arac_kaydet icin)
            aralik: Tarama araligi (saniye, varsayilan 10)
        """
        self._motor = motor
        self._aralik = aralik
        self._thread: Optional[threading.Thread] = None
        self._dur = threading.Event()
        self._izlenen: dict[str, float] = {}  # dosya_yolu -> son_mtime
        self._istatistik = {"tarama": 0, "yenilenen": 0, "hata": 0}

        # Izlenecek klasorler
        proje_kok = Path(__file__).resolve().parent.parent.parent
        self._klasorler = [
            proje_kok / "reymen" / "arac",
            proje_kok / "reymen" / "sistem" / "plugins",
        ]

    def klasor_ekle(self, yol: str | Path) -> None:
        """Izleme listesine yeni klasor ekle."""
        p = Path(yol)
        if p.exists() and p.is_dir():
            self._klasorler.append(p)
            logger.info("[HotReload] Klasor eklendi: %s", p)

    def baslat(self) -> str:
        """Arka planda izleme baslat."""
        if self._thread and self._thread.is_alive():
            return "[HotReload] Zaten calisiyor"

        self._dur.clear()
        self._thread = threading.Thread(target=self._dongu, daemon=True)
        self._thread.start()
        logger.info("[HotReload] Baslatildi (aralik: %ss)", self._aralik)
        return f"[HotReload] Baslatildi (interval={self._aralik}s)"

    def durdur(self) -> str:
        """Izlemeyi durdur."""
        if self._thread and self._thread.is_alive():
            self._dur.set()
            self._thread.join(timeout=5)
            return "[HotReload] Durduruldu"
        return "[HotReload] Zaten kapali"

    def durum(self) -> dict:
        """Durum raporu."""
        return {
            "calisiyor": self._thread is not None and self._thread.is_alive(),
            "izlenen_klasor": len(self._klasorler),
            "izlenen_dosya": len(self._izlenen),
            "istatistik": dict(self._istatistik),
        }

    def _dongu(self) -> None:
        """Ana izleme dongusu."""
        while not self._dur.is_set():
            try:
                self._tarama()
                self._istatistik["tarama"] += 1
            except Exception as e:
                self._istatistik["hata"] += 1
                logger.warning("[HotReload] Tarama hatasi: %s", e)
            time.sleep(self._aralik)

    def _tarama(self) -> None:
        """Klasorleri tara, degisen dosyalari reload et."""
        for klasor in self._klasorler:
            if not klasor.exists():
                continue
            for dosya in klasor.rglob("*.py"):
                if dosya.name.startswith("__"):
                    continue
                yol = str(dosya)
                son_mtime = dosya.stat().st_mtime

                # Ilk tarama: kaydet
                if yol not in self._izlenen:
                    self._izlenen[yol] = son_mtime
                    continue

                # Degisiklik var mi?
                if son_mtime > self._izlenen[yol]:
                    self._izlenen[yol] = son_mtime
                    self._reload_modul(dosya)

    def _reload_modul(self, dosya: Path) -> bool:
        """Degisen dosyayi reload et ve motor'a yeniden kaydet."""
        try:
            # Modul adini bul
            rel = dosya.relative_to(Path(__file__).resolve().parent.parent.parent)
            modul_adi = "reymen." + str(rel.with_suffix("")).replace(os.sep, ".")

            # importlib.reload
            if modul_adi in sys.modules:
                mod = importlib.reload(sys.modules[modul_adi])
                logger.info("[HotReload] Reload edildi: %s", modul_adi)

                # motor_kaydet varsa cagir
                if hasattr(mod, "motor_kaydet") and self._motor:
                    try:
                        mod.motor_kaydet(self._motor)
                        logger.info("[HotReload] Motor'a yeniden kaydedildi: %s", modul_adi)
                    except Exception as e:
                        logger.warning("[HotReload] motor_kaydet hatasi (%s): %s", modul_adi, e)

                self._istatistik["yenilenen"] += 1
                return True
            else:
                logger.debug("[HotReload] Modul henuz yuklenmemis: %s", modul_adi)
        except Exception as e:
            logger.warning("[HotReload] Reload hatasi (%s): %s", dosya.name, e)
        return False


# ── Motor Tool'lari ─────────────────────────────────────────────────────────

_HOT_RELOADER: Optional[HotReloader] = None


def motor_hot_reload_baslat(params: str = "") -> str:
    """HOT_RELOAD_BASLAT(aralik=10)\n
    Hot-reload izlemeyi baslatir.\n
    Parametre: aralik (int, saniye cinsinden tarama araligi)
    """
    global _HOT_RELOADER
    if params and "=" in params:
        try:
            aralik = int(params.split("=")[1].strip().rstrip(")"))
        except (ValueError, IndexError):
            aralik = 10
    else:
        aralik = 10

    if _HOT_RELOADER is None:
        return "[HotReload] Motor referansi yok. Once motor_kaydet() cagrilmali."
    return _HOT_RELOADER.baslat()


def motor_hot_reload_durdur(params: str = "") -> str:
    """HOT_RELOAD_DURDUR()\n
    Hot-reload izlemeyi durdurur.
    """
    global _HOT_RELOADER
    if _HOT_RELOADER:
        return _HOT_RELOADER.durdur()
    return "[HotReload] Calismiyor"


def motor_hot_reload_durum(params: str = "") -> str:
    """HOT_RELOAD_DURUM()\n
    Hot-reload izleyicisinin durum raporu.
    """
    global _HOT_RELOADER
    if _HOT_RELOADER:
        import json
        return json.dumps(_HOT_RELOADER.durum(), indent=2, ensure_ascii=False)
    return '{"calisiyor": false}'


def motor_kaydet(motor: Any) -> None:
    """Motor tarafindan cagrilir, HOT_RELOAD tool'larini kaydeder."""
    global _HOT_RELOADER
    _HOT_RELOADER = HotReloader(motor)

    motor._plugin_arac_kaydet(
        "HOT_RELOAD_BASLAT",
        motor_hot_reload_baslat,
        "Hot-reload izlemeyi baslat: HOT_RELOAD_BASLAT(aralik=10)",
    )
    motor._plugin_arac_kaydet(
        "HOT_RELOAD_DURDUR",
        motor_hot_reload_durdur,
        "Hot-reload izlemeyi durdur: HOT_RELOAD_DURDUR()",
    )
    motor._plugin_arac_kaydet(
        "HOT_RELOAD_DURUM",
        motor_hot_reload_durum,
        "Hot-reload izleyici durumu: HOT_RELOAD_DURUM()",
    )
    logger.info("[HotReload] 3 tool motor'a kaydedildi")
