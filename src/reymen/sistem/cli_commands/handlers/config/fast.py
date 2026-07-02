"""_handle_fast_command handler."""

from src.reymen.sistem.cli_stream import save_config_value
from src.reymen.sistem.cli_display import _cprint, _ACCENT, _RST, _DIM


def _handle_fast_command(cli, cmd: str):
    """Handle /fast — toggle fast mode (OpenAI Priority Processing / Anthropic Fast Mode)."""
    if not cli._fast_command_available():
        _cprint("  (._.) /fast is only available for models that support fast mode (OpenAI Priority Processing or Anthropic Fast Mode).")
        return

    # Determine the branding for the current model
    try:
        from reymen.reymen_cli.models import _is_anthropic_fast_model
        agent = getattr(cli, "agent", None)
        model = getattr(agent, "model", None) or getattr(cli, "model", None)
        feature_name = "Anthropic Fast Mode" if _is_anthropic_fast_model(model) else "Priority Processing"
    except Exception:
        feature_name = "Fast mode"

    parts = cmd.strip().split(maxsplit=1)
    if len(parts) < 2 or parts[1].strip().lower() == "status":
        status = "fast" if cli.service_tier == "priority" else "normal"
        _cprint(f"  {_ACCENT}{feature_name}: {status}{_RST}")
        _cprint(f"  {_DIM}Usage: /fast [normal|fast|status]{_RST}")
        return

    arg = parts[1].strip().lower()

    if arg in {"fast", "on"}:
        cli.service_tier = "priority"
        saved_value = "fast"
        label = "FAST"
    elif arg in {"normal", "off"}:
        cli.service_tier = None
        saved_value = "normal"
        label = "NORMAL"
    else:
        _cprint(f"  {_DIM}(._.) Unknown argument: {arg}{_RST}")
        _cprint(f"  {_DIM}Usage: /fast [normal|fast|status]{_RST}")
        return

    cli.agent = None  # Force agent re-init with new service-tier config
    if save_config_value("agent.service_tier", saved_value):
        _cprint(f"  {_ACCENT}✓ {feature_name} set to {label} (saved to config){_RST}")
    else:
        _cprint(f"  {_ACCENT}✓ {feature_name} set to {label} (session only){_RST}")
