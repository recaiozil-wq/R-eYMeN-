"""_handle_stop_command handler."""


def _handle_stop_command(cli):
    """Handle /stop — kill all running background processes.

    Inspired by OpenAI Codex's separation of interrupt (stop current turn)
    from /stop (clean up background processes). See openai/codex#14602.
    """
    from tools.process_registry import process_registry

    processes = process_registry.list_sessions()
    running = [p for p in processes if p.get("status") == "running"]

    if not running:
        print("  No running background processes.")
        return

    print(f"  Stopping {len(running)} background process(es)...")
    killed = process_registry.kill_all()
    print(f"  ✅ Stopped {killed} process(es).")
