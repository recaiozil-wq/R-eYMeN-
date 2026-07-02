"""_handle_copy_command handler."""

from src.reymen.sistem.cli_display import _cprint
from src.reymen.sistem.cli_helpers import _assistant_copy_text
import logging
logger = logging.getLogger(__name__)


def _handle_copy_command(cli, cmd_original: str) -> None:
    """Handle /copy [number] — copy assistant output to clipboard."""
    parts = cmd_original.split(maxsplit=1)
    arg = parts[1].strip() if len(parts) > 1 else ""

    assistant = [m for m in cli.conversation_history if m.get("role") == "assistant"]
    if not assistant:
        _cprint("  Nothing to copy yet.")
        return

    if arg:
        try:
            idx = int(arg) - 1
        except ValueError:
            _cprint("  Usage: /copy [number]")
            return
        if idx < 0 or idx >= len(assistant):
            _cprint(f"  Invalid response number. Use 1-{len(assistant)}.")
            return
    else:
        idx = len(assistant) - 1
        while idx >= 0 and not _assistant_copy_text(assistant[idx].get("content")):
            idx -= 1
        if idx < 0:
            _cprint("  Nothing to copy in assistant responses yet.")
            return

    text = _assistant_copy_text(assistant[idx].get("content"))
    if not text:
        _cprint("  Nothing to copy in that assistant response.")
        return

    try:
        cli._write_osc52_clipboard(text)
        _cprint(f"  Copied assistant response #{idx + 1} to clipboard")
    except Exception as e:
        _cprint(f"  Clipboard copy failed: {e}")
