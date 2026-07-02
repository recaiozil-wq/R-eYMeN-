"""Handle /resume command — switch to a previous session mid-conversation."""

import logging

logger = logging.getLogger(__name__)


def handle_resume_command(cli, cmd_original: str) -> None:
    """Handle /resume <session_id_or_title> — switch to a previous session mid-conversation."""
    from reymen.sistem.cli_display import _cprint

    parts = cmd_original.split(None, 1)
    target = parts[1].strip() if len(parts) > 1 else ""

    # Strip common outer brackets/quotes users may type literally from the
    # usage hint (e.g. ``/resume <abc123>`` or ``/resume [abc123]``).  The
    # `/resume` help text shows angle brackets as a placeholder and a few
    # users copy them through verbatim.  Stripping them keeps the lookup
    # working without changing the help string.
    if len(target) >= 2 and (
        (target[0] == "<" and target[-1] == ">")
        or (target[0] == "[" and target[-1] == "]")
        or (target[0] == '"' and target[-1] == '"')
        or (target[0] == "'" and target[-1] == "'")
    ):
        target = target[1:-1].strip()

    if not target:
        _cprint("  Usage: /resume <number|session_id_or_title>")
        if cli._show_recent_sessions(reason="resume"):
            # Arm a one-shot pending-resume selection so the user can type
            # just the number (`3`) on the next line instead of having to
            # retype `/resume 3`. The list here must match the one shown by
            # _show_recent_sessions and used for index resolution below —
            # all three go through _list_recent_sessions(limit=10). See
            # #34584.
            cli._pending_resume_sessions = cli._list_recent_sessions(limit=10)
            return
        _cprint("  Tip:   Use /history or `ReYMeN sessions list` to find sessions.")
        return

    # Any explicit /resume <target> supersedes a previously-armed bare
    # numbered prompt.
    cli._pending_resume_sessions = None

    if not cli._session_db:
        from reymen.sistem.ReYMeN_state import format_session_db_unavailable
        _cprint(f"  {format_session_db_unavailable()}")
        return

    # Resolve numbered selection, title, or ID
    if target.isdigit():
        sessions = cli._list_recent_sessions(limit=10)
        index = int(target)
        if index < 1 or index > len(sessions):
            _cprint(f"  Resume index {index} is out of range.")
            _cprint("  Use /resume with no arguments to see available sessions.")
            return
        selected = sessions[index - 1]
        target_id = selected["id"]
    else:
        from reymen.reymen_cli.main import _resolve_session_by_name_or_id
        resolved = _resolve_session_by_name_or_id(target)
        target_id = resolved or target

    session_meta = cli._session_db.get_session(target_id)
    if not session_meta:
        _cprint(f"  Session not found: {target}")
        _cprint("  Use /history or `ReYMeN sessions list` to see available sessions.")
        return

    # If the target is the empty head of a compression chain, redirect to
    # the descendant that actually holds the transcript. See #15000.
    try:
        resolved_id = cli._session_db.resolve_resume_session_id(target_id)
    except Exception:
        resolved_id = target_id
    if resolved_id and resolved_id != target_id:
        _cprint(
            f"  Session {target_id} was compressed into {resolved_id}; "
            f"resuming the descendant with your transcript."
        )
        target_id = resolved_id
        resolved_meta = cli._session_db.get_session(target_id)
        if resolved_meta:
            session_meta = resolved_meta

    if target_id == cli.session_id:
        _cprint("  Already on that session.")
        return

    old_session_id = cli.session_id
    # End current session
    try:
        cli._session_db.end_session(cli.session_id, "resumed_other")
    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")

    # Switch to the target session
    cli.session_id = target_id
    cli._resumed = True
    cli._pending_title = None
    _sync_process_session_id(target_id)

    # Load conversation history (strip transcript-only metadata entries)
    restored = cli._session_db.get_messages_as_conversation(target_id)
    restored = [m for m in (restored or []) if m.get("role") != "session_meta"]
    cli.conversation_history = restored

    # Re-open the target session so it's not marked as ended
    try:
        cli._session_db.reopen_session(target_id)
    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")

    # Sync the agent if already initialised
    if cli.agent:
        cli.agent.session_id = target_id
        cli.agent.reset_session_state()
        if hasattr(cli.agent, "_last_flushed_db_idx"):
            cli.agent._last_flushed_db_idx = len(cli.conversation_history)
        if hasattr(cli.agent, "_todo_store"):
            try:
                from tools.todo_tool import TodoStore
                cli.agent._todo_store = TodoStore()
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")
        if hasattr(cli.agent, "_invalidate_system_prompt"):
            cli.agent._invalidate_system_prompt()

        # Notify memory providers that session_id rotated to a resumed
        # session. reset=False — the provider's accumulated state is
        # still valid; it just needs to target the new session_id for
        # subsequent writes. See #6672.
        try:
            _mm = getattr(cli.agent, "_memory_manager", None)
            if _mm is not None:
                _mm.on_session_switch(
                    target_id,
                    parent_session_id=old_session_id or "",
                    reset=False,
                    reason="resume",
                )
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")

    title_part = f" \"{session_meta['title']}\"" if session_meta.get("title") else ""
    msg_count = len([m for m in cli.conversation_history if m.get("role") == "user"])
    if cli.conversation_history:
        _cprint(
            f"  ↻ Resumed session {target_id}{title_part}"
            f" ({msg_count} user message{'s' if msg_count != 1 else ''},"
            f" {len(cli.conversation_history)} total)"
        )
        cli._display_resumed_history()
    else:
        _cprint(f"  ↻ Resumed session {target_id}{title_part} — no messages, starting fresh.")


# Needed by this handler — imported here to keep it accessible
from src.reymen.sistem.cli_auth import _sync_process_session_id  # noqa: E402, F811
