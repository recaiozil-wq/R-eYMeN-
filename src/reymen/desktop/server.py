"""Web sunucu yoneticisi — soket bazli durum tespiti + arka plan process."""
from __future__ import annotations
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

PID_FILE = Path(__file__).resolve().parent / ".server_pid"


class WebServerManager:
    """Web UI sunucusu. Durumu port+pid dosyasi ile tespit eder."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        self.host = host
        self.port = port

    @property
    def status(self) -> str:
        if self._port_open():
            return "running"
        return "stopped"

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def uptime_seconds(self) -> float:
        return 0.0

    def _port_open(self) -> bool:
        try:
            with socket.create_connection((self.host, self.port), timeout=2):
                return True
        except (ConnectionRefusedError, OSError, TimeoutError):
            return False

    def _read_pid(self) -> int | None:
        if PID_FILE.exists():
            try:
                return int(PID_FILE.read_text().strip())
            except (ValueError, OSError):
                return None
        return None

    def _write_pid(self, pid: int):
        PID_FILE.write_text(str(pid))

    def _clear_pid(self):
        if PID_FILE.exists():
            PID_FILE.unlink()

    def start(self) -> str:
        """Web sunucusunu arka plan process'i olarak baslat."""
        if self._port_open():
            return f"[YESARROW] Zaten calisiyor: {self.url}"

        root = Path(__file__).resolve().parent.parent.parent
        python = sys.executable or "python"
        script = str(root / "reymen" / "desktop" / "_server_daemon.py")

        proc = subprocess.Popen(
            [python, script, str(self.host), str(self.port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(root),
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        self._write_pid(proc.pid)

        # Sunucunun hazir olmasini bekle
        for _ in range(30):
            time.sleep(0.5)
            if self._port_open():
                return f"[YESARROW] Sunucu basladi: {self.url}"

        # PID'yi kontrol et
        try:
            proc.poll()
            if proc.returncode is not None:
                return f"[CROSSMARK] Sunucu cikti (kod: {proc.returncode})"
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )
        return f"[WARNING] Sunucu baslatildi (port kontrolu gecikti): {self.url}"

    def stop(self) -> str:
        """Sunucuyu durdur (PID dosyasi + port)."""
        if not self._port_open():
            self._clear_pid()
            return "[INFO] Sunucu zaten durmus"

        pid = self._read_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                for _ in range(10):
                    time.sleep(0.5)
                    if not self._port_open():
                        self._clear_pid()
                        return "[YESARROW] Sunucu durduruldu"
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.5)
            except (OSError, ProcessLookupError) as _e:
                logger.warning("[Server] Dosya/klasor hatasi (L112): %s", OSError)
                pass

        # PID'siz de dene: port'tan process bul
        try:
            import psutil
            for conn in psutil.net_connections():
                if conn.laddr.port == self.port:
                    os.kill(conn.pid, signal.SIGTERM)
                    self._clear_pid()
                    return "[YESARROW] Sunucu durduruldu (psutil)"
        except ImportError as _e:
            logger.warning("[Server] Modul yuklenemedi (L123): %s", ImportError)
            pass

        self._clear_pid()
        return "[WARNING] Sunucu durdurulamadi, port acik kaldi"

    def restart(self) -> str:
        self.stop()
        time.sleep(1)
        return self.start()


web_server = WebServerManager()
