"""_handle_rollback_command handler."""


def _handle_rollback_command(cli, command: str):
    """Handle /rollback — list, diff, or restore filesystem checkpoints.

    Syntax:
        /rollback                 — list checkpoints
        /rollback <N>             — restore checkpoint N (also undoes last chat turn)
        /rollback diff <N>        — preview changes since checkpoint N
        /rollback <N> <file>      — restore a single file from checkpoint N
    """
    from tools.checkpoint_manager import format_checkpoint_list

    if not hasattr(cli, 'agent') or not cli.agent:
        print("  No active agent session.")
        return

    mgr = cli.agent._checkpoint_mgr
    if not mgr.enabled:
        print("  Checkpoints are not enabled.")
        print("  Enable with: ReYMeN --checkpoints")
        print("  Or in config.yaml: checkpoints: { enabled: true }")
        return

    cwd = os.getenv("TERMINAL_CWD", os.getcwd())
    parts = command.split()
    args = parts[1:] if len(parts) > 1 else []

    if not args:
        # List checkpoints
        checkpoints = mgr.list_checkpoints(cwd)
        print(format_checkpoint_list(checkpoints, cwd))
        return

    # Handle /rollback diff <N>
    if args[0].lower() == "diff":
        if len(args) < 2:
            print("  Usage: /rollback diff <N>")
            return
        checkpoints = mgr.list_checkpoints(cwd)
        if not checkpoints:
            print(f"  No checkpoints found for {cwd}")
            return
        target_hash = cli._resolve_checkpoint_ref(args[1], checkpoints)
        if not target_hash:
            return
        result = mgr.diff(cwd, target_hash)
        if result["success"]:
            stat = result.get("stat", "")
            diff = result.get("diff", "")
            if not stat and not diff:
                print("  No changes since this checkpoint.")
            else:
                if stat:
                    print(f"\n{stat}")
                if diff:
                    # Limit diff output to avoid terminal flood
                    diff_lines = diff.splitlines()
                    if len(diff_lines) > 80:
                        print("\n".join(diff_lines[:80]))
                        print(f"\n  ... ({len(diff_lines) - 80} more lines, showing first 80)")
                    else:
                        print(f"\n{diff}")
        else:
            print(f"  ❌ {result['error']}")
        return

    # Resolve checkpoint reference (number or hash)
    checkpoints = mgr.list_checkpoints(cwd)
    if not checkpoints:
        print(f"  No checkpoints found for {cwd}")
        return

    target_hash = cli._resolve_checkpoint_ref(args[0], checkpoints)
    if not target_hash:
        return

    # Check for file-level restore: /rollback <N> <file>
    file_path = args[1] if len(args) > 1 else None

    result = mgr.restore(cwd, target_hash, file_path=file_path)
    if result["success"]:
        if file_path:
            print(f"  ✅ Restored {file_path} from checkpoint {result['restored_to']}: {result['reason']}")
        else:
            print(f"  ✅ Restored to checkpoint {result['restored_to']}: {result['reason']}")
        print("  A pre-rollback snapshot was saved automatically.")

        # Also undo the last conversation turn so the agent's context
        # matches the restored filesystem state
        if cli.conversation_history:
            cli.undo_last(prefill=False)
            print("  Chat turn undone to match restored file state.")
    else:
        print(f"  ❌ {result['error']}")


import os  # noqa: E402
