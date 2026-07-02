"""ReYMeN Desktop uygulamasi (ust seviye API)."""
from __future__ import annotations
from src.reymen.desktop.server import WebServerManager, web_server
from src.reymen.desktop.autostart import AutoStartManager
from src.reymen.desktop.tray import run_tray

class DesktopApp:
    def __init__(self):
        self.server = web_server

    def start(self) -> str:
        return self.server.start()

    def stop(self) -> str:
        return self.server.stop()

    def restart(self) -> str:
        return self.server.restart()

    @property
    def status(self) -> str:
        return self.server.status

    @property
    def url(self) -> str:
        return self.server.url

    def tray(self):
        run_tray(self.server)

    def enable_autostart(self) -> str:
        return AutoStartManager.enable()

    def disable_autostart(self) -> str:
        return AutoStartManager.disable()

    def autostart_enabled(self) -> bool:
        return AutoStartManager.is_enabled()
