# -*- coding: utf-8 -*-
"""cli_commands.py — ReYMeN CLI alt komutları (gateway, config, session, doctor, backup)."""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

_KOK = Path(__file__).parent.parent.parent.resolve()

# ── Renkler ────────────────────────────────────────────────────────────────────
_R   = "\033[0m"
_C   = "\033[96m"
_G   = "\033[92m"
_Y   = "\033[93m"
_B   = "\033[94m"
_M   = "\033[95m"
_D   = "\033[2m"
_RED = "\033[91m"

def _c(t):   return f"{_C}{t}{_R}"
def _g(t):   return f"{_G}{t}{_R}"
def _y(t):   return f"{_Y}{t}{_R}"
def _d(t):   return f"{_D}{t}{_R}"
def _r(t):   return f"{_RED}{t}{_R}"


# ── GATEWAY (ReYMeN bagimsiz) ─────────────────────────────────────────────────
def cmd_gateway(args) -> int:
    """Gateway yönetimi — ReYMeN kendi gateway sistemi."""
    alt = args.sub or "status"
    profil = getattr(args, "profil", None) or "reymen"

    if alt == "list":
        profiller = ["default", "reymen", "kiral38"]
        for p in profiller:
            _gateway_durum(p)
        return 0

    if alt == "status":
        return _gateway_durum(profil)
    if alt == "start":
        return _gateway_baslat(profil)
    if alt == "stop":
        return _gateway_durdur(profil)
    if alt == "restart":
        _gateway_durdur(profil)
        time.sleep(1)
        return _gateway_baslat(profil)

    print(f"  {_r('[HATA]')} Bilinmeyen gateway alt komutu: {alt}")
    return 1


def _gateway_durum(profil: str) -> int:
    """ReYMeN gateway durumunu kontrol et — process + PID bazli."""
    # 1. Process kontrolu (reymen gateway / telegram_bot)
    try:
        # Telegram bot process'i var mi?
        r = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
        )
        # reymen ile ilgili python process'lerini bul
        reymen_pids = []
        for line in r.stdout.splitlines():
            if "reymen" in line.lower() or "telegram" in line.lower():
                parts = line.split(",")
                if len(parts) >= 2:
                    pid = parts[1].strip('"')
                    reymen_pids.append(pid)

        if reymen_pids:
            print(f"  {_c('⊡')} {_g(profil):<10} {_g('calisiyor')} PID: {', '.join(reymen_pids[:3])}")
        else:
            print(f"  {_c('⊡')} {_y(profil):<10} {_d('kapali')}")
        return 0
    except Exception as e:
        print(f"  {_c('⊡')} {_y(profil):<10} {_d('kontrol basarisiz')}")
        return 1


def _gateway_baslat(profil: str) -> int:
    """ReYMeN gateway'ini baslat — dogrudan Python process'i olarak."""
    try:
        # reymen_launcher.py uzerinden gateway baslat
        reymen_bin = str(_KOK / "reymen_launcher.py")
        cmd = f'start /MIN cmd /c "python {reymen_bin} --profil {profil} gateway start"'
        subprocess.Popen(cmd, shell=True)
        print(f"  {_g('✓')} {profil} gateway baslatiliyor...")
        return 0
    except Exception as e:
        print(f"  {_r('[HATA]')} {e}")
        return 1


def _gateway_durdur(profil: str) -> int:
    """ReYMeN gateway process'lerini durdur."""
    try:
        # reymen ile ilgili python process'lerini bul ve oldur
        r = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
        )
        for line in r.stdout.splitlines():
            if "reymen" in line.lower() or "telegram" in line.lower():
                parts = line.split(",")
                if len(parts) >= 2:
                    pid = parts[1].strip('"')
                    subprocess.run(["taskkill", "/F", "/PID", pid],
                                   capture_output=True, timeout=3)
        print(f"  {_g('✓')} Gateway process'leri durduruldu.")
        return 0
    except Exception as e:
        print(f"  {_y('!')} Durdurma hatasi: {e}")
        return 1


# ── CONFIG ──────────────────────────────────────────────────────────────────────
def cmd_config(args) -> int:
    """Config goruntuleme."""
    alt = getattr(args, "sub", None) or "show"

    if alt == "show":
        return _config_goster()
    if alt == "path":
        print(str(_KOK / "config.yaml"))
        return 0
    if alt == "env":
        return _config_env_goster()

    print(f"  {_r('[HATA]')} Bilinmeyen config alt komutu: {alt}")
    return 1


def _config_goster() -> int:
    yaml_yol = _KOK / "config.yaml"
    if not yaml_yol.exists():
        print(f"  {_y('!')} config.yaml bulunamadi: {yaml_yol}")
        return 1
    icerik = yaml_yol.read_text(encoding="utf-8", errors="replace")
    # Hassas bilgileri temizle
    import re
    icerik = re.sub(r'(api_key|token|password|secret):\s*["\']?[^"\'\n]+["\']?',
                    r'\1: ***', icerik, flags=re.IGNORECASE)
    print(icerik)
    return 0


def _config_env_goster() -> int:
    """Aktif .evn degiskenlerini goster (sifreleri gizle)."""
    import re
    env_yol = _KOK / ".env"
    if not env_yol.exists():
        print(f"  {_y('!')} .env bulunamadi")
        return 1
    for satir in env_yol.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#"):
            continue
        if "=" in satir:
            key, val = satir.split("=", 1)
            if any(k in key.upper() for k in ["API_KEY", "TOKEN", "SECRET", "PASSWORD"]):
                val = "***" if val else ""
            print(f"  {key}={val}")
    return 0


# ── SESSION ─────────────────────────────────────────────────────────────────────
def cmd_session(args) -> int:
    """Session listeleme."""
    alt = getattr(args, "sub", None) or "list"

    if alt == "list":
        return _session_listele(getattr(args, "limit", 10))
    if alt == "last":
        return _session_son()

    print(f"  {_r('[HATA]')} Bilinmeyen session alt komutu: {alt}")
    return 1


def _session_listele(limit: int = 10) -> int:
    """~/.hermes/reymen/state.db'den son session'lari listele."""
    import sqlite3
    db_yollari = [
        _KOK / ".ReYMeN" / "state.db",
        Path.home() / "AppData" / "Local" / "reymen" / "profiles" / "reymen" / "state.db",
        Path.home() / "AppData" / "Local" / "reymen" / "state.db",
    ]
    for db in db_yollari:
        if db.exists():
            try:
                conn = sqlite3.connect(str(db))
                cur = conn.cursor()
                cur.execute(
                    "SELECT session_id, created_at, message_count FROM sessions "
                    "ORDER BY created_at DESC LIMIT ?", (limit,)
                )
                rows = cur.fetchall()
                conn.close()
                if rows:
                    for sid, ts, cnt in rows:
                        print(f"  {_c('◈')} {_g(sid[:12]):<14} "
                              f"{_d(str(ts)[:19]):<22} {cnt} mesaj")
                    return 0
            except Exception as e:
                logger.warning("[CliCommands] except Exception (L209): %s", Exception)
                pass

    print(f"  {_y('!')} Session kaydi bulunamadi")
    return 1


def _session_son() -> int:
    return _session_listele(1)


# ── DOCTOR ──────────────────────────────────────────────────────────────────────
def cmd_doctor(args) -> int:
    """Sistem saglik kontrolu."""
    sorun = 0
    print(f"\n  {_c('ReYMeN Sistem Kontrolü')}")
    print(f"  {_d('─'*50)}")

    # 1. Proje dizini
    if _KOK.exists():
        print(f"  {_g('✓')} Proje: {_KOK}")
    else:
        print(f"  {_r('✗')} Proje bulunamadi")
        sorun += 1

    # 2. .env
    env = _KOK / ".env"
    print(f"  {_g('✓') if env.exists() else _r('✗')} .env: {'var' if env.exists() else 'YOK'}")

    # 3. config.yaml
    yaml = _KOK / "config.yaml"
    print(f"  {_g('✓') if yaml.exists() else _y('?')} config.yaml: {'var' if yaml.exists() else 'yok'}")

    # 4. API key test
    import http.client as _hc
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if deepseek_key:
        try:
            conn = _hc.HTTPSConnection("api.deepseek.com", timeout=3)
            conn.request("GET", "/v1/models", headers={"Authorization": f"Bearer {deepseek_key}"})
            resp = conn.getresponse()
            ok = resp.status == 200
            conn.close()
            print(f"  {_g('✓') if ok else _r('✗')} DeepSeek API: {'calisiyor' if ok else f'hata {resp.status}'}")
        except Exception as e:
            print(f"  {_r('✗')} DeepSeek API: {_d(str(e)[:40])}")
            sorun += 1
    else:
        print(f"  {_r('✗')} DeepSeek API: KEY YOK")
        sorun += 1

    # 5. SOUL.md
    soul = _KOK / "SOUL.md"
    if soul.exists():
        s_len = len(soul.read_text(encoding="utf-8"))
        print(f"  {_g('✓')} SOUL.md: {s_len} karakter")
    else:
        print(f"  {_y('?')} SOUL.md: yok")

    # 6. ConversationLoop
    try:
        from reymen.cereyan.conversation_loop import ConversationLoop
        print(f"  {_g('✓')} ConversationLoop: hazir")
    except Exception as e:
        print(f"  {_r('✗')} ConversationLoop: {e}")
        sorun += 1

    # 7. ReYMeN binary
    reymen = str(_KOK / "reymen_launcher.py")
    print(f"  {_g('✓') if os.path.exists(reymen) else _y('?')} Launcher: {'reymen_launcher.py' if os.path.exists(reymen) else 'bulunamadi'}")

    print(f"  {_d('─'*50)}")
    if sorun:
        print(f"  {_r(f'{sorun} sorun bulundu')}")
    else:
        print(f"  {_g('✓ Tum kontroller basarili')}")
    print()
    return sorun


# ── BACKUP ──────────────────────────────────────────────────────────────────────
def cmd_backup(args) -> int:
    """Git push ile yedekle."""
    alt = getattr(args, "sub", None) or "status"

    if alt == "status":
        return _backup_durum()
    if alt == "push":
        return _backup_push()
    if alt == "log":
        return _backup_log()

    print(f"  {_r('[HATA]')} Bilinmeyen backup alt komutu")
    return 1


def _backup_durum() -> int:
    try:
        import subprocess
        r = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(_KOK), capture_output=True, text=True, timeout=10
        )
        cikti = r.stdout.strip()
        if cikti:
            lines = cikti.splitlines()
            print(f"  {_y(f'{len(lines)}')} degisiklik bekliyor")
            for line in lines[:20]:
                print(f"    {_d(line)}")
        else:
            print(f"  {_g('✓')} Temiz (degisiklik yok)")
        return 0
    except Exception as e:
        print(f"  {_r('[HATA]')} {e}")
        return 1


def _backup_push() -> int:
    print(f"  {_c('∘')} Git push yapiliyor...")
    try:
        r = subprocess.run(
            ["git", "add", "-A"],
            cwd=str(_KOK), capture_output=True, text=True, timeout=30
        )
        r = subprocess.run(
            ["git", "commit", "-m", f"otomatik yedek [$(date +%Y-%m-%d_%H:%M)]"],
            cwd=str(_KOK), capture_output=True, text=True, timeout=30
        )
        r = subprocess.run(
            ["git", "push"],
            cwd=str(_KOK), capture_output=True, text=True, timeout=60
        )
        out = (r.stdout + r.stderr).strip()
        if "Everything up-to-date" in out or r.returncode == 0:
            print(f"  {_g('✓')} Yedeklendi")
        else:
            print(f"  {_y('!')} {out[:100]}")
        return r.returncode
    except Exception as e:
        print(f"  {_r('[HATA]')} {e}")
        return 1


def _backup_log() -> int:
    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            cwd=str(_KOK), capture_output=True, text=True, timeout=10
        )
        print(r.stdout.strip() or "Kayit yok")
        return 0
    except Exception as e:
        print(f"  {_r('[HATA]')} {e}")
        return 1
