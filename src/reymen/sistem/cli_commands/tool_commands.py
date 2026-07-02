"""Tool çağrı komutları — MixinCommands alt modülü.

Bu dosya otomatik olarak cli_mixin_commands.py'den ayrılmıştır.
MixinCommands sınıfının ilgili metotlarını içerir.
"""

import logging
import os
import re
import shutil
import sys
import textwrap
import time
import json
import math
import threading
import uuid
import base64
import atexit
import tempfile
from collections import deque
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class MixinCommands:
    """Tool çağrı komutları."""

    def _handle_tools_command(self, cmd: str):
        """Handle /tools [list|disable|enable] slash commands.

        Delegates to :func:`handlers.tools.tools_handler._handle_tools_command`.
        """
        from .handlers.tools.tools_handler import _handle_tools_command
        _handle_tools_command(self, cmd)

    def _handle_codex_runtime(self, cmd_original: str) -> None:
        """Handle /codex-runtime — toggle the codex app-server runtime opt-in.

        Delegates to :func:`handlers.tools.codex_runtime_handler._handle_codex_runtime`.
        """
        from .handlers.tools.codex_runtime_handler import _handle_codex_runtime
        _handle_codex_runtime(self, cmd_original)

    def _handle_cron_command(self, cmd: str):
        """Handle the /cron command to manage scheduled tasks.

        Delegates to :func:`handlers.tools.cron_handler._handle_cron_command`.
        """
        from .handlers.tools.cron_handler import _handle_cron_command
        _handle_cron_command(self, cmd)

    def _handle_curator_command(self, cmd: str):
        """Handle /curator slash command.

        Delegates to :func:`handlers.tools.curator_handler._handle_curator_command`.
        """
        from .handlers.tools.curator_handler import _handle_curator_command
        _handle_curator_command(self, cmd)

    def _handle_kanban_command(self, cmd: str):
        """Handle the /kanban command — delegate to the shared kanban CLI.

        Delegates to :func:`handlers.tools.kanban_handler._handle_kanban_command`.
        """
        from .handlers.tools.kanban_handler import _handle_kanban_command
        _handle_kanban_command(self, cmd)

    def _handle_skills_command(self, cmd: str):
        """Handle /skills slash command — delegates to ReYMeN_cli.skills_hub.

        Delegates to :func:`handlers.tools.skills_handler._handle_skills_command`.
        """
        from .handlers.tools.skills_handler import _handle_skills_command
        _handle_skills_command(self, cmd)

    def _handle_background_command(self, cmd: str):
        """Handle /background <prompt> — run a prompt in a separate background session.

        Delegates to :func:`handlers.tools.background_handler._handle_background_command`.
        """
        from .handlers.tools.background_handler import _handle_background_command
        _handle_background_command(self, cmd)

    def _try_launch_chrome_debug(port: int, system: str) -> bool:
        """Try to launch a Chromium-family browser with remote debugging enabled.

        Uses a dedicated user-data-dir so the debug instance doesn't conflict
        with an already-running browser using the default profile.

        Returns True if a launch command was executed (doesn't guarantee success).
        """
        from ReYMeN_cli.browser_connect import try_launch_chrome_debug
        return try_launch_chrome_debug(port, system)

    def _handle_bundles_command(self, cmd: str) -> None:
        """In-session ``/bundles`` — show installed skill bundles.

        Delegates to :func:`handlers.tools.bundles_handler._handle_bundles_command`.
        """
        from .handlers.tools.bundles_handler import _handle_bundles_command
        _handle_bundles_command(self, cmd)

    def _handle_browser_command(self, cmd: str):
        """Handle /browser connect|disconnect|status — manage live Chromium-family CDP connection.

        Delegates to :func:`handlers.tools.browser_handler._handle_browser_command`.
        """
        from .handlers.tools.browser_handler import _handle_browser_command
        _handle_browser_command(self, cmd)
