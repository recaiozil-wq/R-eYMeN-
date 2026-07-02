"""_handle_snapshot_command handler."""


def _handle_snapshot_command(cli, command: str):
    """Handle /snapshot — lightweight state snapshots for ReYMeN config/state.

    Syntax:
        /snapshot                  — list recent snapshots
        /snapshot create [label]   — create a snapshot
        /snapshot restore <id>     — restore state from snapshot
        /snapshot prune [N]        — prune to N snapshots (default 20)
    """
    from reymen.reymen_cli.backup import (
        create_quick_snapshot, list_quick_snapshots,
        restore_quick_snapshot, prune_quick_snapshots,
    )
    from reymen.sistem.ReYMeN_constants import display_reymen_home

    parts = command.split()
    subcmd = parts[1].lower() if len(parts) > 1 else "list"

    if subcmd in {"list", "ls"}:
        snaps = list_quick_snapshots()
        if not snaps:
            print("  No state snapshots yet.")
            print("  Create one: /snapshot create [label]")
            return
        print(f"  State snapshots ({display_reymen_home()}/state-snapshots/):\n")
        print(f"  {'#':>3}  {'ID':<35} {'Files':>5} {'Size':>10} {'Label'}")
        print(f"  {'─'*3}  {'─'*35} {'─'*5} {'─'*10} {'─'*20}")
        for i, s in enumerate(snaps, 1):
            size = s.get("total_size", 0)
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.0f} KB"
            else:
                size_str = f"{size / 1024 / 1024:.1f} MB"
            label = s.get("label") or ""
            print(f"  {i:3}  {s['id']:<35} {s.get('file_count', 0):>5} {size_str:>10} {label}")

    elif subcmd == "create":
        label = " ".join(parts[2:]) if len(parts) > 2 else None
        snap_id = create_quick_snapshot(label=label)
        if snap_id:
            print(f"  Snapshot created: {snap_id}")
        else:
            print("  No state files found to snapshot.")

    elif subcmd in {"restore", "rewind"}:
        if len(parts) < 3:
            print("  Usage: /snapshot restore <snapshot-id>")
            # Show hint with most recent snapshot
            snaps = list_quick_snapshots(limit=1)
            if snaps:
                print(f"  Most recent: {snaps[0]['id']}")
            return
        snap_id = parts[2]
        # Allow restore by number (1-indexed)
        try:
            idx = int(snap_id)
            snaps = list_quick_snapshots()
            if 1 <= idx <= len(snaps):
                snap_id = snaps[idx - 1]["id"]
            else:
                print(f"  Invalid snapshot number. Use 1-{len(snaps)}.")
                return
        except ValueError:
            import logging
            logging.getLogger(__name__).warning("[fix_01_sessiz_except] ValueError")
        if restore_quick_snapshot(snap_id):
            print(f"  Restored state from: {snap_id}")
            print("  Restart recommended for state.db changes to take effect.")
        else:
            print(f"  Snapshot not found: {snap_id}")

    elif subcmd == "prune":
        keep = 20
        if len(parts) > 2:
            try:
                keep = int(parts[2])
            except ValueError:
                print("  Usage: /snapshot prune [keep-count]")
                return
        deleted = prune_quick_snapshots(keep=keep)
        print(f"  Pruned {deleted} old snapshot(s) (keeping {keep}).")

    else:
        print(f"  Unknown subcommand: {subcmd}")
        print("  Usage: /snapshot [list|create [label]|restore <id>|prune [N]]")
