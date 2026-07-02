"""_handle_voice_command handler."""

from src.reymen.sistem.cli_display import _cprint, _DIM, _RST, _ACCENT


def _handle_voice_command(cli, command: str):
    """Handle /voice [on|off|tts|status] command."""
    parts = command.strip().split(maxsplit=1)
    subcommand = parts[1].lower().strip() if len(parts) > 1 else ""

    if subcommand == "on":
        cli._enable_voice_mode()
    elif subcommand == "off":
        cli._disable_voice_mode()
    elif subcommand == "tts":
        cli._toggle_voice_tts()
    elif subcommand == "status":
        cli._show_voice_status()
    elif subcommand == "":
        # Toggle
        if cli._voice_mode:
            cli._disable_voice_mode()
        else:
            cli._enable_voice_mode()
    else:
        _cprint(f"Unknown voice subcommand: {subcommand}")
        _cprint("Usage: /voice [on|off|tts|status]")
