"""ReYMeN — Otonom görev çözücü çekirdeği.

Bu paket, görev 7 kapsamındaki 7 düşük öncelikli özelliği barındırır:

- ``cost_tracker``      : API harcama takibi + log
- ``platform_adapter``  : WSL/Kali adapter + path çevirici
- ``tui``               : Rich ile status bar, spinner, progress
- ``self_improve``      : Kalite metrikleri + otomatik iyileştirme
- ``kanban``            : Kart, kolon, öncelik, deadline
- ``video_tools``       : yt-dlp + ffmpeg wrapper
- ``a2a``               : Basit agent mesajlaşma (A2A prototip)
- ``problem_solver``    : Ajanın sorun çözme doğası (retry, fallback, öğrenme)
- ``learning_loop``     : Kendi kendine öğrenen çözüm bulma döngüsü

Her modül kendi başına çalışabilir ve opsiyonel bağımlılıkların yokluğunda
graceful fallback yapar.
"""

from __future__ import annotations

__version__ = "0.9.0"

# tools.xxx → reymen.tools.xxx import hook'u (Hermes bağımsızlık)
try:
    from reymen.tools import _importer  # noqa: F401 — otomatik hook kurar
except Exception:
    pass

__all__ = [
    "__version__",
    "cost_tracker",
    "platform_adapter",
    "tui",
    "self_improve",
    "kanban",
    "video_tools",
    "a2a",
    "problem_solver",
    "learning_loop",
]