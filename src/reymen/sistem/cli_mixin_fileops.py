"""ReYMeNCLI mixin module — File/DevOps operations (rollback, snapshot, stop, debug, update)."""

import logging
import os
import re
import shutil
import sys
import textwrap
import time
import json
import math
import threading
import uuid
import base64
import atexit
import tempfile
from collections import deque
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class MixinFileOps:
    """ReYMeNCLI File/DevOps operations — rollback, snapshot, stop, debug, update."""


    def _handle_rollback_command(self, command: str):
        """Handle /rollback — list, diff, or restore filesystem checkpoints.

        Syntax:
            /rollback                 — list checkpoints
            /rollback <N>             — restore checkpoint N (also undoes last chat turn)
            /rollback diff <N>        — preview changes since checkpoint N
            /rollback <N> <file>      — restore a single file from checkpoint N
        """
        from tools.checkpoint_manager import format_checkpoint_list

        if not hasattr(self, 'agent') or not self.agent:
            print("  No active agent session.")
            return

        mgr = self.agent._checkpoint_mgr
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
            target_hash = self._resolve_checkpoint_ref(args[1], checkpoints)
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

        target_hash = self._resolve_checkpoint_ref(args[0], checkpoints)
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
            if self.conversation_history:
                self.undo_last(prefill=False)
                print("  Chat turn undone to match restored file state.")
        else:
            print(f"  ❌ {result['error']}")


    def _handle_snapshot_command(self, command: str):
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
                logger.warning("[fix_01_sessiz_except] ValueError")
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


    def _handle_stop_command(self):
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


    def _handle_debug_command(self):
        """Handle /debug — upload debug report + logs and print paste URLs."""
        from reymen.reymen_cli.debug import run_debug_share
        from types import SimpleNamespace

        args = SimpleNamespace(lines=200, expire=7, local=False)
        run_debug_share(args)


    def _handle_update_command(self) -> bool:
        """Handle /update — update ReYMeN Agent to the latest version.

        In the classic CLI this exits the session and relaunches as
        ``ReYMeN update`` so the user sees update output directly and gets
        the new version on next launch.

        Returns ``True`` when the update was confirmed (caller should trigger
        app exit so the relaunch is deferred to the main thread after
        prompt_toolkit cleans up terminal modes).  Returns ``False`` / falsy
        when cancelled.
        """
        from reymen.reymen_cli.config import is_managed, format_managed_message

        if is_managed():
            print(f"  ✗ {format_managed_message('update ReYMeN Agent')}")
            return False

        # Use the prompt_toolkit-native modal so the confirmation panel
        # renders properly above the composer and avoids raw input() races
        # with the prompt_toolkit event loop (same pattern as
        # _confirm_destructive_slash).
        choices = [
            ("once", "Update Now", "exit the current session and update ReYMeN Agent"),
            ("cancel", "Cancel", "keep the current session"),
        ]
        raw = self._prompt_text_input_modal(
            title="⚕  Update ReYMeN Agent",
            detail="This will exit the current session and run `ReYMeN update`.",
            choices=choices,
        )
        if raw is None:
            print("  🟡 /update cancelled.")
            return False
        choice = self._normalize_slash_confirm_choice(raw, choices)
        if choice != "once":
            print("  🟡 /update cancelled.")
            return False

        print()
        print("  ⚕ Launching update...")
        print()

        # Store the relaunch args so run() can exec them from the main thread
        # after prompt_toolkit exits and restores terminal modes.  Calling
        # relaunch() directly here (from the process_loop daemon thread) would
        # skip terminal cleanup on POSIX (execvp replaces the process mid-TUI)
        # and only exit the worker thread on Windows (subprocess.run +
        # sys.exit inside a non-main thread does not exit the process).
        self._pending_relaunch = ["update"]
        return True


__all__ = ['MixinFileOps']
