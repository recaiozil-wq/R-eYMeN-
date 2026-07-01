#!/usr/bin/env python
"""Pasa_38 bot baslatici - token'i dosyadan okuyarak, profile override olmadan."""
import os, sys, subprocess
from pathlib import Path

token = Path("/tmp/pasa38_token.txt").read_text().strip()
proje = Path(__file__).resolve().parent

env = os.environ.copy()
env["TELEGRAM_BOT_TOKEN"] = token
env["HERMES_PROFILE"] = "default"
env["HERMES_GATEWAY"] = "http"

proc = subprocess.Popen(
    [sys.executable, str(proje / "reymen" / "ag" / "telegram_bot.py")],
    env=env,
    cwd=str(proje),
    stdout=open(proje / ".ReYMeN" / "pasa38_log.txt", "w"),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
)
print(f"Pasa_38 baslatildi: PID={proc.pid}")
