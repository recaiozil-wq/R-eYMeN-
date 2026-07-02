"""start_bots.py — Tüm Telegram botlarini temiz baslat."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PROJE_KOK = Path(__file__).resolve().parent.parent.parent
HERMES_BASE = Path.home() / "AppData" / "Local" / "hermes" / "profiles"

BOTLAR = [
    {"ad": "Pasa_38", "profil": "default"},
    {"ad": "Kiral38", "profil": "kiral38"},
    {"ad": "ReYMeN_Bot", "profil": "reymen"},
]

def token_oku(profil):
    env_yolu = HERMES_BASE / profil / ".env"
    if not env_yolu.exists():
        return ""
    for satir in env_yolu.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if satir.startswith("TELEGRAM_BOT_TOKEN="):
            return satir.split("=", 1)[1]
    return ""

def bot_baslat(bot_info):
    """Tek bot baslat (DETACHED_PROCESS, no window)."""
    ad = bot_info["ad"]
    profil = bot_info["profil"]
    token = token_oku(profil)

    if not token:
        print(f"[{ad}] ❌ Token bulunamadi!")
        return False

    venv_python = PROJE_KOK / "venv" / "Scripts" / "python.exe"
    script = PROJE_KOK / "reymen" / "ag" / "telegram_bot.py"

    if not venv_python.exists():
        print(f"[{ad}] ❌ venv Python bulunamadi: {venv_python}")
        return False

    env = os.environ.copy()
    env["TELEGRAM_BOT_TOKEN"] = token
    env["HERMES_PROFILE"] = profil
    env["HERMES_GATEWAY"] = "http"

    log_yolu = PROJE_KOK / ".ReYMeN" / f"{ad.lower()}_bot.log"
    log_yolu.parent.mkdir(parents=True, exist_ok=True)

    with open(log_yolu, "w") as lf:
        lf.write(f"[{time.strftime('%H:%M:%S')}] {ad} baslatiliyor... (profil={profil})\n")

    proc = subprocess.Popen(
        [str(venv_python), str(script)],
        env=env,
        cwd=str(PROJE_KOK),
        stdout=open(log_yolu, "a"),
        stderr=subprocess.STDOUT,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
    )

    print(f"[{ad}] ✅ Baslatildi (PID: {proc.pid}) — token: ...{token[-6:]}")
    return True

def main():
    # Once tum eski botlari oldur
    print("=" * 50)
    print("ReYMeN Bot Supervisor — Temiz Baslatma")
    print("=" * 50)

    # Tum webhook'lari temizle
    print("\n1) Webhook temizleniyor...")
    for bot in BOTLAR:
        token = token_oku(bot["profil"])
        if token:
            import urllib.request
            url = f"https://api.telegram.org/bot{token}/deleteWebhook"
            data = json.dumps({"drop_pending_updates": True}).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    sonuc = json.loads(r.read())
                if sonuc.get("ok"):
                    print(f"  [{bot['ad']}] ✅ Webhook temiz")
                else:
                    print(f"  [{bot['ad']}] ⚠️ {sonuc}")
            except Exception as e:
                print(f"  [{bot['ad']}] ❌ {e}")

    # Botlari baslat
    print("\n2) Botlar baslatiliyor...")
    for bot in BOTLAR:
        bot_baslat(bot)
        time.sleep(2)

    # 5sn bekle, log kontrol
    print("\n3) Bekleniyor (8sn)...")
    time.sleep(8)

    print("\n4) Bot durumu:")
    for bot in BOTLAR:
        log_yolu = PROJE_KOK / ".ReYMeN" / f"{bot['ad'].lower()}_bot.log"
        if log_yolu.exists():
            with open(log_yolu) as f:
                icerik = f.read()
            son_satir = icerik.strip().splitlines()[-1] if icerik.strip() else "(bos)"
            print(f"  [{bot['ad']}] Son log: {son_satir[:120]}")

    print("\n" + "=" * 50)
    print("Tum botlar baslatildi.")
    print("Durdurmak icin: python start_bots.py --stop")
    print("=" * 50)

if __name__ == "__main__":
    if "--stop" in sys.argv:
        import wmi  # type: ignore
        c = wmi.WMI()
        killed = 0
        for proc in c.Win32_Process(name="python.exe"):
            cmd = proc.CommandLine or ""
            if "telegram_bot.py" in cmd:
                proc.Terminate()
                killed += 1
                print(f"  PID {proc.ProcessId} olduruldu")
        print(f"Toplam {killed} bot durduruldu.")
    else:
        main()
