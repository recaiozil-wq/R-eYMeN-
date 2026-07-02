"""
ReYMeN Web UI — Geriye uyumluluk shim'i.
Eski `from reymen.web_ui import baslat` çalışmaya devam etsin diye.
Yeni kod: reymen/web_ui/ paketinde.
"""

from src.reymen.web_ui.__init__ import app, baslat, cli, log_streamer, process_manager

__all__ = ["app", "baslat", "cli", "log_streamer", "process_manager"]
