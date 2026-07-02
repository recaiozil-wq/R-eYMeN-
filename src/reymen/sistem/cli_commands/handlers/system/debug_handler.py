"""_handle_debug_command handler."""


def _handle_debug_command(cli):
    """Handle /debug — upload debug report + logs and print paste URLs."""
    from reymen.reymen_cli.debug import run_debug_share
    from types import SimpleNamespace

    args = SimpleNamespace(lines=200, expire=7, local=False)
    run_debug_share(args)
