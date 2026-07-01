"""bot_supervisor.py — ReYMeN Bot Supervisor.
3 bot'u 3 farkli token ile baslatir, crash'te restart eder.

Kullanim:
    python bot_supervisor.py              # 3 botu baslat (supervisor)
    python bot_supervisor.py --once       # Tek seferlik baslat
    python bot_supervisor.py --stop       # Tum botlari durdur
"""

import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from threading import Thread

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SUPERVISOR] %(message)s",
)
log = logging.getLogger("supervisor")

PROJE_KOK = Path(__file__).resolve().parent
HERMES_BASE = Path.home() / "AppData" / "Local" / "hermes" / "profiles"

# Proje .venv Python'unu kullan (uv yonetimli, tum bagimliliklari var)
_venv_py = str(PROJE_KOK / ".venv" / "Scripts" / "python.exe")
if Path(_venv_py).exists():
    PYTHON = _venv_py
else:
    # Fallback: su anki yorumlayici
    PYTHON = getattr(sys, "_base_executable", sys.executable)

BOTLAR = [
    {"ad": "Pasa_38",  "profil": "default", "env_anahtar": "TELEGRAM_BOT_TOKEN"},
    {"ad": "Kiral38",  "profil": "kiral38", "env_anahtar": "TELEGRAM_BOT_TOKEN"},
    {"ad": "ReYMeN_Bot", "profil": "reymen", "env_anahtar": "TELEGRAM_BOT_TOKEN"},
]


def token_oku(profil: str) -> str:
    """Profil .env'sinden TELEGRAM_BOT_TOKEN oku."""
    env_yolu = HERMES_BASE / profil / ".env"
    if not env_yolu.exists():
        log.warning("[%s] .env bulunamadi: %s", profil, env_yolu)
        return ""
    try:
        for satir in env_yolu.read_text(encoding="utf-8").splitlines():
            satir = satir.strip().replace("\r", "")
            if satir.startswith("TELEGRAM_BOT_TOKEN="):
                return satir.split("=", 1)[1]
    except Exception as e:
        log.error("[%s] Token okuma hatasi: %s", profil, e)
    return ""


class BotYonetici:
    """Tek bir bot process'ini yonetir + crash'te restart."""

    def __init__(self, bot_bilgi: dict):
        self.ad = bot_bilgi["ad"]
        self.profil = bot_bilgi["profil"]
        self.env_anahtar = bot_bilgi["env_anahtar"]
        self.process = None
        self.durduruldu = False

    def baslat(self):
        """Bot process'ini baslat."""
        token = token_oku(self.profil)
        if not token:
            log.error("[%s] Token bulunamadi! Baslatilamiyor.", self.ad)
            return False

        env = os.environ.copy()
        env["TELEGRAM_BOT_TOKEN"] = token
        env["HERMES_PROFILE"] = self.profil
        env["HERMES_GATEWAY"] = "ai"

        script = str(PROJE_KOK / "reymen" / "ag" / "telegram_bot.py")

        log.info("[%s] Baslatiliyor... (python: %s, token: ...%s)", self.ad, PYTHON, token[-6:])
        self.process = subprocess.Popen(
            [PYTHON, script],
            env=env,
            cwd=str(PROJE_KOK),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # Log dinleme thread'i
        def _log_dinle():
            for satir in self.process.stdout:
                if self.durduruldu:
                    break
                print(f"[{self.ad}] {satir.decode('utf-8', errors='replace').strip()}")

        Thread(target=_log_dinle, daemon=True).start()
        return True

    def durdur(self):
        """Bot'u durdur."""
        self.durduruldu = True
        if self.process and self.process.poll() is None:
            log.info("[%s] Durduruluyor...", self.ad)
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            log.info("[%s] Durduruldu.", self.ad)

    def restart(self):
        """Bot'u yeniden baslat."""
        self.durdur()
        time.sleep(2)
        self.durduruldu = False
        return self.baslat()


def supervisor():
    """Ana supervisor dongusu — 3 bot, crash'te restart."""
    yoneticiler = [BotYonetici(b) for b in BOTLAR]

    def _sinyal_handler(sig, frame):
        log.info("Sinyal alindi, botlar durduruluyor...")
        for y in yoneticiler:
            y.durdur()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sinyal_handler)
    signal.signal(signal.SIGTERM, _sinyal_handler)

    # Tum botlari baslat
    for y in yoneticiler:
        y.baslat()
        time.sleep(1)

    log.info("=" * 50)
    log.info("3 bot baslatildi. Supervisor aktif.")
    log.info("Durdurmak icin: Ctrl+C")
    log.info("=" * 50)

    # Crash kontrol dongusu
    while True:
        time.sleep(5)
        for y in yoneticiler:
            if y.durduruldu:
                continue
            if y.process and y.process.poll() is not None:
                log.warning("[%s] Crash! (exit: %d) 5sn sonra restart...",
                            y.ad, y.process.returncode)
                time.sleep(5)
                y.baslat()


def main():
    if "--stop" in sys.argv:
        import subprocess as sp
        result = sp.run(
            ["wmic", "process", "where", 'name="python.exe"',
             "get", "ProcessId,CommandLine", "/format:csv"],
            capture_output=True, text=True, timeout=10
        )
        killed = 0
        for line in result.stdout.split("\n"):
            if "telegram_bot.py" in line or "bot_supervisor" in line:
                parts = line.split(",")
                if len(parts) >= 2:
                    pid = parts[1].strip()
                    if pid.isdigit():
                        sp.run(["taskkill", "/f", "/pid", pid],
                               capture_output=True, timeout=5)
                        killed += 1
                        print(f"  PID {pid} olduruldu")
        print(f"Toplam {killed} bot process'i durduruldu.")
        return

    if "--once" in sys.argv:
        for bot in BOTLAR:
            token = token_oku(bot["profil"])
            if not token:
                print(f"[{bot['ad']}] Token yok, atlaniyor.")
                continue
            env = os.environ.copy()
            env["TELEGRAM_BOT_TOKEN"] = token
            env["HERMES_PROFILE"] = bot["profil"]
            env["HERMES_GATEWAY"] = "ai"
            script = str(PROJE_KOK / "reymen" / "ag" / "telegram_bot.py")
            subprocess.Popen(
                [PYTHON, script],
                env=env, cwd=str(PROJE_KOK),
                stdout=open(PROJE_KOK / ".ReYMeN" / f"{bot['ad'].lower()}_bot.log", "w"),
                stderr=subprocess.STDOUT,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            )
            print(f"[{bot['ad']}] Baslatildi (arka planda). python: {PYTHON}")
            time.sleep(2)
        return

    supervisor()


if __name__ == "__main__":
    main()
