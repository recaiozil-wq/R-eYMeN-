"""force_restart_bots.py — T\u00fcm python process'lerini oldur, botlari temiz baslat."""
import os, subprocess, time, json, urllib.request

PROJE = "C:/Users/marko/Desktop/Reymen Proje/ReYMeN-Ajan"
HERMES_BASE = "C:/Users/marko/AppData/Local/hermes/profiles"

print("=" * 50)
print("ADIM 1: TUM PYTHON PROCESS'LERI OLDURULUYOR")
print("=" * 50)
subprocess.run(["taskkill", "/F", "/IM", "python.exe"], capture_output=True, timeout=5)
time.sleep(3)

print("ADIM 2: STALE GATEWAY STATE TEMIZLENIYOR")
for p in ["default", "kiral38", "reymen"]:
    for fname in ["gateway_state.json", "gateway.lock", "gateway.pid"]:
        f = f"{HERMES_BASE}/{p}/{fname}"
        if os.path.exists(f):
            os.remove(f)
            print(f"  Silindi: {f}")

print("ADIM 3: WEBHOOKLAR TEMIZLENIYOR")
for profil in ["default", "kiral38", "reymen"]:
    with open(f"{HERMES_BASE}/{profil}/.env") as f:
        token = ""
        for line in f:
            line = line.strip()
            if "TELEGRAM_BOT_TOKEN" in line and "=" in line:
                token = line.split("=", 1)[1].strip()
                break
    if token:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook"
        data = json.dumps({"drop_pending_updates": True}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            sonuc = json.loads(r.read())
        print(f"  {profil}: {'OK' if sonuc.get('ok') else 'FAIL'} webhook temiz")

print("ADIM 4: BOTLAR BASLATILIYOR")
venv_python = f"{PROJE}/venv/Scripts/python.exe"
script = f"{PROJE}/reymen/ag/telegram_bot.py"

bots = [
    ("Pasa_38", "default"),
    ("Kiral38", "kiral38"),
    ("ReYMeN_Bot", "reymen"),
]

for ad, profil in bots:
    with open(f"{HERMES_BASE}/{profil}/.env") as f:
        token = ""
        for line in f:
            line = line.strip()
            if "TELEGRAM_BOT_TOKEN" in line and "=" in line:
                token = line.split("=", 1)[1].strip()
                break

    if not token:
        print(f"  [{ad}] TOKEN YOK!")
        continue

    env = os.environ.copy()
    env["TELEGRAM_BOT_TOKEN"] = token
    env["HERMES_PROFILE"] = profil
    env["HERMES_GATEWAY"] = "http"

    log_path = f"{PROJE}/.ReYMeN/{ad.lower()}_bot.log"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w") as lf:
        lf.write(f"[{time.strftime('%H:%M:%S')}] {ad} baslatiliyor...\n")

    subprocess.Popen(
        [venv_python, script],
        env=env, cwd=PROJE,
        stdout=open(log_path, "a"),
        stderr=subprocess.STDOUT,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
    )
    print(f"  [{ad}] Baslatildi (token son 6: ...{token[-6:]})")
    time.sleep(2)

print("\nADIM 5: 12sn BEKLE, LOG KONTROL")
time.sleep(12)

print("ADIM 6: DURUM RAPORU")
for ad, profil in bots:
    log_path = f"{PROJE}/.ReYMeN/{ad.lower()}_bot.log"
    with open(log_path) as f:
        content = f.read()
    lines = content.strip().splitlines()
    last = lines[-1] if lines else "(bos)"
    count = len(lines)

    # Check errors
    has_error = any(w in content for w in ["ERROR", "Hata", "409", "Traceback"])
    has_running = "Polling basliyor" in content
    status = "🔴 HATA" if has_error else "✅ CALISIYOR"
    detail = " (polling aktif)" if has_running else ""
    print(f"  {status} {ad}{detail} - {count} satir - son: {last[:90]}")

print("\nBitti. Telegram'dan botlara mesaj atip test edebilirsin.")
print(f"PID: {os.getpid()} (bu script)")
