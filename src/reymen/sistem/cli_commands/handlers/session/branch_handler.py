"""Handle /branch command — fork the current session into a new independent copy."""

import logging
import os
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


def handle_branch_command(cli, cmd_original: str) -> None:
    """Handle /branch [name] — fork the current session into a new independent copy.

    Copies the full conversation history to a new session so the user can
    explore a different approach without losing the original session state.
    Inspired by Claude Code's /branch command.
    """
    from reymen.sistem.cli_display import _cprint

    if not cli.conversation_history:
        _cprint("  No conversation to branch — send a message first.")
        return

    if not cli._session_db:
        from reymen.sistem.ReYMeN_state import format_session_db_unavailable
        _cprint(f"  {format_session_db_unavailable()}")
        return

    parts = cmd_original.split(None, 1)
    branch_name = parts[1].strip() if len(parts) > 1 else ""

    # Generate the new session ID
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:6]
    new_session_id = f"{timestamp_str}_{short_uuid}"

    # Determine branch title
    if branch_name:
        branch_title = branch_name
    else:
        # Auto-generate from the current session title
        current_title = None
        if cli._session_db:
            current_title = cli._session_db.get_session_title(cli.session_id)
        base = current_title or "branch"
        branch_title = cli._session_db.get_next_title_in_lineage(base)

    # Save the current session's state before branching
    parent_session_id = cli.session_id

    # End the old session
    try:
        cli._session_db.end_session(cli.session_id, "branched")
    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")

    # Create the new session with parent link
    try:
        cli._session_db.create_session(
            session_id=new_session_id,
            source=os.environ.get("ReYMeN_SESSION_SOURCE", "cli"),
            model=cli.model,
            model_config={
                "max_iterations": cli.max_turns,
                "reasoning_config": cli.reasoning_config,
            },
            parent_session_id=parent_session_id,
        )
    except Exception as e:
        _cprint(f"  Failed to create branch session: {e}")
        return

    # Copy conversation history to the new session
    for msg in cli.conversation_history:
        try:
            cli._session_db.append_message(
                session_id=new_session_id,
                role=msg.get("role", "user"),
                content=msg.get("content"),
                tool_name=msg.get("tool_name") or msg.get("name"),
                tool_calls=msg.get("tool_calls"),
                tool_call_id=msg.get("tool_call_id"),
                reasoning=msg.get("reasoning"),
            )
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )  # Best-effort copy

    # Set title on the branch
    try:
        cli._session_db.set_session_title(new_session_id, branch_title)
    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")

    # Switch to the new session
    cli._transfer_session_yolo(cli.session_id, new_session_id)
    cli.session_id = new_session_id
    cli.session_start = now
    cli._pending_title = None
    cli._resumed = True  # Prevents auto-title generation
    _sync_process_session_id(new_session_id)

    # Sync the agent
    if cli.agent:
        cli.agent.session_id = new_session_id
        cli.agent.session_start = now
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

        # Notify memory providers that session_id forked to a new branch.
        # reset=False — the branched session carries the transcript
        # forward, so provider state tracks the lineage. parent_session_id
        # links the branch back to the original. See #6672.
        try:
            _mm = getattr(cli.agent, "_memory_manager", None)
            if _mm is not None:
                _mm.on_session_switch(
                    new_session_id,
                    parent_session_id=parent_session_id or "",
                    reset=False,
                    reason="branch",
                )
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")

    msg_count = len([m for m in cli.conversation_history if m.get("role") == "user"])
    _cprint(
        f"  ⑂ Branched session \"{branch_title}\""
        f" ({msg_count} user message{'s' if msg_count != 1 else ''})"
    )
    _cprint(f"  Original session: {parent_session_id}")
    _cprint(f"  Branch session:   {new_session_id}")


# Needed by this handler — imported here to keep it accessible
from src.reymen.sistem.cli_auth import _sync_process_session_id  # noqa: E402, F811
