"""⚙️ Güvenli process yönetimi — PID-based start/stop/restart."""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJE_KOK = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Process Manager
# ---------------------------------------------------------------------------

class ProcessManager:
    """PID-based process yönetimi. taskkill kullanmaz, sinyal gönderir."""

    def __init__(self, pid_dir: Path | None = None) -> None:
        self.pid_dir = pid_dir or (PROJE_KOK / ".ReYMeN" / "pids")
        self.pid_dir.mkdir(parents=True, exist_ok=True)

    def _pid_yolu(self, ad: str) -> Path:
        return self.pid_dir / f"{ad}.pid"

    def _durum_yolu(self, ad: str) -> Path:
        return self.pid_dir / f"{ad}.json"

    def kaydet(self, ad: str, pid: int, extra: dict | None = None) -> None:
        """PID ve metadata kaydet."""
        self._pid_yolu(ad).write_text(str(pid))
        durum = {
            "pid": pid,
            "ad": ad,
            "baslama": datetime.now().isoformat(),
            "durum": "calisiyor",
            "port": (extra or {}).get("port", 5000),
        }
        if extra:
            durum.update(extra)
        self._durum_yolu(ad).write_text(json.dumps(durum, indent=2, ensure_ascii=False))

    def durum(self, ad: str) -> dict:
        """Process durumunu döndür."""
        durum_yolu = self._durum_yolu(ad)
        pid_yolu = self._pid_yolu(ad)

        bilgi: dict = {"ad": ad, "durum": "durduruldu", "pid": None}

        if durum_yolu.exists():
            try:
                bilgi.update(json.loads(durum_yolu.read_text(encoding="utf-8")))
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )

        if pid_yolu.exists():
            try:
                pid = int(pid_yolu.read_text().strip())
                if self._pid_calisiyor(pid):
                    bilgi["durum"] = "calisiyor"
                    bilgi["pid"] = pid
                else:
                    bilgi["durum"] = "durduruldu"
                    bilgi["pid"] = None
            except (ValueError, OSError):
                bilgi["durum"] = "durduruldu"

        return bilgi

    def durdur(self, ad: str, force: bool = False) -> bool:
        """Process'i durdur. force=True ise SIGKILL."""
        pid_yolu = self._pid_yolu(ad)
        if not pid_yolu.exists():
            return True  # zaten yok

        try:
            pid = int(pid_yolu.read_text().strip())
            try:
                os.kill(pid, signal.SIGTERM)
                if not force:
                    # Graceful shutdown için bekle
                    for _ in range(10):
                        if not self._pid_calisiyor(pid):
                            break
                        time.sleep(0.3)
                    else:
                        # Hala calisiyor, force kill
                        if hasattr(signal, "SIGKILL"):
                            os.kill(pid, signal.SIGKILL)
                        else:
                            subprocess.run(
                                ["taskkill", "/F", "/PID", str(pid)],
                                capture_output=True, timeout=5
                            )
            except (OSError, subprocess.TimeoutExpired):
                # Zaten ölmüş
                logger.warning("[fix_01_sessiz_except] Exception")
        except (ValueError, OSError) as e:
            logger.warning("PID okunamadi: %s", e)

        # Temizlik
        pid_yolu.unlink(missing_ok=True)
        self._durum_yolu(ad).unlink(missing_ok=True)
        return True

    def baslat(
        self,
        ad: str,
        komut: list[str],
        port: int = 5000,
        log_dosyasi: Path | None = None,
    ) -> bool:
        """Process'i arka planda başlat."""
        # Önce varsa durdur
        self.durdur(ad)

        stdout = log_dosyasi or (self.pid_dir / f"{ad}.log")
        try:
            with open(str(stdout), "a", encoding="utf-8") as log_f:
                proc = subprocess.Popen(
                    komut,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
                )
            self.kaydet(ad, proc.pid, {"port": port})
            logger.info("Process baslatildi: %s (PID=%d)", ad, proc.pid)
            return True
        except Exception as e:
            logger.error("Process baslatilamadi: %s — %s", ad, e)
            return False

    def tumu(self) -> list[dict]:
        """Tüm kayıtlı process'leri listele."""
        sonuclar = []
        for f in self.pid_dir.glob("*.pid"):
            ad = f.stem
            sonuclar.append(self.durum(ad))
        return sonuclar

    @staticmethod
    def _pid_calisiyor(pid: int) -> bool:
        """PID canlı mı kontrol et."""
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    capture_output=True, text=True, timeout=5
                )
                return str(pid) in result.stdout
            except Exception:
                return False
        else:
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
