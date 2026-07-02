#!/usr/bin/env python3
"""
ReYMeN Terminal Tool — Direkt PowerShell/Bash Komut Çalıştırıcı

Kullanım:
  python terminal_tool.py whoami
  python terminal_tool.py --shell powershell "dir"
  python terminal_tool.py --json "python --version"

Import:
  from terminal_tool import terminal_calistir
import logging
logger = logging.getLogger(__name__)
  sonuc = terminal_calistir("python --version")
"""
import sys, os, subprocess, json, time
from pathlib import Path

class C:
    RED="\033[91m"; YEL="\033[93m"; GRN="\033[92m"; BLU="\033[94m"; BOLD="\033[1m"; RESET="\033[0m"

class TerminalHatasi(Exception): pass
class TerminalTimeout(TerminalHatasi): pass

def terminal_calistir(komut, shell="auto", timeout=60, workdir=None, env_ek=None):
    t0 = time.time()
    if shell == "auto":
        shell = "powershell" if sys.platform == "win32" else "bash"

    if shell == "powershell":    cmd = ["powershell", "-NoProfile", "-Command", komut]
    elif shell == "cmd":         cmd = ["cmd", "/c", komut]
    elif shell == "bash":        cmd = ["bash", "-c", komut]
    else: raise TerminalHatasi(f"Bilinmeyen shell: {shell}")

    env = os.environ.copy()
    if env_ek: env.update(env_ek)

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=workdir or os.getcwd(), env=env)
        sure = round(time.time() - t0, 2)
        return {"basarili": r.returncode == 0, "cikti": r.stdout + r.stderr,
                "exit_code": r.returncode, "sure": sure, "shell": shell}
    except subprocess.TimeoutExpired:
        raise TerminalTimeout(f"Komut {timeout}s içinde bitmedi: {komut[:60]}")
    except Exception as e:
        raise TerminalHatasi(f"Terminal hatası: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ReYMeN Terminal Tool")
    parser.add_argument("komut", nargs="*")
    parser.add_argument("--shell", default="auto", choices=["auto","powershell","bash","cmd"])
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--workdir", default=None)
    args = parser.parse_args()

    if not args.komut:
        print(f"{C.BOLD}{C.BLU}ReYMeN Terminal Tool{C.RESET}\n  {C.YEL}exit ile çık{C.RESET}\n")
        while True:
            try:
                g = input(f"{C.GRN}❯{C.RESET} ").strip()
                if not g or g in ("exit","quit","q"): break
                s = terminal_calistir(g, args.shell, args.timeout, args.workdir)
                print(json.dumps(s, ensure_ascii=False, indent=2) if args.json else s.get("cikti",""))
            except KeyboardInterrupt: print(); break
            except (TerminalHatasi,TerminalTimeout) as e: print(f"{C.RED}❌ {e}{C.RESET}")
    else:
        try:
            s = terminal_calistir(" ".join(args.komut), args.shell, args.timeout, args.workdir)
            if args.json: print(json.dumps(s, ensure_ascii=False, indent=2))
            else: print(s.get("cikti",""))
        except (TerminalHatasi,TerminalTimeout) as e:
            print(f"{C.RED}❌ {e}{C.RESET}"); sys.exit(1)
