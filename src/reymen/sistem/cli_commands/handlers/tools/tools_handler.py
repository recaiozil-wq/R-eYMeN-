"""_handle_tools_command handler."""


def _handle_tools_command(cli, cmd: str):
    """Handle /tools [list|disable|enable] slash commands.

    /tools (no args) shows the tool list.
    /tools list shows enabled/disabled status per toolset.
    /tools disable/enable saves the change to config and resets
    the session so the new tool set takes effect cleanly (no
    prompt-cache breakage mid-conversation).
    """
    from contextlib import redirect_stdout
    from io import StringIO
    from argparse import Namespace

    import shlex

    from reymen.reymen_cli.tools_config import tools_disable_enable_command
    from reymen.sistem.cli_display import _cprint, _ACCENT, _RST, _DIM

    def _run_capture(ns: Namespace) -> None:
        """Run tools_disable_enable_command, routing its ANSI-colored
        print() output through _cprint when inside the interactive TUI
        so escapes aren't mangled by patch_stdout's StdoutProxy into
        garbled '?[32m...?[0m' text.

        Outside the TUI (standalone mode, tests), call straight through
        so real stdout / pytest capture works as expected.
        """
        # Standalone/tests, run as usual
        if getattr(cli, "_app", None) is None:
            tools_disable_enable_command(ns)
            return

        # Buffer reports isatty()=True so color() in ReYMeN_cli/colors.py
        # still emits ANSI escapes. StringIO.isatty() is False, which
        # would otherwise strip all colors before we re-render them.
        class _TTYBuf(StringIO):
            def isatty(self) -> bool:
                return True

        buf = _TTYBuf()
        with redirect_stdout(buf):
            tools_disable_enable_command(ns)
        for line in buf.getvalue().splitlines():
            _cprint(line)

    try:
        parts = shlex.split(cmd)
    except ValueError:
        parts = cmd.split()

    subcommand = parts[1] if len(parts) > 1 else ""
    if subcommand not in {"list", "disable", "enable"}:
        cli.show_tools()
        return

    if subcommand == "list":
        _run_capture(Namespace(tools_action="list", platform="cli"))
        return

    names = parts[2:]
    if not names:
        print(f"(._.) Usage: /tools {subcommand} <name> [name ...]")
        print(f"  Built-in toolset:  /tools {subcommand} web")
        print(f"  MCP tool:          /tools {subcommand} github:create_issue")
        return

    # Apply the change directly — the user typing the command is implicit
    # consent.  Do NOT use input() here; it hangs inside prompt_toolkit's
    # TUI event loop (known pitfall).
    verb = "Disabling" if subcommand == "disable" else "Enabling"
    label = ", ".join(names)
    _cprint(f"{_ACCENT}{verb} {label}...{_RST}")

    _run_capture(Namespace(tools_action=subcommand, names=names, platform="cli"))

    # Reset session so the new tool config is picked up from a clean state
    from reymen.reymen_cli.tools_config import _get_platform_tools
    from reymen.reymen_cli.config import load_config
    cli.enabled_toolsets = _get_platform_tools(load_config(), "cli")
    cli.new_session()
    _cprint(f"{_DIM}Session reset. New tool configuration is active.{_RST}")
