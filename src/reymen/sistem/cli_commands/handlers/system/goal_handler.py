"""_handle_goal_command handler."""

from src.reymen.sistem.cli_display import _cprint, _DIM, _RST
import logging
logger = logging.getLogger(__name__)

logger = __import__("logging").getLogger(__name__)


def _handle_goal_command(cli, cmd: str) -> None:
    """Dispatch /goal subcommands: set / status / pause / resume / clear."""
    parts = (cmd or "").strip().split(None, 1)
    arg = parts[1].strip() if len(parts) > 1 else ""

    mgr = cli._get_goal_manager()
    if mgr is None:
        _cprint(f"  {_DIM}Goals unavailable (no active session).{_RST}")
        return

    lower = arg.lower()

    # Bare /goal or /goal status → show current state
    if not arg or lower == "status":
        _cprint(f"  {mgr.status_line()}")
        return

    if lower == "pause":
        state = mgr.pause(reason="user-paused")
        if state is None:
            _cprint(f"  {_DIM}No goal set.{_RST}")
        else:
            _cprint(f"  ⏸ Goal paused: {state.goal}")
        return

    if lower == "resume":
        state = mgr.resume()
        if state is None:
            _cprint(f"  {_DIM}No goal to resume.{_RST}")
        else:
            _cprint(f"  ▶ Goal resumed: {state.goal}")
            _cprint(
                f"  {_DIM}Send any message (or press Enter on an empty prompt "
                f"is a no-op; type 'continue' to kick it off).{_RST}"
            )
        return

    if lower in {"clear", "stop", "done"}:
        had = mgr.has_goal()
        mgr.clear()
        if had:
            _cprint("  ✓ Goal cleared.")
        else:
            _cprint(f"  {_DIM}No active goal.{_RST}")
        return

    # Otherwise treat the arg as the goal text.
    try:
        state = mgr.set(arg)
    except ValueError as exc:
        _cprint(f"  Invalid goal: {exc}")
        return

    _cprint(f"  ⊙ Goal set ({state.max_turns}-turn budget): {state.goal}")
    _cprint(
        f"  {_DIM}After each turn, a judge model will check if the goal is done. "
        f"ReYMeN keeps working until it is, you pause/clear it, or the budget is "
        f"exhausted. Use /goal status, /goal pause, /goal resume, /goal clear.{_RST}"
    )
    # Kick the loop off immediately so the user doesn't have to send a
    # separate message after setting the goal.
    try:
        cli._pending_input.put(state.goal)
    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")
