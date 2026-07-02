"""_handle_reasoning_command handler."""

from src.reymen.sistem.cli_stream import save_config_value
from src.reymen.sistem.cli_display import _cprint, _ACCENT, _RST, _DIM
from src.reymen.sistem.cli_commands.base import _parse_reasoning_config


def _handle_reasoning_command(cli, cmd: str):
    """Handle /reasoning — manage effort level and display toggle.

    Usage:
        /reasoning              Show current effort level and display state
        /reasoning <level>      Set reasoning effort (none, minimal, low, medium, high, xhigh)
        /reasoning show|on      Show model thinking/reasoning in output
        /reasoning hide|off     Hide model thinking/reasoning from output
    """
    parts = cmd.strip().split(maxsplit=1)

    if len(parts) < 2:
        # Show current state
        rc = cli.reasoning_config
        if rc is None:
            level = "medium (default)"
        elif rc.get("enabled") is False:
            level = "none (disabled)"
        else:
            level = rc.get("effort", "medium")
        display_state = "on ✓" if cli.show_reasoning else "off"
        _cprint(f"  {_ACCENT}Reasoning effort:  {level}{_RST}")
        _cprint(f"  {_ACCENT}Reasoning display: {display_state}{_RST}")
        _cprint(f"  {_DIM}Usage: /reasoning <none|minimal|low|medium|high|xhigh|show|hide>{_RST}")
        return

    arg = parts[1].strip().lower()

    # Display toggle
    if arg in {"show", "on"}:
        cli.show_reasoning = True
        if cli.agent:
            cli.agent.reasoning_callback = cli._current_reasoning_callback()
        save_config_value("display.show_reasoning", True)
        _cprint(f"  {_ACCENT}✓ Reasoning display: ON (saved){_RST}")
        _cprint(f"  {_DIM}  Model thinking will be shown during and after each response.{_RST}")
        return
    if arg in {"hide", "off"}:
        cli.show_reasoning = False
        if cli.agent:
            cli.agent.reasoning_callback = cli._current_reasoning_callback()
        save_config_value("display.show_reasoning", False)
        _cprint(f"  {_ACCENT}✓ Reasoning display: OFF (saved){_RST}")
        return

    # Effort level change
    parsed = _parse_reasoning_config(arg)
    if parsed is None:
        _cprint(f"  {_DIM}(._.) Unknown argument: {arg}{_RST}")
        _cprint(f"  {_DIM}Valid levels: none, minimal, low, medium, high, xhigh{_RST}")
        _cprint(f"  {_DIM}Display:      show, hide{_RST}")
        return

    cli.reasoning_config = parsed
    cli.agent = None  # Force agent re-init with new reasoning config

    if save_config_value("agent.reasoning_effort", arg):
        _cprint(f"  {_ACCENT}✓ Reasoning effort set to '{arg}' (saved to config){_RST}")
    else:
        _cprint(f"  {_ACCENT}✓ Reasoning effort set to '{arg}' (session only){_RST}")
