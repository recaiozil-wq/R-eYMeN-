"""_handle_agents_command handler."""

from src.reymen.sistem.cli_display import _cprint


def _handle_agents_command(cli):
    """Handle /agents — show background processes and agent status."""
    from tools.process_registry import format_uptime_short, process_registry

    processes = process_registry.list_sessions()
    running = [p for p in processes if p.get("status") == "running"]
    finished = [p for p in processes if p.get("status") != "running"]

    _cprint(f"  Running processes: {len(running)}")
    for p in running:
        cmd = p.get("command", "")[:80]
        up = format_uptime_short(p.get("uptime_seconds", 0))
        _cprint(f"    {p.get('session_id', '?')} · {up} · {cmd}")

    if finished:
        _cprint(f"  Recently finished: {len(finished)}")

    agent_running = getattr(cli, "_agent_running", False)
    _cprint(f"  Agent: {'running' if agent_running else 'idle'}")
