"""Handle /sessions command — browse or resume previous sessions."""


def handle_sessions_command(cli, cmd_original: str) -> None:
    """Handle /sessions [list|<id_or_title>] — browse or resume previous sessions.

    Without arguments, prints the same recent-sessions table that /resume
    shows when called without a target, and tells the user how to resume.
    With an explicit subcommand or target, delegates to the resume flow so
    ``/sessions <id>`` and ``/resume <id>`` behave identically.

    The TUI ships an interactive picker overlay for this command; the
    classic CLI prints an inline list because there is no equivalent
    overlay primitive here. Without this handler the canonical name
    ``sessions`` falls through ``process_command``'s elif chain and
    prints ``Unknown command: sessions`` even though the command is
    registered in the central COMMAND_REGISTRY.
    """
    from reymen.sistem.cli_display import _cprint

    parts = cmd_original.split(None, 1)
    arg = parts[1].strip() if len(parts) > 1 else ""
    sub = arg.lower()

    # Bare /sessions or /sessions list — show recent sessions inline.
    if not arg or sub in {"list", "ls", "browse"}:
        if not cli._session_db:
            from reymen.sistem.ReYMeN_state import format_session_db_unavailable
            _cprint(f"  {format_session_db_unavailable()}")
            return
        if not cli._show_recent_sessions(reason="sessions"):
            _cprint("  (._.) No previous sessions yet.")
        return

    # /sessions <id_or_title> behaves the same as /resume <id_or_title>.
    cli._handle_resume_command(f"/resume {arg}")
