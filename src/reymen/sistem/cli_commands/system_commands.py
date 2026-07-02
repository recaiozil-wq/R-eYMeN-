"""Sistem komutları — MixinCommands alt modülü.

Bu dosya otomatik olarak cli_mixin_commands.py'den ayrılmıştır.
MixinCommands sınıfının ilgili metotlarını içerir.
"""

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


class MixinCommands:
    """Sistem komutları."""

    def process_command(self, command: str) -> bool:
        """
        Process a slash command.
        
        Args:
            command: The command string (starting with /)
            
        Returns:
            bool: True to continue, False to exit
        """
        # Lowercase only for dispatch matching; preserve original case for arguments
        cmd_lower = command.lower().strip()
        cmd_original = command.strip()

        # Resolve aliases via central registry so adding an alias is a one-line
        # change in ReYMeN_cli/commands.py instead of touching every dispatch site.
        from reymen.reymen_cli.commands import resolve_command as _resolve_cmd
        _base_word = cmd_lower.split()[0].lstrip("/")
        _cmd_def = _resolve_cmd(_base_word)
        canonical = _cmd_def.name if _cmd_def else _base_word

        # A bare `/resume` prompt is one-shot: any command other than the
        # resume/sessions handlers (which manage the pending state themselves)
        # disarms it so a later number isn't swallowed as a stale selection.
        # See #34584.
        if canonical not in {"resume", "sessions"}:
            self._pending_resume_sessions = None

        if canonical in {"quit", "exit"}:
            # Parse --delete flag: /exit --delete also removes the current
            # session's transcripts + SQLite history. Ported from
            # google-gemini/gemini-cli#19332.
            _rest = cmd_original.split(None, 1)
            _args = (_rest[1] if len(_rest) > 1 else "").strip().lower()
            if _args in {"--delete", "-d"}:
                self._delete_session_on_exit = True
            elif _args:
                _cprint(f"  {_DIM}✗ Unknown argument: {_escape(_args)}. Use /exit --delete to also remove session history.{_RST}")
                return True
            return False
        elif canonical == "help":
            self.show_help()
        elif canonical == "profile":
            self._handle_profile_command()
        elif canonical == "tools":
            self._handle_tools_command(cmd_original)
        elif canonical == "toolsets":
            self.show_toolsets()
        elif canonical == "config":
            self.show_config()
        elif canonical == "redraw":
            # Manual recovery for terminal buffer drift from multiplexer
            # tab switches, subshell ``clear``, SSH window restores, etc.
            # See issue #8688 (cmux). Ctrl+L is bound to the same helper.
            self._force_full_redraw()
            _cprint(f"  {_DIM}✓ UI redrawn{_RST}")
        elif canonical == "clear":
            if self._confirm_destructive_slash(
                "clear",
                "This clears the screen and starts a new session.\n"
                "The current conversation history will be discarded.",
                cmd_original=cmd_original,
            ) is None:
                return
            self.new_session(silent=True)
            _clear_output_history()
            # Clear terminal screen.  Inside the TUI, Rich's console.clear()
            # goes through patch_stdout's StdoutProxy which swallows the
            # screen-clear escape sequences.  Use prompt_toolkit's output
            # object directly to actually clear the terminal.
            if self._app:
                out = self._app.output
                out.erase_screen()
                out.cursor_goto(0, 0)
                out.flush()
            else:
                self.console.clear()
            # Show fresh banner.  Inside the TUI we must route Rich output
            # through ChatConsole (which uses prompt_toolkit's native ANSI
            # renderer) instead of self.console (which writes raw to stdout
            # and gets mangled by patch_stdout).
            if self._app:
                cc = ChatConsole()
                term_w = shutil.get_terminal_size().columns
                if self.compact or term_w < 80:
                    cc.print(_build_compact_banner())
                else:
                    tools = get_tool_definitions(enabled_toolsets=self.enabled_toolsets, quiet_mode=True)
                    cwd = os.getenv("TERMINAL_CWD", os.getcwd())
                    ctx_len = None
                    if hasattr(self, 'agent') and self.agent and hasattr(self.agent, 'context_compressor'):
                        ctx_len = self.agent.context_compressor.context_length
                    build_welcome_banner(
                        console=cc,
                        model=self.model,
                        cwd=cwd,
                        tools=tools,
                        enabled_toolsets=self.enabled_toolsets,
                        session_id=self.session_id,
                        context_length=ctx_len,
                    )
                _cprint("  ✨ (◕‿◕)✨ Fresh start! Screen cleared and conversation reset.\n")
                # Show a random tip on new session
                try:
                    from reymen.reymen_cli.tips import get_random_tip
                    _tip = get_random_tip()
                    try:
                        from reymen.reymen_cli.skin_engine import get_active_skin
                        _tip_color = get_active_skin().get_color("banner_dim", "#B8860B")
                    except Exception:
                        _tip_color = "#B8860B"
                    cc.print(f"[dim {_tip_color}]✦ Tip: {_tip}[/]")
                except Exception:
                    logger.warning("[fix_01_sessiz_except] Exception")
            else:
                self.show_banner()
                print("  ✨ (◕‿◕)✨ Fresh start! Screen cleared and conversation reset.\n")
                # Show a random tip on new session
                try:
                    from reymen.reymen_cli.tips import get_random_tip
                    _tip = get_random_tip()
                    try:
                        from reymen.reymen_cli.skin_engine import get_active_skin
                        _tip_color = get_active_skin().get_color("banner_dim", "#B8860B")
                    except Exception:
                        _tip_color = "#B8860B"
                    self._console_print(f"[dim {_tip_color}]✦ Tip: {_tip}[/]")
                except Exception:
                    logger.warning("[fix_01_sessiz_except] Exception")
        elif canonical == "history":
            self.show_history()
        elif canonical == "title":
            parts = cmd_original.split(maxsplit=1)
            if len(parts) > 1:
                raw_title = parts[1].strip()
                if raw_title:
                    if self._session_db:
                        # Sanitize the title early so feedback matches what gets stored
                        try:
                            from reymen.sistem.ReYMeN_state import SessionDB
                            new_title = SessionDB.sanitize_title(raw_title)
                        except ValueError as e:
                            _cprint(f"  {e}")
                            new_title = None
                        if not new_title:
                            _cprint("  Title is empty after cleanup. Please use printable characters.")
                        elif self._session_db.get_session(self.session_id):
                            # Session exists in DB — set title directly
                            try:
                                if self._session_db.set_session_title(self.session_id, new_title):
                                    _cprint(f"  Session title set: {new_title}")
                                else:
                                    _cprint("  Session not found in database.")
                            except ValueError as e:
                                _cprint(f"  {e}")
                        else:
                            # Session not created yet — defer the title
                            # Check uniqueness proactively with the sanitized title
                            existing = self._session_db.get_session_by_title(new_title)
                            if existing:
                                _cprint(f"  Title '{new_title}' is already in use by session {existing['id']}")
                            else:
                                self._pending_title = new_title
                                _cprint(f"  Session title queued: {new_title} (will be saved on first message)")
                    else:
                        from reymen.sistem.ReYMeN_state import format_session_db_unavailable
                        _cprint(f"  {format_session_db_unavailable()}")
                else:
                    _cprint("  Usage: /title <your session title>")
            # Show current title and session ID if no argument given
            elif self._session_db:
                _cprint(f"  Session ID: {self.session_id}")
                session = self._session_db.get_session(self.session_id)
                if session and session.get("title"):
                    _cprint(f"  Title: {session['title']}")
                elif self._pending_title:
                    _cprint(f"  Title (pending): {self._pending_title}")
                else:
                    _cprint("  No title set. Usage: /title <your session title>")
            else:
                from reymen.sistem.ReYMeN_state import format_session_db_unavailable
                _cprint(f"  {format_session_db_unavailable()}")
        elif canonical == "handoff":
            if not self._handle_handoff_command(cmd_original):
                return False
        elif canonical == "new":
            # Strip inline-skip tokens (now/--yes/-y) before deriving the title
            # so "/new now My Session" yields title="My Session" instead of
            # title="now My Session". See _split_destructive_skip.
            _new_args, _ = self._split_destructive_skip(cmd_original)
            title = _new_args.strip() or None
            if self._confirm_destructive_slash(
                "new",
                "This starts a fresh session.\n"
                "The current conversation history will be discarded.",
                cmd_original=cmd_original,
            ) is None:
                return
            self.new_session(title=title)
        elif canonical == "resume":
            self._handle_resume_command(cmd_original)
        elif canonical == "sessions":
            self._handle_sessions_command(cmd_original)
        elif canonical == "model":
            self._handle_model_switch(cmd_original)
        elif canonical == "codex-runtime":
            self._handle_codex_runtime(cmd_original)
        elif canonical == "gquota":
            self._handle_gquota_command(cmd_original)

        elif canonical == "personality":
            # Use original case (handler lowercases the personality name itself)
            self._handle_personality_command(cmd_original)
        elif canonical == "retry":
            retry_msg = self.retry_last()
            if retry_msg and hasattr(self, '_pending_input'):
                # Re-queue the message so process_loop sends it to the agent
                self._pending_input.put(retry_msg)
        elif canonical == "undo":
            # Parse optional turn count: "/undo" → 1, "/undo 3" → 3.
            _undo_n = 1
            _undo_parts = cmd_original.split()
            if len(_undo_parts) > 1:
                try:
                    _undo_n = int(_undo_parts[1])
                except ValueError:
                    print(f"(._.) Invalid count {_undo_parts[1]!r} — use /undo or /undo N.")
                    return
                if _undo_n < 1:
                    _undo_n = 1
            _undo_desc = (
                "This removes the last user/assistant exchange from history."
                if _undo_n == 1
                else f"This removes the last {_undo_n} user turns from history."
            )
            if self._confirm_destructive_slash(
                "undo",
                _undo_desc,
                cmd_original=cmd_original,
            ) is None:
                return
            self.undo_last(_undo_n)
        elif canonical == "branch":
            self._handle_branch_command(cmd_original)
        elif canonical == "save":
            self.save_conversation()
        elif canonical == "cron":
            self._handle_cron_command(cmd_original)
        elif canonical == "curator":
            self._handle_curator_command(cmd_original)
        elif canonical == "kanban":
            self._handle_kanban_command(cmd_original)
        elif canonical == "skills":
            with self._busy_command(self._slow_command_status(cmd_original)):
                self._handle_skills_command(cmd_original)
        elif canonical == "platforms":
            self._show_gateway_status()
        elif canonical == "status":
            self._show_session_status()
        elif canonical == "statusbar":
            self._status_bar_visible = not self._status_bar_visible
            state = "visible" if self._status_bar_visible else "hidden"
            self._console_print(f"  Status bar {state}")
        elif canonical == "verbose":
            self._toggle_verbose()
        elif canonical == "footer":
            self._handle_footer_command(cmd_original)
        elif canonical == "yolo":
            self._toggle_yolo()
        elif canonical == "reasoning":
            self._handle_reasoning_command(cmd_original)
        elif canonical == "fast":
            self._handle_fast_command(cmd_original)
        elif canonical == "compress":
            self._manual_compress(cmd_original)
        elif canonical == "usage":
            self._show_usage()
        elif canonical == "insights":
            self._show_insights(cmd_original)
        elif canonical == "copy":
            self._handle_copy_command(cmd_original)
        elif canonical == "debug":
            self._handle_debug_command()
        elif canonical == "update":
            if self._handle_update_command():
                return False
        elif canonical == "paste":
            self._handle_paste_command()
        elif canonical == "image":
            self._handle_image_command(cmd_original)
        elif canonical == "reload":
            from reymen.reymen_cli.config import reload_env
            count = reload_env()
            print(f"  Reloaded .env ({count} var(s) updated)")
        elif canonical == "reload-mcp":
            # Interactive reload: confirm first (unless the user has opted out).
            # The auto-reload path (file watcher) calls _reload_mcp directly
            # without this confirmation.
            self._confirm_and_reload_mcp(cmd_original)
        elif canonical == "reload-skills":
            with self._busy_command(self._slow_command_status(cmd_original)):
                self._reload_skills()
        elif canonical == "bundles":
            self._handle_bundles_command(cmd_original)
        elif canonical == "browser":
            self._handle_browser_command(cmd_original)
        elif canonical == "plugins":
            try:
                from reymen.reymen_cli.plugins import get_plugin_manager
                mgr = get_plugin_manager()
                plugins = mgr.list_plugins()
                if not plugins:
                    print("No plugins installed.")
                    print(f"Drop plugin directories into {display_reymen_home()}/plugins/ to get started.")
                else:
                    print(f"Plugins ({len(plugins)}):")
                    for p in plugins:
                        status = "✓" if p["enabled"] else "✗"
                        version = f" v{p['version']}" if p["version"] else ""
                        tools = f"{p['tools']} tools" if p["tools"] else ""
                        hooks = f"{p['hooks']} hooks" if p["hooks"] else ""
                        commands = f"{p['commands']} commands" if p.get("commands") else ""
                        parts = [x for x in [tools, hooks, commands] if x]
                        detail = f" ({', '.join(parts)})" if parts else ""
                        error = f" — {p['error']}" if p["error"] else ""
                        print(f"  {status} {p['name']}{version}{detail}{error}")
            except Exception as e:
                print(f"Plugin system error: {e}")
        elif canonical == "rollback":
            self._handle_rollback_command(cmd_original)
        elif canonical == "snapshot":
            self._handle_snapshot_command(cmd_original)
        elif canonical == "stop":
            self._handle_stop_command()
        elif canonical == "agents":
            self._handle_agents_command()
        elif canonical == "background":
            self._handle_background_command(cmd_original)
        elif canonical == "queue":
            # Extract prompt after "/queue " or "/q "
            parts = cmd_original.split(None, 1)
            payload = parts[1].strip() if len(parts) > 1 else ""
            if not payload:
                _cprint("  Usage: /queue <prompt>")
            else:
                self._pending_input.put(payload)
                if self._agent_running:
                    _cprint(f"  Queued for the next turn: {payload[:80]}{'...' if len(payload) > 80 else ''}")
                else:
                    _cprint(f"  Queued: {payload[:80]}{'...' if len(payload) > 80 else ''}")
        elif canonical == "steer":
            # Inject a message after the next tool call without interrupting.
            # If the agent is actively running, push the text into the agent's
            # pending_steer slot — the drain hook in _execute_tool_calls_*
            # will append it to the next tool result's content. If no agent
            # is running, fall back to queue semantics (same as /queue).
            parts = cmd_original.split(None, 1)
            payload = parts[1].strip() if len(parts) > 1 else ""
            if not payload:
                _cprint("  Usage: /steer <prompt>")
            elif self._agent_running and self.agent is not None and hasattr(self.agent, "steer"):
                try:
                    accepted = self.agent.steer(payload)
                except Exception as exc:
                    _cprint(f"  Steer failed: {exc}")
                else:
                    if accepted:
                        _cprint(f"  ⏩ Steer queued — arrives after the next tool call: {payload[:80]}{'...' if len(payload) > 80 else ''}")
                    else:
                        _cprint("  Steer rejected (empty payload).")
            else:
                # No active run — treat as a normal next-turn message.
                self._pending_input.put(payload)
                _cprint(f"  No agent running; queued as next turn: {payload[:80]}{'...' if len(payload) > 80 else ''}")
        elif canonical == "goal":
            self._handle_goal_command(cmd_original)
        elif canonical == "subgoal":
            self._handle_subgoal_command(cmd_original)
        elif canonical == "skin":
            self._handle_skin_command(cmd_original)
        elif canonical == "voice":
            self._handle_voice_command(cmd_original)
        elif canonical == "busy":
            self._handle_busy_command(cmd_original)
        else:
            # Check for user-defined quick commands (bypass agent loop, no LLM call)
            base_cmd = cmd_lower.split()[0]
            skill_commands = _ensure_skill_commands()
            skill_bundles = get_skill_bundles()
            quick_commands = self.config.get("quick_commands", {})
            if base_cmd.lstrip("/") in quick_commands:
                qcmd = quick_commands[base_cmd.lstrip("/")]
                if qcmd.get("type") == "exec":
                    import subprocess
                    exec_cmd = qcmd.get("command", "")
                    if exec_cmd:
                        try:
                            import shlex
                            args_list = shlex.split(exec_cmd, posix=(os.name != "nt"))
                            result = subprocess.run(  # nosec B603
                                args_list, shell=False, capture_output=True,
                                text=True, timeout=30
                            )
                            output = result.stdout.strip() or result.stderr.strip()
                            if output:
                                self._console_print(_rich_text_from_ansi(output))
                            else:
                                self._console_print("[dim]Command returned no output[/]")
                        except subprocess.TimeoutExpired:
                            self._console_print("[bold red]Quick command timed out (30s)[/]")
                        except Exception as e:
                            self._console_print(f"[bold red]Quick command error: {e}[/]")
                    else:
                        self._console_print(f"[bold red]Quick command '{base_cmd}' has no command defined[/]")
                elif qcmd.get("type") == "alias":
                    target = qcmd.get("target", "").strip()
                    if target:
                        target = target if target.startswith("/") else f"/{target}"
                        user_args = cmd_original[len(base_cmd):].strip()
                        aliased_command = f"{target} {user_args}".strip()
                        return self.process_command(aliased_command)
                    else:
                        self._console_print(f"[bold red]Quick command '{base_cmd}' has no target defined[/]")
                else:
                    self._console_print(f"[bold red]Quick command '{base_cmd}' has unsupported type (supported: 'exec', 'alias')[/]")
            # Check for plugin-registered slash commands
            elif base_cmd.lstrip("/") in _get_plugin_cmd_handler_names():
                from reymen.reymen_cli.plugins import (
                    get_plugin_command_handler,
                    resolve_plugin_command_result,
                )
                plugin_handler = get_plugin_command_handler(base_cmd.lstrip("/"))
                if plugin_handler:
                    user_args = cmd_original[len(base_cmd):].strip()
                    try:
                        result = resolve_plugin_command_result(
                            plugin_handler(user_args)
                        )
                        if result:
                            _cprint(str(result))
                    except Exception as e:
                        _cprint(f"\033[1;31mPlugin command error: {e}{_RST}")
            # Skill bundles take precedence over individual skills — /<bundle>
            # loads multiple skills at once. Rescans cheaply when files change.
            elif base_cmd in skill_bundles:
                user_instruction = cmd_original[len(base_cmd):].strip()
                bundle_result = build_bundle_invocation_message(
                    base_cmd, user_instruction, task_id=self.session_id
                )
                if bundle_result:
                    msg, loaded_names, missing = bundle_result
                    bundle_info = skill_bundles[base_cmd]
                    print(
                        f"\n⚡ Loading bundle: {bundle_info['name']} "
                        f"({len(loaded_names)} skills)"
                    )
                    if missing:
                        ChatConsole().print(
                            f"[yellow]Skipped missing skills: {', '.join(missing)}[/]"
                        )
                    if hasattr(self, '_pending_input'):
                        self._pending_input.put(msg)
                else:
                    ChatConsole().print(
                        f"[bold red]Failed to load bundle for {base_cmd}[/]"
                    )
            # Check for skill slash commands (/gif-search, /axolotl, etc.)
            elif base_cmd in skill_commands:
                user_instruction = cmd_original[len(base_cmd):].strip()
                msg = build_skill_invocation_message(
                    base_cmd, user_instruction, task_id=self.session_id
                )
                if msg:
                    skill_name = skill_commands[base_cmd]["name"]
                    print(f"\n⚡ Loading skill: {skill_name}")
                    if hasattr(self, '_pending_input'):
                        self._pending_input.put(msg)
                else:
                    ChatConsole().print(f"[bold red]Failed to load skill for {base_cmd}[/]")
            else:
                # Prefix matching: if input uniquely identifies one command, execute it.
                # Matches against both built-in COMMANDS and installed skill commands so
                # that execution-time resolution agrees with tab-completion.
                from reymen.reymen_cli.commands import COMMANDS
                typed_base = cmd_lower.split()[0]
                all_known = set(COMMANDS) | set(skill_commands) | set(skill_bundles)
                matches = [c for c in all_known if c.startswith(typed_base)]
                if len(matches) > 1:
                    # Prefer an exact match (typed the full command name)
                    exact = [c for c in matches if c == typed_base]
                    if len(exact) == 1:
                        matches = exact
                    else:
                        # Prefer the unique shortest match:
                        # /qui → /quit (5) wins over /quint-pipeline (15)
                        min_len = min(len(c) for c in matches)
                        shortest = [c for c in matches if len(c) == min_len]
                        if len(shortest) == 1:
                            matches = shortest
                if len(matches) == 1:
                    # Expand the prefix to the full command name, preserving arguments.
                    # Guard against redispatching the same token to avoid infinite
                    # recursion when the expanded name still doesn't hit an exact branch
                    # (e.g. /config with extra args that are not yet handled above).
                    full_name = matches[0]
                    if full_name == typed_base:
                        # Already an exact token — no expansion possible; fall through
                        _cprint(f"\033[1;31mUnknown command: {cmd_lower}{_RST}")
                        _cprint(f"{_DIM}{_ACCENT}Type /help for available commands{_RST}")
                    else:
                        remainder = cmd_original.strip()[len(typed_base):]
                        full_cmd = full_name + remainder
                        return self.process_command(full_cmd)
                elif len(matches) > 1:
                    _cprint(f"{_ACCENT}Ambiguous command: {cmd_lower}{_RST}")
                    _cprint(f"{_DIM}Did you mean: {', '.join(sorted(matches))}?{_RST}")
                else:
                    _cprint(f"\033[1;31mUnknown command: {cmd_lower}{_RST}")
                    _cprint(f"{_DIM}{_ACCENT}Type /help for available commands{_RST}")
        
        return True

    def _handle_goal_command(self, cmd: str) -> None:
        """Dispatch /goal subcommands: set / status / pause / resume / clear.

        Delegates to :func:`handlers.system.goal_handler._handle_goal_command`.
        """
        from .handlers.system.goal_handler import _handle_goal_command
        _handle_goal_command(self, cmd)

    def _handle_subgoal_command(self, cmd: str) -> None:
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

        Delegates to :func:`handlers.system.subgoal_handler._handle_subgoal_command`.
        """
        from .handlers.system.subgoal_handler import _handle_subgoal_command
        _handle_subgoal_command(self, cmd)

    def _maybe_continue_goal_after_turn(self) -> None:
        """Hook run after every CLI turn. Judges + maybe re-queues.

        Safe to call when no goal is set — returns quickly.

        Preemption is automatic: if a real user message is already in
        ``_pending_input`` we skip judging (the user's new input takes
        priority and we'll re-judge after that turn). If judge says done,
        mark it done and tell the user. If judge says continue and we're
        under budget, push the continuation prompt onto the queue.

        Interrupt handling: if the turn was user-cancelled (Ctrl+C), we
        AUTO-PAUSE the goal instead of judging + re-queuing. Otherwise
        Ctrl+C feels like it did nothing — the judge runs on whatever
        partial output landed, almost always says "continue", and the
        loop keeps going. Auto-pause keeps the goal recoverable via
        ``/goal resume`` once the user has sorted out what they want.
        The empty-response skip mirrors the gateway guard at
        ``_handle_message`` in ``gateway/run.py``.
        """
        mgr = self._get_goal_manager()
        if mgr is None or not mgr.is_active():
            return

        # If a real user message is already queued, don't inject a
        # continuation prompt on top — let the user's turn go first.
        # Slash commands don't count as "real user messages" for this
        # check: they're inspection/mutation (e.g. /subgoal added mid-
        # run) and the process_loop dispatches them via process_command,
        # not via chat(). If we treat a queued /subgoal as preempting,
        # the goal loop silently stalls — we'd return here, then the
        # slash command consumes its queue slot via process_command()
        # which never re-fires the goal hook. Peek at all queued entries
        # and only defer when there's a non-slash payload.
        try:
            pending = getattr(self, "_pending_input", None)
            if pending is not None and not pending.empty():
                has_real_message = False
                try:
                    # Queue.queue is the underlying deque — direct peek
                    # without disturbing FIFO order.
                    for entry in list(pending.queue):
                        # Bundled payloads are (text, images) tuples;
                        # unpack for inspection.
                        if isinstance(entry, tuple) and entry:
                            entry = entry[0]
                        if isinstance(entry, str) and _looks_like_slash_command(entry):
                            continue
                        has_real_message = True
                        break
                except Exception:
                    # Fallback: if we can't introspect the queue, behave
                    # like the old check and defer to be safe.
                    has_real_message = True
                if has_real_message:
                    return
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")

        # If the turn was user-interrupted (Ctrl+C), auto-pause the goal
        # and bail. The judge call would almost always return "continue"
        # on the partial output and immediately re-queue another turn,
        # which is exactly what the user cancelled. Pausing (rather than
        # silently skipping) is the observable, recoverable behavior.
        if getattr(self, "_last_turn_interrupted", False):
            try:
                mgr.pause(reason="user-interrupted (Ctrl+C)")
            except Exception as exc:
                logging.debug("goal pause-on-interrupt failed: %s", exc)
            _cprint(
                f"  {_DIM}⏸ Goal paused — turn was interrupted. "
                f"Use /goal resume to continue, or /goal clear to stop.{_RST}"
            )
            return

        # Extract the agent's final response for this turn.
        last_response = ""
        try:
            hist = self.conversation_history or []
            for msg in reversed(hist):
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        # Multimodal content — flatten text parts.
                        parts = [
                            p.get("text", "")
                            for p in content
                            if isinstance(p, dict) and p.get("type") in {"text", "output_text"}
                        ]
                        last_response = "\n".join(t for t in parts if t)
                    else:
                        last_response = str(content or "")
                    break
        except Exception:
            last_response = ""

        # Skip judging on empty/whitespace-only responses. These are almost
        # always transient failures (API error, empty stream) where the
        # judge would say "continue" and trip the consecutive-parse-failures
        # backstop unnecessarily. Mirrors the gateway guard.
        if not last_response.strip():
            return

        decision = mgr.evaluate_after_turn(last_response, user_initiated=True)
        msg = decision.get("message") or ""
        if msg:
            _cprint(f"  {msg}")

        if decision.get("should_continue"):
            prompt = decision.get("continuation_prompt")
            if prompt:
                try:
                    self._pending_input.put(prompt)
                except Exception as exc:
                    logging.debug("goal continuation enqueue failed: %s", exc)

    def _handle_debug_command(self):
        """Handle /debug — upload debug report + logs and print paste URLs.

        Delegates to :func:`handlers.system.debug_handler._handle_debug_command`.
        """
        from .handlers.system.debug_handler import _handle_debug_command
        _handle_debug_command(self)

    def _handle_update_command(self) -> bool:
        """Handle /update — update ReYMeN Agent to the latest version.

        In the classic CLI this exits the session and relaunches as
        ``ReYMeN update`` so the user sees update output directly and gets
        the new version on next launch.

        Returns ``True`` when the update was confirmed (caller should trigger
        app exit so the relaunch is deferred to the main thread after
        prompt_toolkit cleans up terminal modes).  Returns ``False`` / falsy
        when cancelled.

        Delegates to :func:`handlers.system.update_handler._handle_update_command`.
        """
        from .handlers.system.update_handler import _handle_update_command
        return _handle_update_command(self)

    def _handle_voice_command(self, command: str):
        """Handle /voice [on|off|tts|status] command.

        Delegates to :func:`handlers.system.voice_handler._handle_voice_command`.
        """
        from .handlers.system.voice_handler import _handle_voice_command
        _handle_voice_command(self, command)

    def _toggle_voice_tts(self):
        """Toggle TTS output for voice mode."""
        if not self._voice_mode:
            _cprint(f"{_DIM}Enable voice mode first: /voice on{_RST}")
            return

        with self._voice_lock:
            self._voice_tts = not self._voice_tts
        status = "enabled" if self._voice_tts else "disabled"

        if self._voice_tts:
            from tools.tts_tool import check_tts_requirements
            if not check_tts_requirements():
                _cprint(f"{_DIM}Warning: No TTS provider available. Install edge-tts or set API keys.{_RST}")

        _cprint(f"{_ACCENT}Voice TTS {status}.{_RST}")

