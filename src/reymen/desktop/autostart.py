"""Windows otomatik baslatma (Registry HKCU\Run)."""
from __future__ import annotations
import logging
import sys
from pathlib import Path
logger = logging.getLogger(__name__)
REG_VALUE = "ReYMeN Desktop"

class AutoStartManager:
    @staticmethod
    def _app_path() -> str:
        root = Path(__file__).resolve().parent.parent.parent
        python = sys.executable or "python"
        launcher = str(root / "reymen" / "desktop" / "launcher.py")
        return f'"{python}" "{launcher}" --tray'

    @classmethod
    def is_enabled(cls) -> bool:
        import winreg
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_READ) as k:
                val, _ = winreg.QueryValueEx(k, REG_VALUE)
                return val == cls._app_path()
        except (FileNotFoundError, OSError):
            return False

    @classmethod
    def enable(cls) -> str:
        import winreg
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_WRITE) as k:
                winreg.SetValueEx(k, REG_VALUE, 0, winreg.REG_SZ, cls._app_path())
            return "Otomatik baslatma etkin"
        except Exception as e:
            return f"Etkinlestirilemedi: {e}"

    @classmethod
    def disable(cls) -> str:
        import winreg
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_WRITE) as k:
                winreg.DeleteValue(k, REG_VALUE)
            return "Otomatik baslatma devre disi"
        except FileNotFoundError:
            return "Zaten kayitli degil"
        except Exception as e:
            return f"Kaldirilamadi: {e}"

    @classmethod
    def toggle(cls) -> str:
        if cls.is_enabled():
            return cls.disable()
        return cls.enable()
