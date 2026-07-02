"""_handle_subgoal_command handler."""

from src.reymen.sistem.cli_display import _cprint, _DIM, _RST


def _handle_subgoal_command(cli, cmd: str) -> None:
    """Dispatch /subgoal subcommands.

    Forms:
      /subgoal                              show current subgoals
      /subgoal <text>                       append a criterion
      /subgoal remove <n>                   drop subgoal n (1-based)
      /subgoal clear                        wipe all subgoals

    Subgoals are extra criteria the user adds mid-loop. They get
    appended to both the judge prompt (verdict must consider them)
    and the continuation prompt (agent sees them) on the next turn
    boundary. No special kick — the running turn finishes, the next
    judge call includes them.
    """
    parts = (cmd or "").strip().split(None, 2)
    arg = " ".join(parts[1:]).strip() if len(parts) > 1 else ""

    mgr = cli._get_goal_manager()
    if mgr is None:
        _cprint(f"  {_DIM}Goals unavailable (no active session).{_RST}")
        return

    if not mgr.has_goal():
        _cprint(f"  {_DIM}No active goal. Set one with /goal <text>.{_RST}")
        return

    # No args → list current subgoals.
    if not arg:
        _cprint(f"  {mgr.status_line()}")
        _cprint(f"  {mgr.render_subgoals()}")
        return

    tokens = arg.split(None, 1)
    verb = tokens[0].lower()
    rest = tokens[1].strip() if len(tokens) > 1 else ""

    if verb == "remove":
        if not rest:
            _cprint("  Usage: /subgoal remove <n>")
            return
        try:
            idx = int(rest.split()[0])
        except ValueError:
            _cprint("  /subgoal remove: <n> must be an integer (1-based index).")
            return
        try:
            removed = mgr.remove_subgoal(idx)
        except (IndexError, RuntimeError) as exc:
            _cprint(f"  /subgoal remove: {exc}")
            return
        _cprint(f"  ✓ Removed subgoal {idx}: {removed}")
        return

    if verb == "clear":
        try:
            prev = mgr.clear_subgoals()
        except RuntimeError as exc:
            _cprint(f"  /subgoal clear: {exc}")
            return
        if prev:
            _cprint(f"  ✓ Cleared {prev} subgoal{'s' if prev != 1 else ''}.")
        else:
            _cprint(f"  {_DIM}No subgoals to clear.{_RST}")
        return

    # Otherwise — append the whole arg as a new subgoal.
    try:
        text = mgr.add_subgoal(arg)
    except (ValueError, RuntimeError) as exc:
        _cprint(f"  /subgoal: {exc}")
        return
    idx = len(mgr.state.subgoals) if mgr.state else 0
    _cprint(f"  ✓ Added subgoal {idx}: {text}")
