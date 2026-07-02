"""_handle_footer_command handler."""

from src.reymen.sistem.cli_stream import save_config_value
from src.reymen.sistem.cli_display import _cprint


def _handle_footer_command(cli, cmd_original: str) -> None:
    """Toggle or inspect ``display.runtime_footer.enabled`` from the CLI.

    Usage:
        /footer           → toggle
        /footer on|off    → explicit
        /footer status    → show current state
    """
    from reymen.reymen_cli.config import load_config
    from reymen.reymen_cli.colors import Colors as _Colors

    # Parse arg
    arg = ""
    try:
        parts = (cmd_original or "").strip().split(None, 1)
        if len(parts) > 1:
            arg = parts[1].strip().lower()
    except Exception:
        arg = ""

    cfg = load_config() or {}
    footer_cfg = ((cfg.get("display") or {}).get("runtime_footer") or {})
    current = bool(footer_cfg.get("enabled", False))
    fields = footer_cfg.get("fields") or ["model", "context_pct", "cwd"]

    if arg in {"status", "?"}:
        state = "ON" if current else "OFF"
        _cprint(
            f"  {_Colors.BOLD}Runtime footer:{_Colors.RESET} {state}\n"
            f"  Fields: {', '.join(fields)}"
        )
        return

    if arg in {"on", "enable", "true", "1"}:
        new_state = True
    elif arg in {"off", "disable", "false", "0"}:
        new_state = False
    elif arg == "":
        new_state = not current
    else:
        _cprint("  Usage: /footer [on|off|status]")
        return

    if save_config_value("display.runtime_footer.enabled", new_state):
        state = (
            f"{_Colors.GREEN}ON{_Colors.RESET}" if new_state
            else f"{_Colors.DIM}OFF{_Colors.RESET}"
        )
        _cprint(f"  Runtime footer: {state}")
    else:
        _cprint("  Failed to save runtime_footer setting to config.yaml")
