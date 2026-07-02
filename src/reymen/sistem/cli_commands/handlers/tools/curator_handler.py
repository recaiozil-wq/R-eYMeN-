"""_handle_curator_command handler."""

import logging
import shlex

logger = logging.getLogger(__name__)


def _handle_curator_command(cli, cmd: str):
    """Handle /curator slash command.

    Delegates to ReYMeN_cli.curator so the CLI and the `ReYMeN curator`
    subcommand share the same handler set.
    """
    tokens = shlex.split(cmd)[1:] if cmd else []
    if not tokens:
        tokens = ["status"]

    try:
        from reymen.reymen_cli.curator import cli_main
        cli_main(tokens)
    except SystemExit:
        # argparse calls sys.exit() on --help or errors; swallow so we
        # don't kill the interactive session.
        logger.warning("[fix_01_sessiz_except] SystemExit")
    except Exception as exc:
        print(f"(._.) curator: {exc}")
