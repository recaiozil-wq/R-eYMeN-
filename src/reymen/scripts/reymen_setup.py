"""
ReYMeN Otomatik Kurulum ve Fix Scripti
VSCode terminalde calistir: python reymen_setup.py
"""

import subprocess
import sys
import os
from pathlib import Path

# ── RENK KODLARI ──────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def log(msg):   print(f"{GREEN}{BOLD}[✓]{RESET} {msg}")
def warn(msg):  print(f"{YELLOW}{BOLD}[!]{RESET} {msg}")
def err(msg):   print(f"{RED}{BOLD}[✗]{RESET} {msg}")
def info(msg):  print(f"{BLUE}{BOLD}[→]{RESET} {msg}")

def run(cmd, cwd=None):
    """Komutu calistir, sonucu don."""
    info(f"Calistiriliyor: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, cwd=cwd,
            capture_output=False, text=True,
            encoding="utf-8", errors="replace"
        )
        return result
    except FileNotFoundError as e:
        err(f"Komut bulunamadi: {e}")
        return subprocess.CompletedProcess(args=cmd, returncode=-1, stdout="", stderr=str(e))

# ── PROJE YOLU ────────────────────────────────────────────────
PROJE = Path(r"C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan")

# Eğer script proje içinden çalışıyorsa otomatik algıla
if not PROJE.exists():
    PROJE = Path(__file__).parent.resolve()
    warn(f"Varsayilan yol bulunamadi, mevcut dizin kullaniliyor: {PROJE}")

VENV     = PROJE / "venv"
PIP      = VENV / "Scripts" / "pip.exe"
PYTHON   = VENV / "Scripts" / "python.exe"
REQ      = PROJE / "requirements.txt"
OTONOM   = PROJE / "reymen" / "_otonom_fix.py"
TESTS    = PROJE / "tests"

def main():
    print(f"\n{'='*55}")
    print(f"  {BOLD}ReYMeN Otomatik Kurulum & Fix{RESET}")
    print(f"{'='*55}\n")
    print(f"Proje yolu: {PROJE}\n")

    # ── ADIM 1: Proje var mı? ─────────────────────────────────
    info("ADIM 1/5 — Proje dizini kontrol...")
    if not PROJE.exists():
        err(f"Proje dizini bulunamadi: {PROJE}")
        err("PROJE degiskenini duzenleyip tekrar calistir.")
        sys.exit(1)
    log("Proje dizini bulundu")

    # ── ADIM 2: Venv var mı / oluştur ────────────────────────
    info("ADIM 2/5 — Venv kontrol / kurulum...")
    if not VENV.exists():
        warn("Venv bulunamadi, olusturuluyor...")
        r = run([sys.executable, "-m", "venv", str(VENV)], cwd=PROJE)
        if r.returncode != 0:
            err("Venv olusturulamadi!")
            sys.exit(1)
        log("Venv olusturuldu")
    else:
        log("Venv mevcut")

    # ── ADIM 3: pip install requirements ──────────────────────
    info("ADIM 3/5 — Bagimliliklar yukleniyor...")
    if not REQ.exists():
        warn("requirements.txt bulunamadi, bu adim atlaniyor")
    else:
        r = run([str(PYTHON), "-m", "pip", "install", "-r", str(REQ)], cwd=PROJE)
        if r.returncode == 0:
            log("Bagimliliklar yuklendi")
        else:
            warn("Bazi bagimliliklar yuklenemedi, devam ediliyor...")

    # ── ADIM 4: _otonom_fix.py ────────────────────────────────
    info("ADIM 4/5 — _otonom_fix.py calistiriliyor...")
    if not OTONOM.exists():
        warn(f"_otonom_fix.py bulunamadi: {OTONOM}")
        warn("Bu adim atlaniyor")
    else:
        # Önce dry-run
        info("  → Dry-run (onizleme)...")
        r = run([str(PYTHON), str(OTONOM), "--dry-run"], cwd=PROJE)

        # Kullanicidan onay al
        print()
        try:
            cevap = input(f"{YELLOW}{BOLD}[?]{RESET} Fix uygulansin mi? (e/h): ").strip().lower()
        except (EOFError, OSError):
            cevap = "e"
            warn("Terminal interaktif degil, otomatik devam...")
        if cevap in ("e", "evet", "y", "yes"):
            r = run([str(PYTHON), str(OTONOM)], cwd=PROJE)
            if r.returncode == 0:
                log("_otonom_fix.py basariyla tamamlandi")
            else:
                warn("_otonom_fix.py hata ile bitti, testlere devam ediliyor...")
        else:
            warn("Fix atlandi")

    # ── ADIM 5: Testler ───────────────────────────────────────
    info("ADIM 5/5 — Testler calistiriliyor...")
    if not TESTS.exists():
        warn("tests/ klasoru bulunamadi")
    else:
        r = run([
            str(PYTHON), "-m", "pytest",
            "tests/",
            "-x", "--tb=short",
            "--ignore=tests/ReYMeN_reference"
        ], cwd=PROJE)

        print()
        if r.returncode == 0:
            log("TUM TESTLER GECTI! ✓")
        else:
            warn("Bazi testler basarisiz. Yukaridaki ciktiya bak.")

    # ── OZET ──────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  {BOLD}Islem tamamlandi{RESET}")
    print(f"{'='*55}")
    print(f"  Proje : {PROJE}")
    print(f"  Python: {PYTHON}")
    print(f"{'='*55}\n")

if __name__ == "__main__":
    main()
