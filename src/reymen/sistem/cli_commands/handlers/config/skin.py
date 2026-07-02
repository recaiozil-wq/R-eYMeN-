"""_handle_skin_command handler."""

from src.reymen.sistem.ReYMeN_constants import display_reymen_home
from src.reymen.sistem.cli_stream import save_config_value
from src.reymen.sistem.cli_display import _ACCENT


def _handle_skin_command(cli, cmd: str):
    """Handle /skin [name] — show or change the display skin."""
    try:
        from reymen.reymen_cli.skin_engine import list_skins, set_active_skin, get_active_skin_name
    except ImportError:
        print("Skin engine not available.")
        return

    parts = cmd.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        # Show current skin and list available
        current = get_active_skin_name()
        skins = list_skins()
        print(f"\n  Current skin: {current}")
        print("  Available skins:")
        for s in skins:
            marker = " ●" if s["name"] == current else "  "
            source = f" ({s['source']})" if s["source"] == "user" else ""
            print(f"   {marker} {s['name']}{source} — {s['description']}")
        print("\n  Usage: /skin <name>")
        print(f"  Custom skins: drop a YAML file in {display_reymen_home()}/skins/\n")
        return

    new_skin = parts[1].strip().lower()
    available = {s["name"] for s in list_skins()}
    if new_skin not in available:
        print(f"  Unknown skin: {new_skin}")
        print(f"  Available: {', '.join(sorted(available))}")
        return

    set_active_skin(new_skin)
    _ACCENT.reset()  # Re-resolve ANSI color for the new skin
    # _DIM is now a fixed dim+italic ANSI escape (terminal-default fg)
    # so it doesn't need re-resolving on skin switch.
    if save_config_value("display.skin", new_skin):
        print(f"  Skin set to: {new_skin} (saved)")
    else:
        print(f"  Skin set to: {new_skin}")
    print("  Note: banner colors will update on next session start.")
    if cli._apply_tui_skin_style():
        print("  Prompt + TUI colors updated.")
