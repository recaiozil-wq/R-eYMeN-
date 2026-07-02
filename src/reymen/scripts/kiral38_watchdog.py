#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kiral38-watchdog: Sadece 409 conflict + gateway kontrolu (her 5 dk)."""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERMES = Path.home() / "AppData" / "Local" / "hermes"
KIRAL38 = HERMES / "profiles" / "kiral38"
PROJE = Path.home() / "Desktop" / "Reymen Proje" / "ReYMeN-Ajan"
BUGUN = datetime.now(timezone.utc)

rapor = []


def kontrol():
    # 1. Debug log'da 409 var mi?
    debug_log = PROJE / "bot_debug.log"
    if debug_log.exists():
        icerik = debug_log.read_text(encoding="utf-8", errors="ignore")
        conflict_say = icerik.count("409 Conflict")
        if conflict_say > 3:
            rapor.append(f"[WATCHDOG] kiral38: {conflict_say} kez 409 Conflict (log temizlendi)")
            debug_log.write_text("")

    # 2. gateway.lock temiz mi?
    lock = KIRAL38 / "gateway.lock"
    pidf = KIRAL38 / "gateway.pid"
    if lock.exists() and pidf.exists():
        try:
            pid = int(pidf.read_text().strip())
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, timeout=10
            )
            if str(pid) not in r.stdout:
                rapor.append(f"[WATCHDOG] kiral38 PID {pid} olmus, lock temizleniyor")
                lock.unlink(missing_ok=True)
                pidf.unlink(missing_ok=True)
        except:
            pass

    # 3. state.db boyut izle
    db = KIRAL38 / "state.db"
    if db.exists():
        mb = db.stat().st_size / 1024 / 1024
        if mb > 500:
            rapor.append(f"[WATCHDOG] kiral38 state.db {mb:.0f}MB (sinir: 500MB)")

    if rapor:
        print("\n".join(rapor))


if __name__ == "__main__":
    kontrol()
