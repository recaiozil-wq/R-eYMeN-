"""_handle_skills_command handler."""


def _handle_skills_command(cli, cmd: str):
    """Handle /skills slash command — delegates to ReYMeN_cli.skills_hub."""
    from reymen.reymen_cli.skills_hub import handle_skills_slash
    from reymen.sistem.cli_stream import ChatConsole
    handle_skills_slash(cmd, ChatConsole())
