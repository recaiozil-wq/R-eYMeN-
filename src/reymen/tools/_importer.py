"""ReYMeN tools import hook — `from tools.xxx import yyy` → `from reymen.tools.xxx import yyy`.

Bu modül, Hermes Agent'in `tools/` paketi yerine ReYMeN'in `reymen/tools/`
shim'lerinin kullanılmasını sağlar.

Kullanım (herhangi bir entry point'te bir kere):
    import reymen.tools._importer  # otomatik hook kurar
"""
from __future__ import annotations

import importlib
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# ReYMeN tools modüllerinin listesi (import hook ile yönlendirilecek)
_TOOLS_MODULES = {
    "tools.tts_tool",
    "tools.browser_tool",
    "tools.clarify_tool",
    "tools.execute_code_tool",
    "tools.send_message_tool",
    "tools.interrupt",
    "tools.schema_sanitizer",
    "tools.file_tools",
    "tools.macro",
    "tools.approval",
    "tools.tirith_security",
    "tools.computer_use_tool",
    "tools.terminal_tool",
    "tools.process_registry",
    "tools.todo_tool",
    "tools.achievements",
    "tools.skills_tool",
    "tools.skill_usage",
    "tools.checkpoint_manager",
    "tools.kanban_tools",
    "tools.delegate_tool",
    "tools.mcp_tool",
    "tools.cronjob_tools",
    "tools.environments.docker",
    "tools.environments.local",
    "tools.environments.modal",
    "tools.environments.wsl",
    "tools.web_tools",
    "tools.url_safety",
    "tools.website_policy",
    "tools.debug_helpers",
    "tools.lazy_deps",
    "tools.xai_http",
    "tools.vision_tools",
    "tools.voice_mode",
    "tools.image_generation_tool",
}


class _ToolsRedirectFinder:
    """Import hook: tools.xxx → reymen.tools.xxx ve reymen_cli → ReYMeN_cli."""

    def find_spec(self, fullname, path=None, target=None):
        # tools.xxx → reymen.tools.xxx
        if fullname in _TOOLS_MODULES:
            reymen_name = fullname.replace("tools.", "reymen.tools.", 1)
            try:
                return importlib.util.find_spec(reymen_name)
            except (ImportError, ValueError, AttributeError):
                return None

        # reymen_cli → ReYMeN_cli (editable finder bypass)
        if fullname == "reymen_cli" or fullname.startswith("reymen_cli."):
            # Önce sys.modules'te var mı kontrol et
            if fullname in sys.modules:
                return None  # Zaten yüklü, normal akışa devam et

            # reymen_cli → ReYMeN_cli, reymen_cli.xxx → ReYMeN_cli.xxx
            alt_name = fullname.replace("reymen_cli", "ReYMeN_cli", 1)
            try:
                spec = importlib.util.find_spec(alt_name)
                if spec is not None:
                    # Alt modülleri sys.modules'e kaydet (cycle önleme)
                    actual = importlib.import_module(alt_name)
                    sys.modules[fullname] = actual
                return spec
            except (ImportError, ValueError, AttributeError):
                return None

        # hermes_cli → ReYMeN_cli (Hermes bagimsizligi)
        if fullname == "hermes_cli" or fullname.startswith("hermes_cli."):
            if fullname in sys.modules:
                return None
            # hermes_cli → ReYMeN_cli, hermes_cli.xxx → ReYMeN_cli.xxx
            alt_name = fullname.replace("hermes_cli", "ReYMeN_cli", 1)
            try:
                spec = importlib.util.find_spec(alt_name)
                if spec is not None:
                    actual = importlib.import_module(alt_name)
                    sys.modules[fullname] = actual
                return spec
            except (ImportError, ValueError, AttributeError):
                return None

        return None


# Otomatik hook kurulumu
_installed = False


def install() -> None:
    """Import hook'unu sys.meta_path'e ekler."""
    global _installed
    if _installed:
        return

    finder = _ToolsRedirectFinder()
    sys.meta_path.insert(0, finder)
    _installed = True
    logger.debug("ReYMeN tools import hook installed (%d modules)", len(_TOOLS_MODULES))


# Modül yüklendiğinde otomatik kur
install()
