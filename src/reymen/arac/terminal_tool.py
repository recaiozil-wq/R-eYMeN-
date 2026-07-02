#!/usr/bin/env python3
"""
ReYMeN Terminal Tool — Direkt PowerShell/Bash Komut Çalıştırıcı

Kullanım (CLI):
  python terminal_tool.py whoami
  python terminal_tool.py "ls -la"
  python terminal_tool.py --shell powershell "Get-Process"

Kullanım (Import):
  from arac.terminal_tool import terminal_calistir
import logging
logger = logging.getLogger(__name__)
  sonuc = terminal_calistir("python --version")
"""
import sys, os, subprocess, json, shlex, time
from pathlib import Path
from datetime import datetime

# ── Renkler ──────────────────────────────────────
class C:
    RED = "\033[91m"; YEL = "\033[93m"; GRN = "\033[92m"
    BLU = "\033[94m"; BOLD = "\033[1m"; RESET = "\033[0m"

# ── Hata Sınıfları ───────────────────────────────
class TerminalHatasi(Exception):
    """Terminal çalıştırma hatası."""
    pass

class TerminalTimeout(TerminalHatasi):
    """Komut timeout ile sonlandı."""
    pass


def terminal_calistir(
    komut: str,
    shell: str = "auto",
    timeout: int = 60,
    workdir: str = None,
    env_ek: dict = None,
) -> dict:
    """
    PowerShell veya Bash'te komut çalıştır.

    Parametreler:
        komut    : Çalıştırılacak komut (string)
        shell    : "auto" (otomatik), "powershell", "bash", "cmd"
        timeout  : Maksimum bekleme süresi (saniye)
        workdir  : Çalışma dizini (None = cwd)
        env_ek   : Ortam değişkeni ekle (dict)

    Dönüş:
        {
            "basarili": True/False,
            "cikti": "stdout + stderr",
            "exit_code": 0/1/...,
            "sure": 1.5,
            "shell": "powershell"
        }
    """

    t0 = time.time()

    # Shell otomatik tespit
    if shell == "auto":
        if sys.platform == "win32":
            shell = "powershell"
        else:
            shell = "bash"

    # Shell komut şablonu
    if shell == "powershell":
        cmd = ["powershell", "-NoProfile", "-Command", komut]
    elif shell == "cmd":
        cmd = ["cmd", "/c", komut]
    elif shell == "bash":
        cmd = ["bash", "-c", komut]
    else:
        raise TerminalHatasi(f"Bilinmeyen shell: {shell}")

    # Ortam değişkenleri
    env = os.environ.copy()
    if env_ek:
        env.update(env_ek)

    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir or os.getcwd(),
            env=env,
        )
        sure = round(time.time() - t0, 2)
        return {
            "basarili": r.returncode == 0,
            "cikti": r.stdout + r.stderr,
            "exit_code": r.returncode,
            "sure": sure,
            "shell": shell,
        }
    except subprocess.TimeoutExpired:
        raise TerminalTimeout(
            f"Komut {timeout}s içinde bitmedi: {komut[:60]}..."
        )
    except FileNotFoundError as e:
        raise TerminalHatasi(f"Shell bulunamadı: {e}")
    except Exception as e:
        raise TerminalHatasi(f"Terminal hatası: {e}")


def terminal_kaliteli_cikti(sonuc: dict) -> str:
    """Terminal sonucunu renkli ve düzenli göster."""
    c = sonuc
    renk = C.GRN if c["basarili"] else C.RED
    satirlar = [
        f"\n{C.BOLD}{'═'*50}{C.RESET}",
        f"  {C.BOLD}Shell:{C.RESET} {c.get('shell','?')}",
        f"  {C.BOLD}Süre:{C.RESET} {c.get('sure','?')}s",
        f"  {C.BOLD}Çıkış:{C.RESET} {renk}{c.get('exit_code','?')}{C.RESET}",
        f"  {C.BOLD}Durum:{C.RESET} {renk}{'✅ Başarılı' if c['basarili'] else '❌ Hata'}{C.RESET}",
        f"{C.BOLD}{'─'*50}{C.RESET}",
    ]
    if c.get("cikti"):
        satirlar.append(c["cikti"])
    satirlar.append(f"{C.BOLD}{'═'*50}{C.RESET}")
    return "\n".join(satirlar)


# ── CLI (Doğrudan Çalıştırma) ────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="ReYMeN Terminal Tool — PowerShell/Bash komut çalıştırıcı"
    )
    parser.add_argument("komut", nargs="*", help="Çalıştırılacak komut")
    parser.add_argument("--shell", default="auto",
                        choices=["auto", "powershell", "bash", "cmd"])
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--json", action="store_true",
                        help="Çıktıyı JSON formatında göster")
    parser.add_argument("--workdir", default=None)

    args = parser.parse_args()

    if not args.komut:
        # İnteraktif mod
        print(f"{C.BOLD}{C.BLU}ReYMeN Terminal Tool{C.RESET}")
        print(f"  {C.YEL}Çıkmak için: exit veya Ctrl+C{C.RESET}")
        print()
        while True:
            try:
                girilen = input(f"{C.GRN}❯{C.RESET} ").strip()
                if not girilen or girilen in ("exit", "quit", "q"):
                    break
                sonuc = terminal_calistir(
                    girilen, shell=args.shell,
                    timeout=args.timeout, workdir=args.workdir
                )
                if args.json:
                    print(json.dumps(sonuc, ensure_ascii=False, indent=2))
                else:
                    print(terminal_kaliteli_cikti(sonuc))
            except KeyboardInterrupt:
                print(f"\n{C.YEL}İptal edildi.{C.RESET}")
                break
            except (TerminalHatasi, TerminalTimeout) as e:
                print(f"{C.RED}❌ {e}{C.RESET}")
    else:
        # Tek komut modu
        try:
            komut_str = " ".join(args.komut)
            sonuc = terminal_calistir(
                komut_str, shell=args.shell,
                timeout=args.timeout, workdir=args.workdir
            )
            if args.json:
                print(json.dumps(sonuc, ensure_ascii=False, indent=2))
            else:
                print(terminal_kaliteli_cikti(sonuc))
        except (TerminalHatasi, TerminalTimeout) as e:
            print(f"{C.RED}❌ {e}{C.RESET}")
            sys.exit(1)
