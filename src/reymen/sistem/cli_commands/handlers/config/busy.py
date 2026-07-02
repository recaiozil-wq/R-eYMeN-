"""_handle_busy_command handler."""

from src.reymen.sistem.cli_stream import save_config_value
from src.reymen.sistem.cli_display import _cprint, _ACCENT, _RST, _DIM


def _handle_busy_command(cli, cmd: str):
    """Handle /busy — control what Enter does while ReYMeN is working.

    Usage:
        /busy               Show current busy input mode
        /busy status        Show current busy input mode
        /busy queue         Queue input for the next turn instead of interrupting
        /busy steer         Inject Enter mid-run via /steer (after next tool call)
        /busy interrupt     Interrupt the current run on Enter (default)
    """
    parts = cmd.strip().split(maxsplit=1)
    if len(parts) < 2 or parts[1].strip().lower() == "status":
        _cprint(f"  {_ACCENT}Busy input mode: {cli.busy_input_mode}{_RST}")
        if cli.busy_input_mode == "queue":
            _behavior = "queues for next turn"
        elif cli.busy_input_mode == "steer":
            _behavior = "steers into current run (after next tool call)"
        else:
            _behavior = "interrupts current run"
        _cprint(f"  {_DIM}Enter while busy: {_behavior}{_RST}")
        _cprint(f"  {_DIM}Usage: /busy [queue|steer|interrupt|status]{_RST}")
        return

    arg = parts[1].strip().lower()
    if arg not in {"queue", "interrupt", "steer"}:
        _cprint(f"  {_DIM}(._.) Unknown argument: {arg}{_RST}")
        _cprint(f"  {_DIM}Usage: /busy [queue|steer|interrupt|status]{_RST}")
        return

    cli.busy_input_mode = arg
    if save_config_value("display.busy_input_mode", arg):
        if arg == "queue":
            behavior = "Enter will queue follow-up input while ReYMeN is busy."
        elif arg == "steer":
            behavior = "Enter will steer your message into the current run (after the next tool call)."
        else:
            behavior = "Enter will interrupt the current run while ReYMeN is busy."
        _cprint(f"  {_ACCENT}✓ Busy input mode set to '{arg}' (saved to config){_RST}")
        _cprint(f"  {_DIM}{behavior}{_RST}")
    else:
        _cprint(f"  {_ACCENT}✓ Busy input mode set to '{arg}' (session only){_RST}")
