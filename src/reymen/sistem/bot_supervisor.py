# -*- coding: utf-8 -*-
"""
bot_supervisor.py — ReYMeN Bot Supervisor

3 botu baslatir, izler, crash'te restart eder.
Kullanim:
  python bot_supervisor.py          # Normal mod (izleme+restart)
  python bot_supervisor.py --once   # Sadece baslat, izleme yapma

Windows Startup icin:
  Bu script'i Windows baslangicina eklemek icin:
    1. WIN+R → shell:startup
    2. baslat_botlar.bat'yi buraya kopyala
"""

import os
import sys
import subprocess
import time
import json
import signal
from pathlib import Path
from datetime import datetime

# === AYARLAR ===
PROJE_KOK = Path(__file__).resolve().parent.parent.parent  # ReYMeN-Ajan/
BOT_PY = PROJE_KOK / "reymen" / "ag" / "telegram_bot.py"
DURUM_JSON = PROJE_KOK / "durum.json"
HERMES_PROFILES = Path.home() / "AppData" / "Local" / "hermes" / "profiles"

# Bot tanimlari: (adisyon, profil_adi, .env_yolu)
BOTLAR = [
    {
        "adisyon": "pasa_38",
        "profil": "default",
        "env": HERMES_PROFILES / "default" / ".env",
    },
    {
        "adisyon": "kiral38",
        "profil": "kiral38",
        "env": HERMES_PROFILES / "kiral38" / ".env",
    },
    {
        "adisyon": "reymen",
        "profil": "reymen",
        "env": HERMES_PROFILES / "reymen" / ".env",
    },
]


def _token_oku(env_path):
    """Profil .env'sinden TELEGRAM_BOT_TOKEN oku."""
    if not env_path.exists():
        return None
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("TELEGRAM_BOT_TOKEN") and "=" in line:
                return line.split("=", 1)[1].strip()
    return None


def bot_baslat(bot):
    """Bir bot process'ini baslat."""
    token = _token_oku(bot["env"])
    if not token:
        print(f"[{bot['adisyon']}] token bulunamadi: {bot['env']}")
        return None

    env = os.environ.copy()
    env["TELEGRAM_BOT_TOKEN"] = token
    env["HERMES_PROFILE"] = bot["profil"]
    env["HERMES_GATEWAY"] = "ai"

    try:
        p = subprocess.Popen(
            [sys.executable, str(BOT_PY)],
            env=env,
            cwd=str(PROJE_KOK),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        print(f"[{bot['adisyon']}] baslatildi (PID={p.pid})")
        return p
    except Exception as e:
        print(f"[{bot['adisyon']}] baslatma hatasi: {e}")
        return None


def durum_guncelle(processes):
    """Calisan botlari durum.json'a yansit."""
    data = {
        "proje": "ReYMeN Agent",
        "surum": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "botlar": {},
        "supervisor": {
            "calisiyor": True,
            "son_guncelleme": datetime.now().isoformat(),
            "aciklama": "bot_supervisor.py ile yonetiliyor",
        },
    }
    for bot in BOTLAR:
        pid = processes.get(bot["adisyon"], None)
        durum = "aktif" if pid else "pasif"
        data["botlar"][bot["adisyon"]] = {
            "profil": bot["profil"],
            "gateway": durum,
            "pid": pid,
            "yetki": "tam",
            "browser": "acik",
            "terminal": "acik",
            "web": "firecrawl",
        }
    with open(DURUM_JSON, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ana():
    once = "--once" in sys.argv
    print("=" * 50)
    print("ReYMeN Bot Supervisor")
    print(f"Baslatma: {datetime.now().isoformat()}")
    print(f"Mod: {'--once (izlemesiz)' if once else 'izleme+restart'}")
    print("=" * 50)

    # Process'leri tut
    processes = {}

    # Tum botlari baslat
    for bot in BOTLAR:
        p = bot_baslat(bot)
        if p:
            processes[bot["adisyon"]] = p

    # Durum.json'a yaz
    pids = {adisyon: p.pid if p else None for adisyon, p in processes.items()}
    durum_guncelle(pids)
    print(f"\n{DURUM_JSON} guncellendi.")

    if once:
        print("\n--once modu: cikiliyor. Botlar ayri process'lerde calisiyor.")
        return

    # Izleme dongusu
    print("\nIzleme basladi (30sn aralikla)...")
    while True:
        time.sleep(30)
        for bot in BOTLAR:
            ad = bot["adisyon"]
            p = processes.get(ad)
            if p and p.poll() is not None:
                # Crash'te restart
                print(f"[{ad}] CRASH (PID={p.pid}, kod={p.returncode}). Yeniden baslatiliyor...")
                yenisi = bot_baslat(bot)
                if yenisi:
                    processes[ad] = yenisi
        # Her 5 dk'da bir durum guncelle
        if int(time.time()) % 300 < 30:
            pids = {adisyon: p.pid if p else None for adisyon, p in processes.items()}
            durum_guncelle(pids)


if __name__ == "__main__":
    ana()
