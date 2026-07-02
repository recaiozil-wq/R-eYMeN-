#!/usr/bin/env python3
"""ReYMeN Desktop CLI — baslat/durdur/durum/tray."""
from __future__ import annotations
import sys
from src.reymen.desktop.server import web_server
from src.reymen.desktop.autostart import AutoStartManager

def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Kullanim: reymen-desktop [komut]")
        print("  start        Web sunucusunu baslat")
        print("  stop         Web sunucusunu durdur")
        print("  restart      Web sunucusunu yeniden baslat")
        print("  status       Durum bilgisi")
        print("  tray         Sistem tepsisi modu (arka plan)")
        print("  autostart    Windows baslangic kaydini ac/kapat")
        return

    cmd = args[0]

    if cmd == "start":
        print(web_server.start())
    elif cmd == "stop":
        print(web_server.stop())
    elif cmd == "restart":
        print(web_server.restart())
    elif cmd == "status":
        s = web_server.status
        print(f"Durum: {s}")
        if s == "running":
            print(f"URL: {web_server.url}")
            # Uptime: port-based, gosterilmiyor
        print(f"Auto-start: {'Aktif' if AutoStartManager.is_enabled() else 'Pasif'}")
    elif cmd == "tray":
        from reymen.desktop.tray import run_tray
        print("Sistem tepsisi baslatiliyor...")
        run_tray(web_server)
    elif cmd == "autostart":
        if AutoStartManager.is_enabled():
            print(AutoStartManager.disable())
        else:
            print(AutoStartManager.enable())
    else:
        print(f"Bilinmeyen komut: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
