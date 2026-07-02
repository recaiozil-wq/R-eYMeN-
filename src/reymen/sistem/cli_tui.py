"""cli_tui.py - ReYMeNCLI TUI/UI metotlari."""

import logging, os, re, sys, time, json, math, threading, shutil, textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

from src.reymen.sistem.cli_helpers import *
from src.reymen.sistem.cli_display import *
from src.reymen.sistem.cli_commands import *
from src.reymen.sistem.cli_auth import *
from src.reymen.sistem.cli_maintenance import *
from src.reymen.sistem.cli_stream import *
from contextlib import contextmanager



class TUIMixin:
    """TUI/UI metotlari mixin'i."""

    def _force_full_redraw(self) -> None:
        """Force a clean full-screen repaint of the prompt_toolkit UI.

        Used to recover from terminal buffer drift caused by external
        redraws we can't detect — e.g. macOS cmux / tmux tab switches,
        ``clear`` issued from a subshell, or SSH window restores. These
        wipe or repaint the terminal without firing SIGWINCH, so
        prompt_toolkit's tracked ``_cursor_pos`` no longer matches reality
        and the next incremental redraw stacks on top of stale content
        (ghost status bars, duplicated prompts).

        Bound to Ctrl+L and exposed as the ``/redraw`` slash command,
        matching the standard terminal-UX convention (bash, zsh, fish,
        vim, htop).
        """
        app = getattr(self, "_app", None)
        if not app:
            return
        self._clear_prompt_toolkit_screen(app)
        _replay_output_history()
        try:
            app.invalidate()
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")

    def _schedule_resize_recovery(self, app, original_on_resize, delay: float = 0.12) -> None:
        """Debounce resize redraws so footer chrome is not stamped into scrollback."""
        try:
            old_timer = getattr(self, "_resize_recovery_timer", None)
            lock = getattr(self, "_resize_recovery_lock", None)
            if lock is None:
                lock = threading.Lock()
                self._resize_recovery_lock = lock

            def _timer_fired(timer_ref):
                def _run_recovery():
                    with lock:
                        if getattr(self, "_resize_recovery_timer", None) is not timer_ref:
                            return
                        self._resize_recovery_timer = None
                        self._resize_recovery_pending = False
                    self._recover_after_resize(app, original_on_resize)

                try:
                    loop = app.loop  # type: ignore[attr-defined]
                except Exception:
                    loop = None
                if loop is not None:
                    try:
                        loop.call_soon_threadsafe(_run_recovery)
                        return
                    except Exception:
                        logger.warning("[fix_01_sessiz_except] Exception")
                _run_recovery()

            with lock:
                if old_timer is not None:
                    try:
                        old_timer.cancel()
                    except Exception:
                        logger.warning("[fix_01_sessiz_except] Exception")
                self._resize_recovery_pending = True
                timer = threading.Timer(delay, lambda: _timer_fired(timer))
                timer.daemon = True
                self._resize_recovery_timer = timer
                timer.start()
        except Exception:
            self._resize_recovery_pending = False
            self._recover_after_resize(app, original_on_resize)

    def _status_bar_context_style(self, percent_used: Optional[int]) -> str:
        if percent_used is None:
            return "class:status-bar-dim"
        if percent_used >= 95:
            return "class:status-bar-critical"
        if percent_used > 80:
            return "class:status-bar-bad"
        if percent_used >= 50:
            return "class:status-bar-warn"
        return "class:status-bar-good"

    def _build_context_bar(self, percent_used: Optional[int], width: int = 10) -> str:
        safe_percent = max(0, min(100, percent_used or 0))
        filled = round((safe_percent / 100) * width)
        return f"[{('█' * filled) + ('░' * max(0, width - filled))}]"

    def _format_prompt_elapsed(prompt_start_time: Optional[float], prompt_duration: float, live: bool = False) -> str:
        """Format per-prompt elapsed time for the status bar.

        Always returns a string — shows 0s on fresh start before first turn.
        Keeps seconds visible at all scales so it increments smoothly:
            59s → 1m → 1m 1s → ... → 1m 59s → 2m → 2m 1s → ...
            59m 59s → 1h → 1h 0m 1s → ...
            23h 59m 59s → 1d → 1d 0h 1m → ...

        Emoji prefix: ⏱ when turn is live, ⏲ when frozen or fresh start.
        Uses width-1 (no variation selector) glyphs so the status bar stays
        aligned in monospace terminals.
        """
        if prompt_start_time is None and prompt_duration == 0.0:
            return "⏲ 0s"
        elapsed = time.time() - prompt_start_time if prompt_start_time is not None else prompt_duration
        elapsed = max(0.0, elapsed)

        days = int(elapsed // 86400)
        remaining = elapsed % 86400
        hours = int(remaining // 3600)
        remaining = remaining % 3600
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)

        if days > 0:
            time_str = f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            time_str = f"{hours}h {minutes}m {seconds}s" if seconds else f"{hours}h {minutes}m"
        elif minutes > 0:
            time_str = f"{minutes}m {seconds}s" if seconds else f"{minutes}m"
        else:
            time_str = f"{int(elapsed)}s"

        emoji = "⏱" if live else "⏲"
        return f"{emoji} {time_str}"

    def _get_status_bar_snapshot(self) -> Dict[str, Any]:
        # Prefer the agent's model name — it updates on fallback.
        # self.model reflects the originally configured model and never
        # changes mid-session, so the TUI would show a stale name after
        # _try_activate_fallback() switches provider/model.
        agent = getattr(self, "agent", None)
        model_name = (getattr(agent, "model", None) or self.model or "unknown")
        model_short = model_name.split("/")[-1] if "/" in model_name else model_name
        if model_short.endswith(".gguf"):
            model_short = model_short[:-5]
        if len(model_short) > 26:
            model_short = f"{model_short[:23]}..."

        elapsed_seconds = max(0.0, (datetime.now() - self.session_start).total_seconds())
        snapshot = {
            "model_name": model_name,
            "model_short": model_short,
            "duration": format_duration_compact(elapsed_seconds),
            "prompt_elapsed": self._format_prompt_elapsed(
                getattr(self, "_prompt_start_time", None),
                getattr(self, "_prompt_duration", 0.0),
                live=getattr(self, "_prompt_start_time", None) is not None,
            ),
            "context_tokens": 0,
            "context_length": None,
            "context_percent": None,
            "session_input_tokens": 0,
            "session_output_tokens": 0,
            "session_cache_read_tokens": 0,
            "session_cache_write_tokens": 0,
            "session_prompt_tokens": 0,
            "session_completion_tokens": 0,
            "session_total_tokens": 0,
            "session_api_calls": 0,
            "compressions": 0,
            "active_background_tasks": 0,
            "active_background_processes": 0,
        }

        # Count live /background tasks. The dict entry is removed in the
        # task thread's finally block, so len() reflects truly-running tasks.
        # len() on a CPython dict is atomic; safe to read without a lock.
        try:
            bg_tasks = getattr(self, "_background_tasks", None)
            if bg_tasks:
                snapshot["active_background_tasks"] = len(bg_tasks)
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")

        # Count live background terminal processes (terminal tool background
        # sessions tracked by tools.process_registry). Cheap O(1) read.
        try:
            from tools.process_registry import process_registry
            snapshot["active_background_processes"] = process_registry.count_running()
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")


        if not agent:
            return snapshot

        snapshot["session_input_tokens"] = getattr(agent, "session_input_tokens", 0) or 0
        snapshot["session_output_tokens"] = getattr(agent, "session_output_tokens", 0) or 0
        snapshot["session_cache_read_tokens"] = getattr(agent, "session_cache_read_tokens", 0) or 0
        snapshot["session_cache_write_tokens"] = getattr(agent, "session_cache_write_tokens", 0) or 0
        snapshot["session_prompt_tokens"] = getattr(agent, "session_prompt_tokens", 0) or 0
        snapshot["session_completion_tokens"] = getattr(agent, "session_completion_tokens", 0) or 0
        snapshot["session_total_tokens"] = getattr(agent, "session_total_tokens", 0) or 0
        snapshot["session_api_calls"] = getattr(agent, "session_api_calls", 0) or 0

        compressor = getattr(agent, "context_compressor", None)
        if compressor:
            # last_prompt_tokens is parked at the -1 sentinel right after a
            # compression, until the next real API call reports a prompt count
            # (awaiting_real_usage_after_compression). The status bar must not
            # render that sentinel verbatim — it produced "-1/200K" / "-1%".
            # Clamp it to 0 so the one transitional turn reads as empty context.
            context_tokens = getattr(compressor, "last_prompt_tokens", 0) or 0
            if context_tokens < 0:
                context_tokens = 0
            context_length = getattr(compressor, "context_length", 0) or 0
            if context_length < 0:
                context_length = 0
            snapshot["context_tokens"] = context_tokens
            snapshot["context_length"] = context_length or None
            snapshot["compressions"] = getattr(compressor, "compression_count", 0) or 0
            if context_length:
                snapshot["context_percent"] = max(0, min(100, round((context_tokens / context_length) * 100)))

        return snapshot

    def _status_bar_display_width(text: str) -> int:
        """Return terminal cell width for status-bar text.

        len() is not enough for prompt_toolkit layout decisions because some
        glyphs can render wider than one Python codepoint. Keeping the status
        bar within the real display width prevents it from wrapping onto a
        second line and leaving behind duplicate rows.
        """
        try:
            from prompt_toolkit.utils import get_cwidth
            return get_cwidth(text or "")
        except Exception:
            return len(text or "")

    def _scrollback_box_width(width: Optional[int] = None) -> int:
        """Return the full viewport width for printed scrollback box rules.

        Previously this clamped to ``max(32, min(width, 56))`` as a defense
        against terminal-emulator reflow on column-shrink (#25975, salvaging
        #24403).  That clamp made response/reasoning borders look stubby on
        any modern wide terminal.  We now trust the prompt_toolkit
        ``_output_screen_diff`` monkey-patch landed in #26137 (salvaging
        #25981) to keep chrome out of scrollback in the first place, and
        accept that an aggressive column-shrink may visually reflow already
        printed Panel borders — that's a cosmetic artifact of stamped
        scrollback history, not a live-render bug.

        A small floor (32 cols) is kept so the box still renders on tiny
        terminals without negative ``'─' * (w - 2)`` math.
        """
        if width is None:
            try:
                width = shutil.get_terminal_size((80, 24)).columns
            except Exception:
                width = 80
        return max(32, int(width or 80))

    def _tui_input_rule_height(self, position: str, width: Optional[int] = None) -> int:
        """Return the visible height for the top/bottom input separator rules."""
        if position not in {"top", "bottom"}:
            raise ValueError(f"Unknown input rule position: {position}")
        if getattr(self, "_status_bar_suppressed_after_resize", False):
            return 0
        if position == "top":
            return 1
        return 0 if self._use_minimal_tui_chrome(width=width) else 1

    def _agent_spacer_height(self, width: Optional[int] = None) -> int:
        """Return the spacer height shown above the status bar while the agent runs."""
        if not getattr(self, "_agent_running", False):
            return 0
        return 0 if self._use_minimal_tui_chrome(width=width) else 1

    def _spinner_widget_height(self, width: Optional[int] = None) -> int:
        """Return the visible height for the spinner/status text line above the status bar."""
        spinner_line = self._render_spinner_text()
        if not spinner_line:
            return 0
        if self._use_minimal_tui_chrome(width=width):
            return 0
        width = width or self._get_tui_terminal_width()
        if width and width > 10:
            import math
            text_width = self._status_bar_display_width(spinner_line)
            return max(1, math.ceil(text_width / width))
        return 1

    def _render_spinner_text(self) -> str:
        """Return the live spinner/status text exactly as rendered in the TUI."""
        txt = getattr(self, "_spinner_text", "")
        if not txt:
            return ""
        t0 = getattr(self, "_tool_start_time", 0) or 0
        if t0 > 0:
            elapsed = time.monotonic() - t0
            if elapsed >= 60:
                _m, _s = int(elapsed // 60), int(elapsed % 60)
                # Fixed-width timer to avoid status-line wrap jitter while
                # scrolling/repainting (e.g. 01m05s, 12m09s).
                elapsed_str = f"{_m:02d}m{_s:02d}s"
            else:
                # Keep width stable before the 60s rollover as well.
                elapsed_str = f"{elapsed:5.1f}s"
            return f"  {txt}  ({elapsed_str})"
        return f"  {txt}"

    def _get_voice_status_fragments(self, width: Optional[int] = None):
        """Return the voice status bar fragments for the interactive TUI."""
        width = width or self._get_tui_terminal_width()
        compact = self._use_minimal_tui_chrome(width=width)
        label = self._voice_record_key_label()
        if self._voice_recording:
            if compact:
                return [("class:voice-status-recording", " ● REC ")]
            return [("class:voice-status-recording", f" ● REC  {label} to stop ")]
        if self._voice_processing:
            if compact:
                return [("class:voice-status", " ◉ STT ")]
            return [("class:voice-status", " ◉ Transcribing... ")]
        if compact:
            return [("class:voice-status", f" 🎤 {label} ")]
        tts = " | TTS on" if self._voice_tts else ""
        cont = " | Continuous" if self._voice_continuous else ""
        return [("class:voice-status", f" 🎤 Voice mode{tts}{cont}  —  {label} to record ")]

    def _get_status_bar_fragments(self):
        if not self._status_bar_visible or getattr(self, '_model_picker_state', None):
            return []
        try:
            snapshot = self._get_status_bar_snapshot()
            # Use prompt_toolkit's own terminal width when running inside the
            # TUI — shutil.get_terminal_size() can return stale or fallback
            # values (especially on SSH) that differ from what prompt_toolkit
            # actually renders, causing the fragments to overflow to a second
            # line and produce duplicated status bar rows over long sessions.
            width = self._get_tui_terminal_width()
            duration_label = snapshot["duration"]
            yolo_active = self._is_session_yolo_active()

            if width < 52:
                frags = [
                    ("class:status-bar", " ⚕ "),
                    ("class:status-bar-strong", snapshot["model_short"]),
                    ("class:status-bar-dim", " · "),
                    ("class:status-bar-dim", duration_label),
                ]
                if yolo_active:
                    frags.append(("class:status-bar-dim", " · "))
                    frags.append(("class:status-bar-yolo", "⚠ YOLO"))
                frags.append(("class:status-bar", " "))
            else:
                percent = snapshot["context_percent"]
                percent_label = f"{percent}%" if percent is not None else "--"
                if width < 76:
                    compressions = snapshot.get("compressions", 0)
                    bg_count = snapshot.get("active_background_tasks", 0)
                    bg_proc_count = snapshot.get("active_background_processes", 0)
                    frags = [
                        ("class:status-bar", " ⚕ "),
                        ("class:status-bar-strong", snapshot["model_short"]),
                        ("class:status-bar-dim", " · "),
                        (self._status_bar_context_style(percent), percent_label),
                    ]
                    if compressions:
                        frags.append(("class:status-bar-dim", " · "))
                        frags.append((self._compression_count_style(compressions), f"🗜️ {compressions}"))
                    if bg_count:
                        frags.append(("class:status-bar-dim", " · "))
                        frags.append(("class:status-bar-strong", f"▶ {bg_count}"))
                    if bg_proc_count:
                        frags.append(("class:status-bar-dim", " · "))
                        frags.append(("class:status-bar-strong", f"⚙ {bg_proc_count}"))
                    frags.extend([
                        ("class:status-bar-dim", " · "),
                        ("class:status-bar-dim", duration_label),
                    ])
                    if yolo_active:
                        frags.append(("class:status-bar-dim", " · "))
                        frags.append(("class:status-bar-yolo", "⚠ YOLO"))
                    frags.append(("class:status-bar", " "))
                else:
                    if snapshot["context_length"]:
                        ctx_total = _format_context_length(snapshot["context_length"])
                        ctx_used = format_token_count_compact(snapshot["context_tokens"])
                        context_label = f"{ctx_used}/{ctx_total}"
                    else:
                        context_label = "ctx --"

                    bar_style = self._status_bar_context_style(percent)
                    compressions = snapshot.get("compressions", 0)
                    bg_count = snapshot.get("active_background_tasks", 0)
                    bg_proc_count = snapshot.get("active_background_processes", 0)
                    frags = [
                        ("class:status-bar", " ⚕ "),
                        ("class:status-bar-strong", snapshot["model_short"]),
                        ("class:status-bar-dim", " │ "),
                        ("class:status-bar-dim", context_label),
                        ("class:status-bar-dim", " │ "),
                        (bar_style, self._build_context_bar(percent)),
                        ("class:status-bar-dim", " "),
                        (bar_style, percent_label),
                    ]
                    if compressions:
                        frags.append(("class:status-bar-dim", " │ "))
                        frags.append((self._compression_count_style(compressions), f"🗜️ {compressions}"))
                    if bg_count:
                        frags.append(("class:status-bar-dim", " │ "))
                        frags.append(("class:status-bar-strong", f"▶ {bg_count}"))
                    if bg_proc_count:
                        frags.append(("class:status-bar-dim", " │ "))
                        frags.append(("class:status-bar-strong", f"⚙ {bg_proc_count}"))
                    frags.extend([
                        ("class:status-bar-dim", " │ "),
                        ("class:status-bar-dim", duration_label),
                    ])
                    # Position 7: per-prompt elapsed timer (live or frozen)
                    prompt_elapsed = snapshot.get("prompt_elapsed")
                    if prompt_elapsed:
                        frags.append(("class:status-bar-dim", " │ "))
                        frags.append(("class:status-bar-dim", prompt_elapsed))
                    if yolo_active:
                        frags.append(("class:status-bar-dim", " │ "))
                        frags.append(("class:status-bar-yolo", "⚠ YOLO"))
                    frags.append(("class:status-bar", " "))

            total_width = sum(self._status_bar_display_width(text) for _, text in frags)
            if total_width > width:
                plain_text = "".join(text for _, text in frags)
                trimmed = self._trim_status_bar_text(plain_text, width)
                return [("class:status-bar", trimmed)]
            return frags
        except Exception:
            return [("class:status-bar", f" {self._build_status_bar_text()} ")]

    def _expand_paste_references(self, text: str | None) -> str:
        """Expand [Pasted text #N -> file] placeholders into file contents."""
        if not isinstance(text, str) or "[Pasted text #" not in text:
            return text or ""
        paste_ref_re = re.compile(r'\[Pasted text #\d+: \d+ lines \u2192 (.+?)\]')

        def _expand_ref(match):
            path = Path(match.group(1))
            # Use try/except instead of path.exists() to avoid TOCTOU race:
            # the paste file may be deleted between check and read, causing
            # the input to be silently dropped (#17666).
            try:
                return path.read_text(encoding="utf-8")
            except (OSError, IOError):
                logger.warning("Paste file gone or unreadable, returning placeholder: %s", path)
                return match.group(0)

        return paste_ref_re.sub(_expand_ref, text)

    def _print_user_message_preview(self, user_input: str) -> None:
        """Render a user message using the normal chat scrollback style."""
        ChatConsole().print(f"[{_accent_hex()}]{'─' * 40}[/]")
        text = str(user_input or "")
        if "\n" in text:
            ChatConsole().print(self._format_submitted_user_message_preview(text))
        else:
            ChatConsole().print(f"[bold {_accent_hex()}]●[/] [bold]{_escape(text)}[/]")

    def _render_resume_history_panel_lines(self, panel) -> list[str]:
        """Render the resume panel at the current terminal width for resize replay."""
        from io import StringIO

        buf = StringIO()
        width = shutil.get_terminal_size((80, 24)).columns
        console = Console(
            file=buf,
            force_terminal=True,
            color_system="truecolor",
            highlight=False,
            width=width,
        )
        with _suspend_output_history():
            console.print(panel)
        return buf.getvalue().rstrip("\n").splitlines()

    def _enable_voice_mode(self):
        """Enable voice mode after checking requirements."""
        if self._voice_mode:
            _cprint(f"{_DIM}Voice mode is already enabled.{_RST}")
            return

        from tools.voice_mode import check_voice_requirements, detect_audio_environment

        # Environment detection -- warn and block in incompatible environments
        env_check = detect_audio_environment()
        if not env_check["available"]:
            _cprint(f"\n{_ACCENT}Voice mode unavailable in this environment:{_RST}")
            for warning in env_check["warnings"]:
                _cprint(f"  {_DIM}{warning}{_RST}")
            return

        reqs = check_voice_requirements()
        if not reqs["available"]:
            _cprint(f"\n{_ACCENT}Voice mode requirements not met:{_RST}")
            for line in reqs["details"].split("\n"):
                _cprint(f"  {_DIM}{line}{_RST}")
            if reqs["missing_packages"]:
                if _is_termux_environment():
                    _cprint(f"\n  {_BOLD}Option 1: pkg install termux-api{_RST}")
                    _cprint(f"  {_DIM}Then install/update the Termux:API Android app for microphone capture{_RST}")
                    _cprint(f"  {_BOLD}Option 2: pkg install python-numpy portaudio && python -m pip install sounddevice{_RST}")
                else:
                    _cprint(f"\n  {_BOLD}Install: {sys.executable} -m pip install {' '.join(reqs['missing_packages'])}{_RST}")
            return

        with self._voice_lock:
            self._voice_mode = True

        # Check config for auto_tts (shape-safe — malformed ``voice:`` YAML
        # leaves ``voice_config`` as a non-dict, so guard before .get()).
        try:
            from reymen.reymen_cli.config import load_config
            _raw_voice = load_config().get("voice")
            voice_config = _raw_voice if isinstance(_raw_voice, dict) else {}
            if voice_config.get("auto_tts", False):
                with self._voice_lock:
                    self._voice_tts = True
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")

        # Voice mode instruction is injected as a user message prefix (not a
        # system prompt change) to avoid invalidating the prompt cache.  See
        # _voice_message_prefix property and its usage in _process_message().

        tts_status = " (TTS enabled)" if self._voice_tts else ""
        # Use the startup-pinned cache so the advertised shortcut always
        # matches the live prompt_toolkit binding — reading live config
        # here would drift after a mid-session config edit (Copilot
        # round-14 on #19835, same class as round-13).
        _ptt_display = self._voice_record_key_label()
        _cprint(f"\n{_ACCENT}Voice mode enabled{tts_status}{_RST}")
        _cprint(f"  {_DIM}{_ptt_display} to start/stop recording{_RST}")
        _cprint(f"  {_DIM}/voice tts  to toggle speech output{_RST}")
        _cprint(f"  {_DIM}/voice off  to disable voice mode{_RST}")

    def _disable_voice_mode(self):
        """Disable voice mode, cancel any active recording, and stop TTS."""
        recorder = None
        with self._voice_lock:
            if self._voice_recording and self._voice_recorder:
                self._voice_recorder.cancel()
                self._voice_recording = False
            recorder = self._voice_recorder
            self._voice_mode = False
            self._voice_tts = False
            self._voice_continuous = False

        # Shut down the persistent audio stream in background
        if recorder is not None:
            def _bg_shutdown(rec=recorder):
                try:
                    rec.shutdown()
                except Exception:
                    logger.warning("[fix_01_sessiz_except] Exception")
            threading.Thread(target=_bg_shutdown, daemon=True).start()
            self._voice_recorder = None

        # Stop any active TTS playback
        try:
            from tools.voice_mode import stop_playback
            stop_playback()
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")
        self._voice_tts_done.set()

        _cprint(f"\n{_DIM}Voice mode disabled.{_RST}")

    def _show_voice_status(self):
        """Show current voice mode status."""
        from tools.voice_mode import check_voice_requirements

        reqs = check_voice_requirements()

        _cprint(f"\n{_BOLD}Voice Mode Status{_RST}")
        _cprint(f"  Mode:      {'ON' if self._voice_mode else 'OFF'}")
        _cprint(f"  TTS:       {'ON' if self._voice_tts else 'OFF'}")
        _cprint(f"  Recording: {'YES' if self._voice_recording else 'no'}")
        # Display the startup-pinned label so /voice status always
        # matches the live prompt_toolkit binding (Copilot round-14 on
        # #19835, same class as round-13). Reading live config here
        # would drift after a mid-session config edit.
        _cprint(f"  Record key: {self._voice_record_key_label()}")
        _cprint(f"\n  {_BOLD}Requirements:{_RST}")
        for line in reqs["details"].split("\n"):
            _cprint(f"    {line}")

    def _get_approval_display_fragments(self):
        """Render the dangerous-command approval panel for the prompt_toolkit UI.

        Layout priority: title + command + choices must always render, even if
        the terminal is short or the description is long. Description is placed
        at the bottom of the panel and gets truncated to fit the remaining row
        budget. This prevents HSplit from clipping approve/deny off-screen when
        tirith findings produce multi-paragraph descriptions or when the user
        runs in a compact terminal pane.
        """
        state = self._approval_state
        if not state:
            return []

        def _panel_box_width(title_text: str, content_lines: list[str], min_width: int = 46, max_width: int = 76) -> int:
            term_cols = shutil.get_terminal_size((100, 20)).columns
            longest = max([len(title_text)] + [len(line) for line in content_lines] + [min_width - 4])
            inner = min(max(longest + 4, min_width - 2), max_width - 2, max(24, term_cols - 6))
            return inner + 2

        def _wrap_panel_text(text: str, width: int, subsequent_indent: str = "") -> list[str]:
            wrapped = textwrap.wrap(
                text,
                width=max(8, width),
                replace_whitespace=False,
                drop_whitespace=False,
                subsequent_indent=subsequent_indent,
            )
            return wrapped or [""]

        def _append_panel_line(lines, border_style: str, content_style: str, text: str, box_width: int) -> None:
            inner_width = max(0, box_width - 2)
            lines.append((border_style, "│ "))
            lines.append((content_style, text.ljust(inner_width)))
            lines.append((border_style, " │\n"))

        def _append_blank_panel_line(lines, border_style: str, box_width: int) -> None:
            lines.append((border_style, "│" + (" " * box_width) + "│\n"))

        command = state["command"]
        description = state["description"]
        choices = state["choices"]
        selected = state.get("selected", 0)
        show_full = state.get("show_full", False)

        title = "⚠️  Dangerous Command"
        cmd_display = command if show_full or len(command) <= 70 else command[:70] + '...'
        choice_labels = {
            "once": "Allow once",
            "session": "Allow for this session",
            "always": "Add to permanent allowlist",
            "deny": "Deny",
            "view": "Show full command",
        }

        preview_lines = _wrap_panel_text(description, 60)
        preview_lines.extend(_wrap_panel_text(cmd_display, 60))
        for i, choice in enumerate(choices):
            prefix = '❯ ' if i == selected else '  '
            preview_lines.extend(_wrap_panel_text(
                f"{prefix}{choice_labels.get(choice, choice)}",
                60,
                subsequent_indent="  ",
            ))

        box_width = _panel_box_width(title, preview_lines)
        inner_text_width = max(8, box_width - 2)

        # Pre-wrap the mandatory content — command + choices must always render.
        cmd_wrapped = _wrap_panel_text(cmd_display, inner_text_width)

        # (choice_index, wrapped_line) so we can re-apply selected styling below
        choice_wrapped: list[tuple[int, str]] = []
        for i, choice in enumerate(choices):
            label = choice_labels.get(choice, choice)
            # Show number prefix for quick selection (1-9 for items 1-9, 0 for 10th item)
            if i < 9:
                num_prefix = str(i + 1)
            elif i == 9:
                num_prefix = '0'
            else:
                num_prefix = ' '  # No number for items beyond 10th
            if i == selected:
                prefix = f'❯ {num_prefix}. '
            else:
                prefix = f'  {num_prefix}. '
            for wrapped in _wrap_panel_text(f"{prefix}{label}", inner_text_width, subsequent_indent="    "):
                choice_wrapped.append((i, wrapped))

        # Budget vertical space so HSplit never clips the command or choices.
        # Panel chrome (full layout with separators):
        #   top border + title + blank_after_title
        #   + blank_between_cmd_choices + bottom border = 5 rows.
        # In tight terminals we collapse to:
        #   top border + title + bottom border = 3 rows (no blanks).
        #
        # reserved_below: rows consumed below the approval panel by the
        # spinner/tool-progress line, status bar, input area, separators, and
        # prompt symbol. Measured at ~6 rows during live PTY approval prompts;
        # budget 6 so we don't overestimate the panel's room.
        term_rows = shutil.get_terminal_size((100, 24)).lines
        chrome_full = 5
        chrome_tight = 3
        reserved_below = 6

        available = max(0, term_rows - reserved_below)
        mandatory_full = chrome_full + len(cmd_wrapped) + len(choice_wrapped)

        # If the full-chrome panel doesn't fit, drop the separator blanks.
        # This keeps the command and every choice on-screen in compact terminals.
        use_compact_chrome = mandatory_full > available
        chrome_rows = chrome_tight if use_compact_chrome else chrome_full

        # If the command itself is too long to leave room for choices (e.g. user
        # hit "view" on a multi-hundred-character command), truncate it so the
        # approve/deny buttons still render. Keep at least 1 row of command.
        max_cmd_rows = max(1, available - chrome_rows - len(choice_wrapped))
        if len(cmd_wrapped) > max_cmd_rows:
            keep = max(1, max_cmd_rows - 1) if max_cmd_rows > 1 else 1
            cmd_wrapped = cmd_wrapped[:keep] + ["… (command truncated — use /logs or /debug for full text)"]

        # Allocate any remaining rows to description. The extra -1 in full mode
        # accounts for the blank separator between choices and description.
        mandatory_no_desc = chrome_rows + len(cmd_wrapped) + len(choice_wrapped)
        desc_sep_cost = 0 if use_compact_chrome else 1
        available_for_desc = available - mandatory_no_desc - desc_sep_cost
        # Even on huge terminals, cap description height so the panel stays compact.
        available_for_desc = max(0, min(available_for_desc, 10))

        desc_wrapped = _wrap_panel_text(description, inner_text_width) if description else []
        if available_for_desc < 1 or not desc_wrapped:
            desc_wrapped = []
        elif len(desc_wrapped) > available_for_desc:
            keep = max(1, available_for_desc - 1)
            desc_wrapped = desc_wrapped[:keep] + ["… (description truncated)"]

        # Render: title → command → choices → description (description last so
        # any remaining overflow clips from the bottom of the least-critical
        # content, never from the command or choices). Use compact chrome (no
        # blank separators) when the terminal is tight.
        lines = []
        lines.append(('class:approval-border', '╭' + ('─' * box_width) + '╮\n'))
        _append_panel_line(lines, 'class:approval-border', 'class:approval-title', title, box_width)
        if not use_compact_chrome:
            _append_blank_panel_line(lines, 'class:approval-border', box_width)

        for wrapped in cmd_wrapped:
            _append_panel_line(lines, 'class:approval-border', 'class:approval-cmd', wrapped, box_width)
        if not use_compact_chrome:
            _append_blank_panel_line(lines, 'class:approval-border', box_width)

        for i, wrapped in choice_wrapped:
            style = 'class:approval-selected' if i == selected else 'class:approval-choice'
            _append_panel_line(lines, 'class:approval-border', style, wrapped, box_width)

        if desc_wrapped:
            if not use_compact_chrome:
                _append_blank_panel_line(lines, 'class:approval-border', box_width)
            for wrapped in desc_wrapped:
                _append_panel_line(lines, 'class:approval-border', 'class:approval-desc', wrapped, box_width)

        lines.append(('class:approval-border', '╰' + ('─' * box_width) + '╯\n'))
        return lines

    def _get_tui_prompt_symbols(self) -> tuple[str, str]:
        """Return ``(normal_prompt, state_suffix)`` for the active skin.

        ``normal_prompt`` is the full ``branding.prompt_symbol``.
        ``state_suffix`` is what special states (sudo/secret/approval/agent)
        should render after their leading icon.

        When a profile is active (not "default"), the profile name is
        prepended to the prompt symbol: ``coder ❯`` instead of ``❯``.
        """
        try:
            from reymen.reymen_cli.skin_engine import get_active_prompt_symbol
            symbol = get_active_prompt_symbol("❯ ")
        except Exception:
            symbol = "❯ "

        symbol = (symbol or "❯ ").rstrip() + " "

        # Prepend profile name when not default
        try:
            from reymen.reymen_cli.profiles import get_active_profile_name
            profile = get_active_profile_name()
            if profile not in {"default", "custom"}:
                symbol = f"{profile} {symbol}"
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")
        stripped = symbol.rstrip()
        if not stripped:
            return "❯ ", "❯ "

        parts = stripped.split()
        candidate = parts[-1] if parts else ""
        arrow_chars = ("❯", ">", "$", "#", "›", "»", "→")
        if any(ch in candidate for ch in arrow_chars):
            return symbol, candidate.rstrip() + " "

        # Icon-only custom prompts should still remain visible in special states.
        return symbol, symbol

    def _get_tui_prompt_fragments(self):
        """Return the prompt_toolkit fragments for the current interactive state."""
        symbol, state_suffix = self._get_tui_prompt_symbols()
        compact = self._use_minimal_tui_chrome(width=self._get_tui_terminal_width())

        def _state_fragment(style: str, icon: str, extra: str = ""):
            if compact:
                text = icon
                if extra:
                    text = f"{text} {extra.strip()}".rstrip()
                return [(style, text + " ")]
            if extra:
                return [(style, f"{icon} {extra} {state_suffix}")]
            return [(style, f"{icon} {state_suffix}")]

        if self._voice_recording:
            bar = self._audio_level_bar()
            return _state_fragment("class:voice-recording", "●", bar)
        if self._voice_processing:
            return _state_fragment("class:voice-processing", "◉")
        if self._sudo_state:
            return _state_fragment("class:sudo-prompt", "🔐")
        if self._secret_state:
            return _state_fragment("class:sudo-prompt", "🔑")
        if self._approval_state:
            return _state_fragment("class:prompt-working", "⚠")
        if getattr(self, "_slash_confirm_state", None):
            return _state_fragment("class:prompt-working", "⚠")
        if self._clarify_freetext:
            return _state_fragment("class:clarify-selected", "✎")
        if self._clarify_state:
            return _state_fragment("class:prompt-working", "?")
        if self._command_running:
            return _state_fragment("class:prompt-working", self._command_spinner_frame())
        if self._agent_running:
            return _state_fragment("class:prompt-working", "⚕")
        if self._voice_mode:
            return _state_fragment("class:voice-prompt", "🎤")
        return [("class:prompt", symbol)]

    def _get_tui_prompt_text(self) -> str:
        """Return the visible prompt text for width calculations."""
        return "".join(text for _, text in self._get_tui_prompt_fragments())

    def _build_tui_style_dict(self) -> dict[str, str]:
        """Layer the active skin's prompt_toolkit colors over the base TUI style.

        Also rewrites any hex-color tokens in the resulting style strings
        to their light-mode equivalents (via _LIGHT_MODE_REMAP) when the
        terminal is detected as light.  This makes the chrome readable
        on cream Terminal.app backgrounds without per-skin overrides.
        """
        style_dict = dict(getattr(self, "_tui_style_base", {}) or {})
        try:
            from reymen.reymen_cli.skin_engine import get_prompt_toolkit_style_overrides
            style_dict.update(get_prompt_toolkit_style_overrides())
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")
        # Light-mode remap on the style strings.  Each value is a pt
        # style string like "bg:#1a1a2e #C0C0C0 bold" — split on space,
        # rewrite any "#XXX" tokens (including "bg:#XXX") through the
        # light-mode remap, rejoin.
        #
        # CRITICAL: skip the remap entirely when a style string already
        # specifies its own bg (e.g. status-bar / completion-menu styles
        # with `bg:#1a1a2e ...`).  Those colors were tuned for that
        # specific dark bg and remapping the FG to a dark equivalent
        # would produce dark-on-dark (invisible).  The terminal's BG
        # mode is irrelevant — what matters is the bg the style itself
        # paints.
        try:
            if _detect_light_mode():
                def _remap_value(v: str) -> str:
                    if not v:
                        return v
                    tokens = v.split()
                    has_explicit_bg = any(t.startswith("bg:") for t in tokens)
                    if has_explicit_bg:
                        # The style paints its own bg — leave its fg alone.
                        return v
                    return " ".join(
                        _maybe_remap_for_light_mode(t) if t.startswith("#") else t
                        for t in tokens
                    )
                style_dict = {k: _remap_value(v or "") for k, v in style_dict.items()}
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")
        return style_dict

    def _apply_tui_skin_style(self) -> bool:
        """Refresh prompt_toolkit styling for a running interactive TUI."""
        if not getattr(self, "_app", None) or not getattr(self, "_tui_style_base", None):
            return False
        self._app.style = PTStyle.from_dict(self._build_tui_style_dict())
        self._invalidate(min_interval=0.0)
        return True

    def _register_extra_tui_keybindings(self, kb, *, input_area) -> None:
        """Register extra keybindings on the TUI ``KeyBindings`` object.

        Wrapper CLIs can override this to add keybindings (e.g. transport
        controls, modal shortcuts) without overriding ``run()``.

        Parameters
        ----------
        kb : KeyBindings
            The active keybinding registry for the prompt_toolkit application.
        input_area : TextArea
            The main input widget, for wrappers that need to inspect or
            manipulate user input from a keybinding handler.
        """

    def _build_tui_layout_children(
        self,
        *,
        sudo_widget,
        secret_widget,
        approval_widget,
        slash_confirm_widget=None,
        clarify_widget,
        model_picker_widget=None,
        spinner_widget=None,
        spacer,
        status_bar,
        input_rule_top,
        image_bar,
        input_area,
        input_rule_bot,
        voice_status_bar,
        completions_menu,
    ) -> list:
        """Assemble the ordered list of children for the root ``HSplit``.

        Wrapper CLIs typically override ``_get_extra_tui_widgets`` instead of
        this method.  Override this only when you need full control over widget
        ordering.
        """
        return [
            item for item in [
                Window(height=0),
                sudo_widget,
                secret_widget,
                approval_widget,
                slash_confirm_widget,
                clarify_widget,
                model_picker_widget,
                spinner_widget,
                spacer,
                *self._get_extra_tui_widgets(),
                status_bar,
                input_rule_top,
                image_bar,
                input_area,
                input_rule_bot,
                voice_status_bar,
                completions_menu,
            ] if item is not None
        ]



    def _clear_prompt_toolkit_screen(self, app, *, rebuild_scrollback: bool = False) -> None:
        """Clear the terminal and reset prompt_toolkit renderer state."""
        try:
            renderer = app.renderer
            out = renderer.output
            out.reset_attributes()
            out.erase_screen()
            if rebuild_scrollback:
                try:
                    out.write_raw("\x1b[3J")
                except Exception:
                    logger.warning("[fix_01_sessiz_except] Exception")
            out.cursor_goto(0, 0)
            out.flush()
            # Drop prompt_toolkit's cached screen + cursor state so the
            # next _redraw() starts from a known (0, 0) origin and
            # re-renders every cell rather than diffing against stale.
            renderer.reset(leave_alternate_screen=False)
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")


    def _recover_after_resize(self, app, original_on_resize) -> None:
        """Recover a resized classic CLI without desynchronizing cursor state.

        Unlike _force_full_redraw, we do NOT clear the physical screen or
        scrollback here.  The startup banner and tool summary are printed
        before prompt_toolkit owns the live chrome, so they live in normal
        terminal scrollback.  Erasing the screen on SIGWINCH removes that
        startup UI and ``_replay_output_history`` cannot reconstruct it
        (the banner was never added to ``_OUTPUT_HISTORY``).

        Instead we just reset prompt_toolkit's renderer cache so the next
        incremental redraw starts from a clean slate, then let
        ``original_on_resize`` recalculate layout for the new size.

        We also flag ``_status_bar_suppressed_after_resize`` so the dynamic
        status bar and input separator rules stay hidden until the next user
        input.  On column shrink the terminal reflows already-rendered status
        bar rows into scrollback before prompt_toolkit can erase them; drawing
        a fresh full-width bar immediately makes the old and new versions
        look duplicated (#19280, #22976).  Clearing the suppression on the
        next prompt restores the bar cleanly.
        """
        self._status_bar_suppressed_after_resize = True
        try:
            app.renderer.reset(leave_alternate_screen=False)
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")
        try:
            app.invalidate()
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")
        original_on_resize()


    @staticmethod
    def _compression_count_style(count: int) -> str:
        """Return a style class reflecting context compression pressure."""
        if count >= 10:
            return "class:status-bar-bad"
        if count >= 5:
            return "class:status-bar-warn"
        return "class:status-bar-dim"


    @classmethod
    def _trim_status_bar_text(cls, text: str, max_width: int) -> str:
        """Trim status-bar text to a single terminal row."""
        if max_width <= 0:
            return ""
        try:
            from prompt_toolkit.utils import get_cwidth
        except Exception:
            get_cwidth = None

        if cls._status_bar_display_width(text) <= max_width:
            return text

        ellipsis = "..."
        ellipsis_width = cls._status_bar_display_width(ellipsis)
        if max_width <= ellipsis_width:
            return ellipsis[:max_width]

        out = []
        width = 0
        for ch in text:
            ch_width = get_cwidth(ch) if get_cwidth else len(ch)
            if width + ch_width + ellipsis_width > max_width:
                break
            out.append(ch)
            width += ch_width
        return "".join(out).rstrip() + ellipsis


    @staticmethod
    def _get_tui_terminal_width(default: tuple[int, int] = (80, 24)) -> int:
        """Return the live prompt_toolkit width, falling back to ``shutil``.

        The TUI layout can be narrower than ``shutil.get_terminal_size()`` reports,
        especially on Termux/mobile shells, so prefer prompt_toolkit's width whenever
        an app is active.
        """
        try:
            from prompt_toolkit.application import get_app
            return get_app().output.get_size().columns
        except Exception:
            return shutil.get_terminal_size(default).columns


    def _use_minimal_tui_chrome(self, width: Optional[int] = None) -> bool:
        """Hide low-value chrome on narrow/mobile terminals to preserve rows."""
        if width is None:
            width = self._get_tui_terminal_width()
        return width < 64


    def set_voice_record_key_cache(self, raw_key: object) -> None:
        """Populate the voice label cache from a raw ``voice.record_key``.

        Called at CLI startup after the prompt_toolkit binding is
        registered so the cached label always matches the live binding.
        """
        try:
            from reymen.reymen_cli.voice import format_voice_record_key_for_status
            self._voice_record_key_display_cache = format_voice_record_key_for_status(raw_key)
        except Exception:
            self._voice_record_key_display_cache = "Ctrl+B"


    def _build_status_bar_text(self, width: Optional[int] = None) -> str:
        """Return a compact one-line session status string for the TUI footer."""
        try:
            snapshot = self._get_status_bar_snapshot()
            if width is None:
                width = self._get_tui_terminal_width()
            percent = snapshot["context_percent"]
            percent_label = f"{percent}%" if percent is not None else "--"
            duration_label = snapshot["duration"]

            yolo_active = self._is_session_yolo_active()
            if width < 52:
                text = f"⚕ {snapshot['model_short']} · {duration_label}"
                if yolo_active:
                    text += " · ⚠ YOLO"
                return self._trim_status_bar_text(text, width)
            if width < 76:
                parts = [f"⚕ {snapshot['model_short']}", percent_label]
                compressions = snapshot.get("compressions", 0)
                if compressions:
                    parts.append(f"🗜️ {compressions}")
                bg_count = snapshot.get("active_background_tasks", 0)
                if bg_count:
                    parts.append(f"▶ {bg_count}")
                bg_proc_count = snapshot.get("active_background_processes", 0)
                if bg_proc_count:
                    parts.append(f"⚙ {bg_proc_count}")
                parts.append(duration_label)
                if yolo_active:
                    parts.append("⚠ YOLO")
                return self._trim_status_bar_text(" · ".join(parts), width)

            if snapshot["context_length"]:
                ctx_total = _format_context_length(snapshot["context_length"])
                ctx_used = format_token_count_compact(snapshot["context_tokens"])
                context_label = f"{ctx_used}/{ctx_total}"
            else:
                context_label = "ctx --"

            compressions = snapshot.get("compressions", 0)
            parts = [f"⚕ {snapshot['model_short']}", context_label, percent_label]
            if compressions:
                parts.append(f"🗜️ {compressions}")
            bg_count = snapshot.get("active_background_tasks", 0)
            if bg_count:
                parts.append(f"▶ {bg_count}")
            bg_proc_count = snapshot.get("active_background_processes", 0)
            if bg_proc_count:
                parts.append(f"⚙ {bg_proc_count}")
            parts.append(duration_label)
            prompt_elapsed = snapshot.get("prompt_elapsed")
            if prompt_elapsed:
                parts.append(prompt_elapsed)
            if yolo_active:
                parts.append("⚠ YOLO")
            return self._trim_status_bar_text(" │ ".join(parts), width)
        except Exception:
            return f"⚕ {self.model if getattr(self, 'model', None) else 'ReYMeN'}"


    def _format_submitted_user_message_preview(self, user_input: str) -> str:
        """Format the submitted user-message scrollback preview."""
        ts_suffix = (
            f" [dim]{datetime.now().strftime('%H:%M')}[/]"
            if getattr(self, "show_timestamps", False) else ""
        )
        lines = user_input.split("\n")
        if len(lines) <= 1:
            return f"[bold {_accent_hex()}]●[/] [bold]{_escape(user_input)}[/]{ts_suffix}"

        first_lines = int(getattr(self, "user_message_preview_first_lines", 2))
        last_lines = int(getattr(self, "user_message_preview_last_lines", 2))
        first_lines = max(1, first_lines)
        last_lines = max(0, last_lines)
        head = lines[:first_lines]
        remaining_after_head = max(0, len(lines) - len(head))
        tail_count = min(last_lines, remaining_after_head)
        tail = lines[-tail_count:] if tail_count else []

        hidden_middle_count = len(lines) - len(head) - len(tail)
        if hidden_middle_count < 0:
            hidden_middle_count = 0
            tail = []

        preview_lines = [
            f"[bold {_accent_hex()}]●[/] [bold]{_escape(head[0])}[/]{ts_suffix}"
        ]
        preview_lines.extend(f"[bold]{_escape(line)}[/]" for line in head[1:])

        if hidden_middle_count > 0:
            noun = "line" if hidden_middle_count == 1 else "lines"
            preview_lines.append(f"[dim]... (+{hidden_middle_count} more {noun})[/]")

        preview_lines.extend(f"[bold]{_escape(line)}[/]" for line in tail)
        return "\n".join(preview_lines)


    def _stream_reasoning_delta(self, text: str) -> None:
        """Stream reasoning/thinking tokens into a dim box above the response.

        Opens a dim reasoning box on first token, streams line-by-line.
        The box is closed automatically when content tokens start arriving
        (via _stream_delta → _emit_stream_text).

        Once the response box is open, suppress any further reasoning
        rendering — a late thinking block (e.g. after an interrupt) would
        otherwise draw a reasoning box inside the response box.
        """
        if not text:
            return
        self._reasoning_shown_this_turn = True
        if getattr(self, "_stream_box_opened", False):
            return

        # Open reasoning box on first reasoning token
        if not getattr(self, "_reasoning_box_opened", False):
            self._reasoning_box_opened = True
            w = self._scrollback_box_width()
            r_label = " Reasoning "
            r_fill = w - 2 - len(r_label)
            _cprint(f"\n{_DIM}┌─{r_label}{'─' * max(r_fill - 1, 0)}┐{_RST}")

        self._reasoning_buf = getattr(self, "_reasoning_buf", "") + text

        # Emit complete lines, and force-flush long partial lines so
        # reasoning is visible in real-time even without newlines.
        while "\n" in self._reasoning_buf:
            line, self._reasoning_buf = self._reasoning_buf.split("\n", 1)
            _cprint(f"{_DIM}{line}{_RST}")
        if len(self._reasoning_buf) > 80:
            _cprint(f"{_DIM}{self._reasoning_buf}{_RST}")
            self._reasoning_buf = ""


    def _stream_delta(self, text) -> None:
        """Line-buffered streaming callback for real-time token rendering.

        Receives text deltas from the agent as tokens arrive. Buffers
        partial lines and emits complete lines via _cprint to work
        reliably with prompt_toolkit's patch_stdout.

        Reasoning/thinking blocks (<REASONING_SCRATCHPAD>, <think>, etc.)
        are suppressed during streaming since they'd display raw XML tags.
        The agent strips them from the final response anyway.

        A ``None`` value signals an intermediate turn boundary (tools are
        about to execute).  Flushes any open boxes and resets state so
        tool feed lines render cleanly between turns.
        """
        if text is None:
            self._flush_stream()
            self._reset_stream_state()
            return
        if not text:
            return

        self._stream_started = True

        # ── Tag-based reasoning suppression ──
        # Track whether we're inside a reasoning/thinking block.
        # These tags are model-generated (system prompt tells the model
        # to use them) and get stripped from final_response. We must
        # suppress them during streaming too — unless show_reasoning is
        # enabled, in which case we route the inner content to the
        # reasoning display box instead of discarding it.
        _OPEN_TAGS = ("<REASONING_SCRATCHPAD>", "<think>", "<reasoning>", "<THINKING>", "<thinking>", "<thought>")
        _CLOSE_TAGS = ("</REASONING_SCRATCHPAD>", "</think>", "</reasoning>", "</THINKING>", "</thinking>", "</thought>")

        # Append to a pre-filter buffer first
        self._stream_prefilt = getattr(self, "_stream_prefilt", "") + text

        # Check if we're entering a reasoning block.
        # Only match tags that appear at a "block boundary": start of the
        # stream, after a newline (with optional whitespace), or when nothing
        # but whitespace has been emitted on the current line.
        # This prevents false positives when models *mention* tags in prose
        # like "(/think not producing <think> tags)".
        #
        # _stream_last_was_newline tracks whether the last character emitted
        # (or the start of the stream) is a line boundary.  It's True at
        # stream start and set True whenever emitted text ends with '\n'.
        if not hasattr(self, "_stream_last_was_newline"):
            self._stream_last_was_newline = True  # start of stream = boundary

        if not getattr(self, "_in_reasoning_block", False):
            for tag in _OPEN_TAGS:
                search_start = 0
                while True:
                    idx = self._stream_prefilt.find(tag, search_start)
                    if idx == -1:
                        break
                    # Check if this is a block boundary position
                    preceding = self._stream_prefilt[:idx]
                    if idx == 0:
                        # At buffer start — only a boundary if we're at
                        # a line start (stream start or last emit ended
                        # with newline)
                        is_block_boundary = getattr(self, "_stream_last_was_newline", True)
                    else:
                        # Find last newline in the buffer before the tag
                        last_nl = preceding.rfind("\n")
                        if last_nl == -1:
                            # No newline in buffer — boundary only if
                            # last emit was a newline AND only whitespace
                            # has accumulated before the tag
                            is_block_boundary = (
                                getattr(self, "_stream_last_was_newline", True)
                                and preceding.strip() == ""
                            )
                        else:
                            # Text between last newline and tag must be
                            # whitespace-only
                            is_block_boundary = preceding[last_nl + 1:].strip() == ""
                    if is_block_boundary:
                        # Emit everything before the tag
                        if preceding:
                            self._emit_stream_text(preceding)
                            self._stream_last_was_newline = preceding.endswith("\n")
                        self._in_reasoning_block = True
                        self._stream_prefilt = self._stream_prefilt[idx + len(tag):]
                        break
                    # Not a block boundary — keep searching after this occurrence
                    search_start = idx + 1
                if getattr(self, "_in_reasoning_block", False):
                    break

            # Could also be a partial open tag at the end — hold it back
            if not getattr(self, "_in_reasoning_block", False):
                # Check for partial tag match at the end
                safe = self._stream_prefilt
                for tag in _OPEN_TAGS:
                    for i in range(1, len(tag)):
                        if self._stream_prefilt.endswith(tag[:i]):
                            safe = self._stream_prefilt[:-i]
                            break
                if safe:
                    self._emit_stream_text(safe)
                    self._stream_last_was_newline = safe.endswith("\n")
                    self._stream_prefilt = self._stream_prefilt[len(safe):]
                return

        # Inside a reasoning block — look for close tag.
        # Keep accumulating _stream_prefilt because close tags can arrive
        # split across multiple tokens (e.g. "</REASONING_SCRATCH" + "PAD>...").
        if getattr(self, "_in_reasoning_block", False):
            for tag in _CLOSE_TAGS:
                idx = self._stream_prefilt.find(tag)
                if idx != -1:
                    self._in_reasoning_block = False
                    # When show_reasoning is on, route inner content to
                    # the reasoning display box instead of discarding.
                    if self.show_reasoning:
                        inner = self._stream_prefilt[:idx]
                        if inner:
                            self._stream_reasoning_delta(inner)
                    after = self._stream_prefilt[idx + len(tag):]
                    self._stream_prefilt = ""
                    # Process remaining text after close tag through full
                    # filtering (it could contain another open tag)
                    if after:
                        self._stream_delta(after)
                    return
            # When show_reasoning is on, stream reasoning content live
            # instead of silently accumulating. Keep only the tail that
            # could be a partial close tag prefix.
            max_tag_len = max(len(t) for t in _CLOSE_TAGS)
            if len(self._stream_prefilt) > max_tag_len:
                if self.show_reasoning:
                    # Route the safe prefix to reasoning display
                    safe_reasoning = self._stream_prefilt[:-max_tag_len]
                    self._stream_reasoning_delta(safe_reasoning)
                self._stream_prefilt = self._stream_prefilt[-max_tag_len:]
            return


    def _emit_stream_text(self, text: str) -> None:
        """Emit filtered text to the streaming display."""
        if not text:
            return

        # When show_reasoning is on and reasoning is still rendering,
        # defer content until the reasoning box closes.  This ensures the
        # reasoning block always appears BEFORE the response in the terminal.
        if self.show_reasoning and getattr(self, "_reasoning_box_opened", False):
            self._deferred_content = getattr(self, "_deferred_content", "") + text
            return

        # Close the live reasoning box before opening the response box
        self._close_reasoning_box()

        # Open the response box header on the very first visible text
        if not self._stream_box_opened:
            # Strip leading whitespace/newlines before first visible content
            text = text.lstrip("\n")
            if not text:
                return
            self._stream_box_opened = True
            try:
                from reymen.reymen_cli.skin_engine import get_active_skin
                _skin = get_active_skin()
                label = _skin.get_branding("response_label", "⚕ ReYMeN")
                _text_hex = _skin.get_color("banner_text", "#FFF8DC")
            except Exception:
                label = "⚕ ReYMeN"
                _text_hex = "#FFF8DC"
            # Build a true-color ANSI escape for the response text color
            # so streamed content matches the Rich Panel appearance.
            try:
                _r = int(_text_hex[1:3], 16)
                _g = int(_text_hex[3:5], 16)
                _b = int(_text_hex[5:7], 16)
                self._stream_text_ansi = f"\033[38;2;{_r};{_g};{_b}m"
            except (ValueError, IndexError):
                self._stream_text_ansi = ""
            if self.show_timestamps:
                label = f"{label} {datetime.now().strftime('%H:%M')}"
            w = self._scrollback_box_width()
            fill = w - 2 - ReYMeNCLI._status_bar_display_width(label)
            _cprint(f"\n{_ACCENT}╭─{label}{'─' * max(fill - 1, 0)}╮{_RST}")

        self._stream_buf += text

        # Emit complete lines, keep partial remainder in buffer
        _tc = getattr(self, "_stream_text_ansi", "")

        def _emit_one(printed_line: str) -> None:
            _cprint(f"{_STREAM_PAD}{_tc}{printed_line}{_RST}" if _tc else f"{_STREAM_PAD}{printed_line}")

        def _flush_table_buf() -> None:
            buf = self._stream_table_buf
            self._stream_table_buf = []
            self._in_stream_table = False
            if not buf:
                return
            # Strip cell-level markdown (`code`, **bold**, ~~strike~~) FIRST
            # so the realigner pads to the final visible cell width, not
            # the marker-decorated source width.  Otherwise a body row
            # like `` | Bold | `**bold**` | `` lands narrower than its
            # header column once the markers are removed.
            joined = "\n".join(buf)
            if self.final_response_markdown == "strip":
                joined = _strip_markdown_syntax(joined)
            block = realign_markdown_tables(joined, _terminal_width_for_streaming())
            for ln in block.split("\n"):
                _emit_one(ln)

        while "\n" in self._stream_buf:
            line, self._stream_buf = self._stream_buf.split("\n", 1)

            # Hold table-shaped lines in a side-buffer so we can re-pad
            # the whole block once it ends.  Streaming line-by-line, we
            # cannot re-align mid-table without reflowing already-printed
            # rows; the cost is that the user sees the table appear in a
            # single batch when the block closes instead of row-by-row.
            if self._in_stream_table:
                if looks_like_table_row(line) or is_table_divider(line):
                    self._stream_table_buf.append(line)
                    continue
                # Block ended — flush the realigned table, then fall
                # through to print the current (non-table) line.
                _flush_table_buf()
            elif looks_like_table_row(line):
                self._stream_table_buf.append(line)
                self._in_stream_table = True
                continue

            if self.final_response_markdown == "strip":
                line = _strip_markdown_syntax(line)
            _emit_one(line)


    def _slow_command_status(self, command: str) -> str:
        """Return a user-facing status message for slower slash commands."""
        cmd_lower = command.lower().strip()
        if cmd_lower.startswith("/skills search"):
            return "Searching skills..."
        if cmd_lower.startswith("/skills browse"):
            return "Loading skills..."
        if cmd_lower.startswith("/skills inspect"):
            return "Inspecting skill..."
        if cmd_lower.startswith("/skills install"):
            return "Installing skill..."
        if cmd_lower.startswith("/skills"):
            return "Processing skills command..."
        if cmd_lower == "/reload-mcp":
            return "Reloading MCP servers..."
        if cmd_lower == "/reload-skills" or cmd_lower == "/reload_skills":
            return "Reloading skills..."
        if cmd_lower.startswith("/browser"):
            return "Configuring browser..."
        return "Processing command..."


    def _command_spinner_frame(self) -> str:
        """Return the current spinner frame for slow slash commands."""
        frame_idx = int(time.monotonic() * 10) % len(_COMMAND_SPINNER_FRAMES)
        return _COMMAND_SPINNER_FRAMES[frame_idx]


    @contextmanager
    def _busy_command(self, status: str):
        """Expose a temporary busy state in the TUI while a slash command runs."""
        self._command_running = True
        self._command_status = status
        self._invalidate(min_interval=0.0)
        try:
            print(f"⏳ {status}")
            yield
        finally:
            self._command_running = False
            self._command_status = ""
            self._invalidate(min_interval=0.0)


    def _open_external_editor(self, buffer=None) -> bool:
        """Open the active input buffer in an external editor."""
        app = getattr(self, "_app", None)
        if not app:
            _cprint(f"{_DIM}External editor is only available inside the interactive CLI.{_RST}")
            return False
        if self._command_running:
            _cprint(f"{_DIM}Wait for the current command to finish before opening the editor.{_RST}")
            return False
        if self._sudo_state or self._secret_state or self._approval_state or getattr(self, "_slash_confirm_state", None) or self._clarify_state:
            _cprint(f"{_DIM}Finish the active prompt before opening the editor.{_RST}")
            return False
        target_buffer = buffer or getattr(app, "current_buffer", None)
        if target_buffer is None:
            _cprint(f"{_DIM}No active input buffer is available for the external editor.{_RST}")
            return False
        try:
            existing_text = getattr(target_buffer, "text", "")
            expanded_text = self._expand_paste_references(existing_text)
            if expanded_text != existing_text and hasattr(target_buffer, "text"):
                self._skip_paste_collapse = True
                target_buffer.text = expanded_text
                if hasattr(target_buffer, "cursor_position"):
                    target_buffer.cursor_position = len(expanded_text)
            # Set skip flag (again) so the text-change event fired when the
            # editor closes does not re-collapse the returned content.
            self._skip_paste_collapse = True
            target_buffer.open_in_editor(validate_and_handle=False)
            return True
        except Exception as exc:
            _cprint(f"{_DIM}Failed to open external editor: {exc}{_RST}")
            return False


    def _audio_level_bar(self) -> str:
        """Return a visual audio level indicator based on current RMS."""
        _LEVEL_BARS = " ▁▂▃▄▅▆▇"
        rec = getattr(self, "_voice_recorder", None)
        if rec is None:
            return ""
        rms = rec.current_rms
        # Normalize RMS (0-32767) to 0-7 index, with log-ish scaling
        # Typical speech RMS is 500-5000, we cap display at ~8000
        level = min(rms, 8000) * 7 // 8000
        return _LEVEL_BARS[level]


    def _get_extra_tui_widgets(self) -> list:
        """Return extra prompt_toolkit widgets to insert into the TUI layout.

        Wrapper CLIs can override this to inject widgets (e.g. a mini-player,
        overlay menu) into the layout without overriding ``run()``.  Widgets
        are inserted between the spacer and the status bar.
        """
        return []


    def run(self):
        """Run the interactive CLI loop with persistent input at bottom."""
        # Detect light/dark terminal mode now (before pt grabs the tty).
        # Caches the result so subsequent _hex_to_ansi / style calls
        # don't risk re-querying mid-render.
        try:
            _detect_light_mode()
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")
        # Push the entire TUI to the bottom of the terminal so the banner,
        # responses, and prompt all appear pinned to the bottom — empty
        # space stays above, not below.  This prints enough blank lines to
        # scroll the cursor to the last row before any content is rendered.
        try:
            _term_lines = shutil.get_terminal_size().lines
            if _term_lines > 2:
                print("\n" * (_term_lines - 1), end="", flush=True)
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")

        self.show_banner()
        # Surface any active supply-chain security advisories right after the
        # welcome banner. Quiet/single-query paths call this themselves.
        self._show_security_advisories()
        # If resuming a session, load history and display it immediately
        # so the user has context before typing their first message.
        if self._resumed:
            if self._preload_resumed_session():
                self._display_resumed_history()

        try:
            from reymen.reymen_cli.skin_engine import get_active_skin
            _welcome_skin = get_active_skin()
            _welcome_text = _welcome_skin.get_branding("welcome", "Welcome to ReYMeN Agent! Type your message or /help for commands.")
            _welcome_color = _welcome_skin.get_color("banner_text", "#FFF8DC")
        except Exception:
            _welcome_text = "Welcome to ReYMeN Agent! Type your message or /help for commands."
            _welcome_color = "#FFF8DC"
        self._console_print(f"[{_welcome_color}]{_welcome_text}[/]")

        # Redaction opt-out warning (#17691): ON by default, loud when off.
        # The redactor snapshots its state at import time so any toggle now
        # won't affect the running process — we just want the operator to
        # see that they're running without the safety net.
        try:
            _redact_raw = os.getenv("ReYMeN_REDACT_SECRETS", "true")
            if _redact_raw.lower() not in {"1", "true", "yes", "on"}:
                self._console_print(
                    "[bold red]⚠  Secret redaction is DISABLED[/] "
                    f"(ReYMeN_REDACT_SECRETS={_redact_raw}). "
                    "API keys and tokens may appear verbatim in chat output, "
                    "session JSONs, and logs. Set "
                    "[cyan]security.redact_secrets: true[/] in config.yaml "
                    "to re-enable."
                )
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")
        # First-time OpenClaw-residue banner — fires once if ~/.openclaw/ exists
        # after an OpenClaw→ReYMeN migration (especially migrations done by
        # OpenClaw's own tool, which doesn't archive the source directory).
        try:
            from agent.onboarding import (
                OPENCLAW_RESIDUE_FLAG,
                detect_openclaw_residue,
                is_seen,
                mark_seen,
                openclaw_residue_hint_cli,
            )
            if not is_seen(self.config, OPENCLAW_RESIDUE_FLAG) and detect_openclaw_residue():
                try:
                    _resid_color = _welcome_skin.get_color("banner_dim", "#B8860B")
                except Exception:
                    _resid_color = "#B8860B"
                self._console_print(f"[{_resid_color}]{openclaw_residue_hint_cli()}[/]")
                try:
                    from reymen.reymen_cli.config import get_config_path as _get_cfg_path_resid
                    mark_seen(_get_cfg_path_resid(), OPENCLAW_RESIDUE_FLAG)
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )  # best-effort — banner will fire again next session
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )  # banner is non-critical — never break startup
        # Show a random tip to help users discover features
        try:
            from reymen.reymen_cli.tips import get_random_tip
            _tip = get_random_tip()
            try:
                _tip_color = _welcome_skin.get_color("banner_dim", "#B8860B")
            except Exception:
                _tip_color = "#B8860B"
            self._console_print(f"[dim {_tip_color}]✦ Tip: {_tip}[/]")
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )  # Tips are non-critical — never break startup

        # Curator — kick off a background skill-maintenance pass on startup
        # if the schedule says we're due.  Runs in a daemon thread so it
        # never blocks the interactive loop.  Best-effort; any failure is
        # swallowed to avoid breaking session startup.
        try:
            from agent.curator import maybe_run_curator
            maybe_run_curator(
                idle_for_seconds=float("inf"),  # CLI startup = fully idle
                on_summary=lambda msg: self._console_print(
                    f"[dim #6b7684]💾 {msg}[/]"
                ),
            )
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")
        if self.preloaded_skills and not self._startup_skills_line_shown:
            skills_label = ", ".join(self.preloaded_skills)
            self._console_print(
                f"[bold {_accent_hex()}]Activated skills:[/] {skills_label}"
            )
            self._startup_skills_line_shown = True
        self._console_print()
        
        # State for async operation
        self._agent_running = False
        self._pending_input = queue.Queue()     # For normal input (commands + new queries)
        self._interrupt_queue = queue.Queue()   # For messages typed while agent is running
        # See constructor note. Mirrored here for the run() path that skips
        # the earlier __init__ branch.
        self._last_turn_interrupted = False
        self._should_exit = False
        self._last_ctrl_c_time = 0  # Track double Ctrl+C for force exit

        # Give plugin manager a CLI reference so plugins can inject messages
        from reymen.reymen_cli.plugins import get_plugin_manager
        get_plugin_manager()._cli_ref = self

        # Config file watcher — detect mcp_servers changes and auto-reload
        from reymen.reymen_cli.config import get_config_path as _get_config_path
        _cfg_path = _get_config_path()
        self._config_mtime: float = _cfg_path.stat().st_mtime if _cfg_path.exists() else 0.0
        self._config_mcp_servers: dict = self.config.get("mcp_servers") or {}
        self._last_config_check: float = 0.0  # monotonic time of last check

        # Clarify tool state: interactive question/answer with the user.
        # When the agent calls the clarify tool, _clarify_state is set and
        # the prompt_toolkit UI switches to a selection mode.
        self._clarify_state = None      # dict with question, choices, selected, response_queue
        self._clarify_freetext = False  # True when user chose "Other" and is typing
        self._clarify_deadline = 0      # monotonic timestamp when the clarify times out

        # Sudo password prompt state (similar mechanism to clarify)
        self._sudo_state = None         # dict with response_queue when active
        self._sudo_deadline = 0
        self._modal_input_snapshot = None

        # Dangerous command approval state (similar mechanism to clarify)
        self._approval_state = None     # dict with command, description, choices, selected, response_queue
        self._approval_deadline = 0
        self._approval_lock = threading.Lock()  # serialize concurrent approval prompts (delegation race fix)

        # Destructive slash-command confirmation state (/new, /clear, /undo).
        # These prompts are answered through the prompt_toolkit composer, not
        # raw input(), so the option labels stay visible and Enter does not EOF
        # the whole app.
        self._slash_confirm_state = None
        self._slash_confirm_deadline = 0

        # Slash command loading state
        self._command_running = False
        self._command_status = ""

        # Secure secret capture state for skill setup
        self._secret_state = None       # dict with var_name, prompt, metadata, response_queue
        self._secret_deadline = 0

        # Clipboard image attachments (paste images into the CLI)
        self._attached_images: list[Path] = []
        self._image_counter = 0

        # Voice mode state (protected by _voice_lock for cross-thread access)
        self._voice_lock = threading.Lock()
        self._voice_mode = False        # Whether voice mode is enabled
        self._voice_tts = False         # Whether TTS output is enabled
        self._voice_recorder = None     # AudioRecorder instance (lazy init)
        self._voice_recording = False   # Whether currently recording
        self._voice_processing = False  # Whether STT is in progress
        self._voice_continuous = False  # Whether to auto-restart after agent responds
        self._voice_tts_done = threading.Event()  # Signals TTS playback finished
        self._voice_tts_done.set()  # Initially "done" (no TTS pending)

        if os.environ.get("ReYMeN_DEFER_AGENT_STARTUP") != "1":
            self._install_tool_callbacks()

        if os.environ.get("ReYMeN_DEFER_AGENT_STARTUP") != "1":
            self._ensure_tirith_security()
        
        # Key bindings for the input area
        kb = KeyBindings()

        from prompt_toolkit.keys import Keys as _IgnoreKeys

        @kb.add(_IgnoreKeys.Ignore, eager=True)
        def handle_ignored_terminal_sequence(event):
            """Consume parser-level ignored terminal sequences before self-insert.

            install_ignored_terminal_sequences() in ReYMeN_cli.pt_input_extras
            registers focus reports (CSI I / CSI O) as Keys.Ignore at the
            VT100 parser level. Without this no-op binding the default
            self-insert path would still fire and the bytes would land in
            the buffer.
            """
            return None

        def handle_enter(event):
            """Handle Enter key - submit input.
            
            Routes to the correct queue based on active UI state:
            - Sudo password prompt: password goes to sudo response queue
            - Approval selection: selected choice goes to approval response queue
            - Clarify freetext mode: answer goes to the clarify response queue
            - Clarify choice mode: selected choice goes to the clarify response queue
            - Agent running: goes to _interrupt_queue (chat() monitors this)
            - Agent idle: goes to _pending_input (process_loop monitors this)
            Commands (starting with /) always go to _pending_input so they're
            handled as commands, not sent as interrupt text to the agent.
            """
            # --- Sudo password prompt: submit the typed password ---
            if self._sudo_state:
                text = event.app.current_buffer.text
                self._sudo_state["response_queue"].put(text)
                self._sudo_state = None
                event.app.invalidate()
                return

            # --- Secret prompt: submit the typed secret ---
            if self._secret_state:
                text = event.app.current_buffer.text
                self._submit_secret_response(text)
                event.app.current_buffer.reset()
                event.app.invalidate()
                return

            # --- Approval selection: confirm the highlighted choice ---
            if self._approval_state:
                self._handle_approval_selection()
                event.app.invalidate()
                return

            # --- Slash-command confirmation: submit typed or highlighted choice ---
            if self._slash_confirm_state:
                text = event.app.current_buffer.text.strip()
                choices = self._slash_confirm_state.get("choices") or []
                choice = self._normalize_slash_confirm_choice(text, choices) if text else None
                if choice is None:
                    selected = self._slash_confirm_state.get("selected", 0)
                    if 0 <= selected < len(choices):
                        choice = choices[selected][0]
                self._submit_slash_confirm_response(choice or "cancel")
                event.app.current_buffer.reset()
                event.app.invalidate()
                return

            # --- /model picker modal ---
            if self._model_picker_state:
                try:
                    self._handle_model_picker_selection()
                except Exception as _exc:
                    _cprint(f"  ✗ Model selection failed: {_exc}")
                    self._close_model_picker()
                event.app.current_buffer.reset()
                event.app.invalidate()
                return

            # --- Clarify freetext mode: user typed their own answer ---
            if self._clarify_freetext and self._clarify_state:
                text = event.app.current_buffer.text.strip()
                if text:
                    self._clarify_state["response_queue"].put(text)
                    self._clarify_state = None
                    self._clarify_freetext = False
                    event.app.current_buffer.reset()
                    event.app.invalidate()
                return

            # --- Clarify choice mode: confirm the highlighted selection ---
            if self._clarify_state and not self._clarify_freetext:
                state = self._clarify_state
                selected = state["selected"]
                choices = state.get("choices") or []
                if selected < len(choices):
                    state["response_queue"].put(choices[selected])
                    self._clarify_state = None
                    event.app.invalidate()
                else:
                    # "Other" selected → switch to freetext
                    self._clarify_freetext = True
                    event.app.invalidate()
                return

            # --- Normal input routing ---
            text = event.app.current_buffer.text.strip()
            has_images = bool(self._attached_images)
            if text or has_images:
                # Handle /model directly on the UI thread so interactive pickers
                # can safely use prompt_toolkit terminal handoff helpers.
                if self._should_handle_model_command_inline(text, has_images=has_images):
                    if not self.process_command(text):
                        self._should_exit = True
                        if event.app.is_running:
                            event.app.exit()
                    event.app.current_buffer.reset(append_to_history=True)
                    # Force a repaint: process_command() prints through
                    # patch_stdout (scrolls output above the prompt) and never
                    # invalidates the app, so the just-cleared input area can
                    # keep showing the submitted text until some unrelated
                    # redraw fires. Every other early-return branch in this
                    # handler invalidates after reset — match them.
                    event.app.invalidate()
                    return

                # Handle /steer while the agent is running immediately on the
                # UI thread.  Queuing through _pending_input would deadlock the
                # steer until after the agent loop finishes (process_loop is
                # blocked inside self.chat()), which turns /steer into a
                # post-run next-turn message — defeating mid-run injection.
                # agent.steer() is thread-safe (holds _pending_steer_lock).
                if self._should_handle_steer_command_inline(text, has_images=has_images):
                    self.process_command(text)
                    event.app.current_buffer.reset(append_to_history=True)
                    # Force a repaint after clearing the buffer.  /steer is
                    # dispatched mid-run while the agent streams output through
                    # patch_stdout; process_command() never invalidates the
                    # app, so without this the submitted "/steer <text>" can
                    # linger in the input area (looking unsent) and invite an
                    # accidental re-submit. See issue #34569.
                    event.app.invalidate()
                    return

                # Snapshot and clear attached images
                images = list(self._attached_images)
                self._attached_images.clear()
                event.app.invalidate()
                # Bundle text + images as a tuple when images are present
                payload = (text, images) if images else text
                if self._agent_running and not (text and _looks_like_slash_command(text)):
                    _effective_mode = self.busy_input_mode
                    if _effective_mode == "steer":
                        # Route Enter through /steer — inject mid-run after the
                        # next tool call.  Images can't ride along (steer only
                        # appends text), so fall back to queue when images are
                        # attached.  If the agent lacks steer() or rejects the
                        # payload, also fall back to queue so nothing is lost.
                        if images or not text:
                            _effective_mode = "queue"
                        else:
                            accepted = False
                            try:
                                if self.agent is not None and hasattr(self.agent, "steer"):
                                    accepted = bool(self.agent.steer(text))
                            except Exception as exc:
                                _cprint(f"  {_DIM}Steer failed ({exc}) — queued for next turn.{_RST}")
                                accepted = False
                            if accepted:
                                preview = text[:80] + ("..." if len(text) > 80 else "")
                                _cprint(f"  {_ACCENT}⏩ Steered: '{preview}'{_RST}")
                            else:
                                _effective_mode = "queue"
                    if _effective_mode == "queue":
                        # Queue for the next turn instead of interrupting
                        self._pending_input.put(payload)
                        preview = text if text else f"[{len(images)} image{'s' if len(images) != 1 else ''} attached]"
                        _cprint(f"  Queued for the next turn: {preview[:80]}{'...' if len(preview) > 80 else ''}")
                    elif _effective_mode == "interrupt":
                        self._interrupt_queue.put(payload)
                        # Debug: log to file when message enters interrupt queue
                        try:
                            _dbg = _ReYMeN_home / "interrupt_debug.log"
                            with open(_dbg, "a", encoding="utf-8") as _f:
                                _f.write(f"{time.strftime('%H:%M:%S')} ENTER: queued interrupt msg={str(payload)[:60]!r}, "
                                         f"agent_running={self._agent_running}\n")
                        except Exception:
                            logger.warning("[fix_01_sessiz_except] Exception")
                    # First-touch onboarding: on the very first busy-while-running
                    # event for this install, print a one-line tip explaining the
                    # /busy knob.  Flag persists to config.yaml and never fires
                    # again.  Guarded for exceptions so onboarding can't break
                    # the input loop.
                    try:
                        from agent.onboarding import (
                            BUSY_INPUT_FLAG,
                            busy_input_hint_cli,
                            is_seen,
                            mark_seen,
                        )
                        if not is_seen(CLI_CONFIG, BUSY_INPUT_FLAG):
                            _cprint(f"  {_DIM}{busy_input_hint_cli(self.busy_input_mode)}{_RST}")
                            mark_seen(_ReYMeN_home / "config.yaml", BUSY_INPUT_FLAG)
                            CLI_CONFIG.setdefault("onboarding", {}).setdefault("seen", {})[BUSY_INPUT_FLAG] = True
                    except Exception:
                        logger.warning("[fix_01_sessiz_except] Exception")
                else:
                    self._pending_input.put(payload)
                event.app.current_buffer.reset(append_to_history=True)

        _bind_prompt_submit_keys(kb, handle_enter)
        
        @kb.add('escape', 'enter')
        def handle_alt_enter(event):
            """Alt+Enter inserts a newline for multi-line input.

            Works on mac/Linux/WSL. On Windows Terminal this keystroke is
            intercepted at the terminal layer (toggles fullscreen) and never
            reaches here — Windows users get newline via Ctrl+Enter instead
            (bound below as c-j, since WT delivers Ctrl+Enter as LF).
            """
            event.current_buffer.insert_text('\n')

        if _preserve_ctrl_enter_newline():
            @kb.add('c-j')
            def handle_ctrl_enter_newline(event):
                """Ctrl+Enter inserts a newline on Windows, WSL, SSH, and WT.

                Windows Terminal (incl. WSL/SSH sessions through it) delivers
                Ctrl+Enter as LF (c-j), distinct from plain Enter (c-m). This
                binding makes Ctrl+Enter the equivalent of Alt+Enter on those
                terminals, giving an Enter-involving newline keystroke
                without requiring terminal settings changes. Ctrl+J (the raw
                LF keystroke) also triggers this by virtue of being the same
                key code — a harmless side effect since Ctrl+J has no
                conflicting ReYMeN binding. See issue #22379.
                """
                event.current_buffer.insert_text('\n')

        # VSCode/Cursor bind Ctrl+G to "Find Next" at the editor level, so
        # the keystroke never reaches the embedded terminal. Alt+G is unbound
        # in those IDEs and arrives here as ('escape', 'g') — register it as
        # a fallback so the editor handoff works inside Cursor/VSCode too.
        _editor_filter = Condition(
            lambda: not self._clarify_state and not self._approval_state and not self._sudo_state and not self._secret_state
        )

        @kb.add('c-g', filter=_editor_filter)
        @kb.add('escape', 'g', filter=_editor_filter)
        def handle_open_in_editor(event):
            """Ctrl+G (or Alt+G in VSCode/Cursor) opens the current draft in an external editor."""
            cli_ref._open_external_editor(event.current_buffer)

        @kb.add('tab', eager=True)
        def handle_tab(event):
            """Tab: accept completion, auto-suggestion, or start completions.

            Priority:
            1. Completion menu open → accept selected completion
            2. Ghost text suggestion available → accept auto-suggestion
            3. Otherwise → start completion menu

            After accepting a provider like 'anthropic:', the completion menu
            closes and complete_while_typing doesn't fire (no keystroke).
            This binding re-triggers completions so stage-2 models appear
            immediately.
            """
            buf = event.current_buffer
            if buf.complete_state:
                # Completion menu is open — accept the selection
                completion = buf.complete_state.current_completion
                if completion is None:
                    # Menu open but nothing selected — select first then grab it
                    buf.go_to_completion(0)
                    completion = buf.complete_state and buf.complete_state.current_completion
                if completion is None:
                    return
                # Accept the selected completion
                buf.apply_completion(completion)
            elif buf.suggestion and buf.suggestion.text:
                # No completion menu, but there's a ghost text auto-suggestion — accept it
                buf.insert_text(buf.suggestion.text)
            else:
                # No menu and no suggestion — start completions from scratch
                buf.start_completion()

        # --- Clarify tool: arrow-key navigation for multiple-choice questions ---

        @kb.add('up', filter=Condition(lambda: bool(self._clarify_state) and not self._clarify_freetext))
        def clarify_up(event):
            """Move selection up in clarify choices."""
            if self._clarify_state:
                self._clarify_state["selected"] = max(0, self._clarify_state["selected"] - 1)
                event.app.invalidate()

        @kb.add('down', filter=Condition(lambda: bool(self._clarify_state) and not self._clarify_freetext))
        def clarify_down(event):
            """Move selection down in clarify choices."""
            if self._clarify_state:
                choices = self._clarify_state.get("choices") or []
                max_idx = len(choices)  # last index is the "Other" option
                self._clarify_state["selected"] = min(max_idx, self._clarify_state["selected"] + 1)
                event.app.invalidate()

        # Number keys for quick clarify selection (1-9, 0 for 10th item)
        def _make_clarify_number_handler(idx):
            def handler(event):
                if self._clarify_state and not self._clarify_freetext:
                    choices = self._clarify_state.get("choices") or []
                    # Map index to choice (treating "Other" as the last option)
                    if idx < len(choices):
                        # Select a numbered choice
                        self._clarify_state["response_queue"].put(choices[idx])
                        self._clarify_state = None
                        self._clarify_freetext = False
                        event.app.invalidate()
                    elif idx == len(choices):
                        # Select "Other" option
                        self._clarify_freetext = True
                        event.app.invalidate()
            return handler

        for _num in range(10):
            # 1-9 select items 0-8, 0 selects item 9 (10thitem)
            _idx = 9 if _num == 0 else _num - 1
            kb.add(str(_num), filter=Condition(lambda: bool(self._clarify_state) and not self._clarify_freetext))(_make_clarify_number_handler(_idx))

        # --- Dangerous command approval: arrow-key navigation ---

        @kb.add('up', filter=Condition(lambda: bool(self._approval_state)))
        def approval_up(event):
            if self._approval_state:
                self._approval_state["selected"] = max(0, self._approval_state["selected"] - 1)
                event.app.invalidate()

        @kb.add('down', filter=Condition(lambda: bool(self._approval_state)))
        def approval_down(event):
            if self._approval_state:
                max_idx = len(self._approval_state["choices"]) - 1
                self._approval_state["selected"] = min(max_idx, self._approval_state["selected"] + 1)
                event.app.invalidate()

        # --- Slash-command confirmation: arrow-key navigation ---
        @kb.add('up', filter=Condition(lambda: bool(self._slash_confirm_state)))
        def slash_confirm_up(event):
            if self._slash_confirm_state:
                self._slash_confirm_state["selected"] = max(0, self._slash_confirm_state.get("selected", 0) - 1)
                event.app.invalidate()

        @kb.add('down', filter=Condition(lambda: bool(self._slash_confirm_state)))
        def slash_confirm_down(event):
            if self._slash_confirm_state:
                max_idx = len(self._slash_confirm_state.get("choices") or []) - 1
                self._slash_confirm_state["selected"] = min(max_idx, self._slash_confirm_state.get("selected", 0) + 1)
                event.app.invalidate()

        # --- /model picker: arrow-key navigation ---
        @kb.add('up', filter=Condition(lambda: bool(self._model_picker_state)))
        def model_picker_up(event):
            if self._model_picker_state:
                self._model_picker_state["selected"] = max(0, self._model_picker_state.get("selected", 0) - 1)
                event.app.invalidate()

        @kb.add('down', filter=Condition(lambda: bool(self._model_picker_state)))
        def model_picker_down(event):
            state = self._model_picker_state
            if not state:
                return
            if state.get("stage") == "provider":
                max_idx = len(state.get("providers") or [])
            else:
                max_idx = len(state.get("model_list") or []) + 1
            state["selected"] = min(max_idx, state.get("selected", 0) + 1)
            event.app.invalidate()

        @kb.add('escape', filter=Condition(lambda: bool(self._model_picker_state)), eager=True)
        def model_picker_escape(event):
            """ESC closes the /model picker."""
            self._close_model_picker()
            event.app.current_buffer.reset()
            event.app.invalidate()

        # Number keys for quick approval selection (1-9, 0 for 10th item)
        def _make_approval_number_handler(idx):
            def handler(event):
                if self._approval_state and idx < len(self._approval_state["choices"]):
                    self._approval_state["selected"] = idx
                    self._handle_approval_selection()
                    event.app.invalidate()
            return handler

        for _num in range(10):
            # 1-9 select items 0-8, 0 selects item 9 (10th item)
            _idx = 9 if _num == 0 else _num - 1
            kb.add(str(_num), filter=Condition(lambda: bool(self._approval_state)))(_make_approval_number_handler(_idx))

        # Number keys for quick slash-confirm selection (1-9, 0 for 10th item)
        def _make_slash_confirm_number_handler(idx):
            def handler(event):
                if self._slash_confirm_state and idx < len(self._slash_confirm_state.get("choices") or []):
                    choice = self._slash_confirm_state["choices"][idx][0]
                    self._submit_slash_confirm_response(choice)
                    event.app.current_buffer.reset()
                    event.app.invalidate()
            return handler

        for _num in range(10):
            _idx = 9 if _num == 0 else _num - 1
            kb.add(str(_num), filter=Condition(lambda: bool(self._slash_confirm_state)))(_make_slash_confirm_number_handler(_idx))

        # --- History navigation: up/down browse history in normal input mode ---
        # The TextArea is multiline, so by default up/down only move the cursor.
        # Buffer.auto_up/auto_down handle both: cursor movement when multi-line,
        # history browsing when on the first/last line (or single-line input).
        _normal_input = Condition(
            lambda: not self._clarify_state and not self._approval_state and not self._slash_confirm_state and not self._sudo_state and not self._secret_state and not self._model_picker_state
        )

        @kb.add('up', filter=_normal_input)
        def history_up(event):
            """Up arrow: browse history when on first line, else move cursor up."""
            event.app.current_buffer.auto_up(count=event.arg)

        @kb.add('down', filter=_normal_input)
        def history_down(event):
            """Down arrow: browse history when on last line, else move cursor down."""
            event.app.current_buffer.auto_down(count=event.arg)

        @kb.add('c-l')
        def handle_ctrl_l(event):
            """Ctrl+L: force a clean full-screen repaint.

            Recovers the UI after external terminal buffer drift — tmux /
            cmux tab switches, ``clear`` from a subshell, SSH window
            restores, etc. — that prompt_toolkit can't detect on its own.
            Matches the universal bash/zsh/fish/vim/htop convention.
            """
            self._force_full_redraw()

        @kb.add('c-c')
        def handle_ctrl_c(event):
            """Handle Ctrl+C - cancel interactive prompts, interrupt agent, or exit.
            
            Priority:
            0. Cancel active voice recording
            1. Cancel active sudo/approval/clarify prompt
            2. Interrupt the running agent (first press)
            3. Force exit (second press within 2s, or when idle)
            """
            now = time.time()

            # Cancel active voice recording.
            # Run cancel() in a background thread to prevent blocking the
            # event loop if AudioRecorder._lock or CoreAudio takes time.
            _should_cancel_voice = False
            _recorder_ref = None
            with cli_ref._voice_lock:
                if cli_ref._voice_recording and cli_ref._voice_recorder:
                    _recorder_ref = cli_ref._voice_recorder
                    cli_ref._voice_recording = False
                    cli_ref._voice_continuous = False
                    _should_cancel_voice = True
            if _should_cancel_voice:
                _cprint(f"\n{_DIM}Recording cancelled.{_RST}")
                threading.Thread(
                    target=_recorder_ref.cancel, daemon=True
                ).start()
                event.app.invalidate()
                return

            # Cancel sudo prompt
            if self._sudo_state:
                self._sudo_state["response_queue"].put("")
                self._sudo_state = None
                event.app.invalidate()
                return

            # Cancel secret prompt
            if self._secret_state:
                self._cancel_secret_capture()
                event.app.current_buffer.reset()
                event.app.invalidate()
                return

            # Cancel approval prompt (deny)
            if self._approval_state:
                self._approval_state["response_queue"].put("deny")
                self._approval_state = None
                event.app.invalidate()
                return

            # Cancel slash confirmation prompt
            if self._slash_confirm_state:
                self._submit_slash_confirm_response("cancel")
                event.app.current_buffer.reset()
                event.app.invalidate()
                return

            # Cancel /model picker
            if self._model_picker_state:
                self._close_model_picker()
                event.app.current_buffer.reset()
                event.app.invalidate()
                return

            # Cancel clarify prompt
            if self._clarify_state:
                self._clarify_state["response_queue"].put(
                    "The user cancelled. Use your best judgement to proceed."
                )
                self._clarify_state = None
                self._clarify_freetext = False
                event.app.current_buffer.reset()
                event.app.invalidate()
                return

            if self._agent_running and self.agent:
                if now - self._last_ctrl_c_time < 2.0:
                    print("\n⚡ Force exiting...")
                    self._should_exit = True
                    event.app.exit()
                    return
                
                self._last_ctrl_c_time = now
                print("\n⚡ Interrupting agent... (press Ctrl+C again to force exit)")
                self.agent.interrupt()
            # If there's text or images, clear them (like bash).
            # If everything is already empty, exit.
            elif event.app.current_buffer.text or self._attached_images:
                event.app.current_buffer.reset()
                self._attached_images.clear()
                event.app.invalidate()
            else:
                self._should_exit = True
                event.app.exit()

        # Ctrl+Shift+C: no binding needed. Terminal emulators (GNOME Terminal,
        # iTerm2, kitty, Windows Terminal, etc.) intercept Ctrl+Shift+C before
        # the keystroke reaches the application's stdin — prompt_toolkit never
        # sees it, and prompt_toolkit's key spec parser doesn't even recognise
        # 'c-S-c' anyway (the Shift modifier is meaningless on control-sequence
        # keys). #19884 added a handler for this; #19895 patched the resulting
        # startup crash with try/except. Both were based on a misreading of how
        # terminal key events propagate. Deleting the dead handler outright.

        @kb.add('c-q')  # Ctrl+Q
        def handle_ctrl_q(event):
            """Alternative interrupt/exit shortcut (Ctrl+Q).

            Behaves like Ctrl+C: cancels active prompts, interrupts the
            running agent, or clears the input buffer. Does not support
            the double-press 'force exit' feature of Ctrl+C.
            """
            # Cancel active voice recording.
            _should_cancel_voice = False
            _recorder_ref = None
            with cli_ref._voice_lock:
                if cli_ref._voice_recording and cli_ref._voice_recorder:
                    _recorder_ref = cli_ref._voice_recorder
                    cli_ref._voice_recording = False
                    cli_ref._voice_continuous = False
                    _should_cancel_voice = True
            if _should_cancel_voice:
                _cprint(f"\n{_DIM}Recording cancelled.{_RST}")
                threading.Thread(
                    target=_recorder_ref.cancel, daemon=True
                ).start()
                event.app.invalidate()
                return

            # Cancel sudo prompt
            if self._sudo_state:
                self._sudo_state["response_queue"].put("")
                self._sudo_state = None
                event.app.invalidate()
                return

            # Cancel secret prompt
            if self._secret_state:
                self._cancel_secret_capture()
                event.app.current_buffer.reset()
                event.app.invalidate()
                return

            # Cancel approval prompt (deny)
            if self._approval_state:
                self._approval_state["response_queue"].put("deny")
                self._approval_state = None
                event.app.invalidate()
                return

            # Cancel slash confirmation prompt
            if self._slash_confirm_state:
                self._submit_slash_confirm_response("cancel")
                event.app.current_buffer.reset()
                event.app.invalidate()
                return

            # Cancel /model picker
            if self._model_picker_state:
                self._close_model_picker()
                event.app.current_buffer.reset()
                event.app.invalidate()
                return

            # Cancel clarify prompt
            if self._clarify_state:
                self._clarify_state["response_queue"].put(
                    "The user cancelled. Use your best judgement to proceed."
                )
                self._clarify_state = None
                self._clarify_freetext = False
                event.app.current_buffer.reset()
                event.app.invalidate()
                return

            if self._agent_running and self.agent:
                print("\n⚡ Interrupting agent...")
                self.agent.interrupt()
            elif event.app.current_buffer.text or self._attached_images:
                event.app.current_buffer.reset()
                self._attached_images.clear()
                event.app.invalidate()
            else:
                self._should_exit = True
                event.app.exit()

        @kb.add('c-d')
        def handle_ctrl_d(event):
            """Ctrl+D: delete char under cursor (standard readline behaviour).
            Only exit when the input is empty — same as bash/zsh. Pending
            attached images count as input and block the EOF-exit so the
            user doesn't lose them silently.
            """
            buf = event.app.current_buffer
            if buf.text:
                buf.delete()
            elif self._attached_images:
                # Empty text but pending attachments — no-op, don't exit.
                return
            else:
                self._should_exit = True
                event.app.exit()

        _modal_prompt_active = Condition(
            lambda: bool(self._secret_state or self._sudo_state or self._slash_confirm_state)
        )

        @kb.add('escape', filter=_modal_prompt_active, eager=True)
        def handle_escape_modal(event):
            """ESC cancels active secret/sudo prompts."""
            if self._secret_state:
                self._cancel_secret_capture()
                event.app.current_buffer.reset()
                event.app.invalidate()
                return
            if self._sudo_state:
                self._sudo_state["response_queue"].put("")
                self._sudo_state = None
                event.app.invalidate()
                return
            if self._slash_confirm_state:
                self._submit_slash_confirm_response("cancel")
                event.app.current_buffer.reset()
                event.app.invalidate()
                return

        @kb.add('c-z')
        def handle_ctrl_z(event):
            """Handle Ctrl+Z - suspend process to background (Unix only)."""
            if sys.platform == 'win32':
                _cprint(f"\n{_DIM}Suspend (Ctrl+Z) is not supported on Windows.{_RST}")
                event.app.invalidate()
                return
            import signal as _sig
            from prompt_toolkit.application import run_in_terminal
            from reymen.reymen_cli.skin_engine import get_active_skin
            agent_name = get_active_skin().get_branding("agent_name", "ReYMeN Agent")
            msg = f"\n{agent_name} has been suspended. Run `fg` to bring {agent_name} back."
            def _suspend():
                os.write(1, msg.encode())
                os.kill(0, _sig.SIGTSTP)
            run_in_terminal(_suspend)

        # Voice push-to-talk key: configurable via config.yaml (voice.record_key)
        # Default: Ctrl+B (avoids conflict with Ctrl+R readline reverse-search).
        # Config spellings (ctrl/control/alt/option/opt) are normalized to
        # prompt_toolkit's c-x / a-x format via ``normalize_voice_record_key_for_prompt_toolkit``
        # so the same config value binds identically in the TUI and CLI
        # (Copilot round-9 review on #19835). ``super``/``win``/``windows``
        # configs silently fall back to the default here since prompt_toolkit
        # has no super modifier — log a warning so users notice the
        # TUI/CLI split instead of a silent mismatch (round-11).
        _raw_key: object = "ctrl+b"
        try:
            from reymen.reymen_cli.config import load_config
            from reymen.reymen_cli.voice import (
                normalize_voice_record_key_for_prompt_toolkit,
                voice_record_key_from_config,
            )
            _raw_key = voice_record_key_from_config(load_config())
            _voice_key = normalize_voice_record_key_for_prompt_toolkit(_raw_key)
            if (
                isinstance(_raw_key, str)
                and _raw_key.strip().lower().split("+", 1)[0].strip() in {"super", "win", "windows"}
                and _voice_key == "c-b"
            ):
                logger.warning(
                    "voice.record_key %r uses a TUI-only modifier (super/win); "
                    "CLI fell back to Ctrl+B. Use ctrl+<key> or alt+<key> for "
                    "cross-runtime parity.",
                    _raw_key,
                )
        except Exception:
            _voice_key = "c-b"

        # Cache the UI label here — same ``_raw_key`` that drives the
        # prompt_toolkit binding below. Every status / placeholder /
        # recording-hint render reads this cached value so display can
        # never drift from the live keybinding even if the user edits
        # voice.record_key mid-session (Copilot round-13 on #19835).
        self.set_voice_record_key_cache(_raw_key)

        @kb.add(_voice_key)
        def handle_voice_record(event):
            """Toggle voice recording when voice mode is active.

            IMPORTANT: This handler runs in prompt_toolkit's event-loop thread.
            Any blocking call here (locks, sd.wait, disk I/O) freezes the
            entire UI.  All heavy work is dispatched to daemon threads.
            """
            if not cli_ref._voice_mode:
                return
            # Always allow STOPPING a recording (even when agent is running)
            if cli_ref._voice_recording:
                # Manual stop via push-to-talk key: stop continuous mode
                with cli_ref._voice_lock:
                    cli_ref._voice_continuous = False
                # Flag clearing is handled atomically inside _voice_stop_and_transcribe
                event.app.invalidate()
                threading.Thread(
                    target=cli_ref._voice_stop_and_transcribe,
                    daemon=True,
                ).start()
            else:
                # Guard: don't START recording during agent run or interactive prompts
                if cli_ref._agent_running:
                    return
                if cli_ref._clarify_state or cli_ref._sudo_state or cli_ref._approval_state or cli_ref._slash_confirm_state:
                    return
                # Guard: don't start while a previous stop/transcribe cycle is
                # still running — recorder.stop() holds AudioRecorder._lock and
                # start() would block the event-loop thread waiting for it.
                if cli_ref._voice_processing:
                    return

                # Interrupt TTS if playing, so user can start talking.
                # stop_playback() is fast (just terminates a subprocess).
                if not cli_ref._voice_tts_done.is_set():
                    try:
                        from tools.voice_mode import stop_playback
                        stop_playback()
                        cli_ref._voice_tts_done.set()
                    except Exception:
                        logger.warning("[fix_01_sessiz_except] Exception")

                with cli_ref._voice_lock:
                    cli_ref._voice_continuous = True

                # Dispatch to a daemon thread so play_beep(sd.wait),
                # AudioRecorder.start(lock acquire), and config I/O
                # never block the prompt_toolkit event loop.
                def _start_recording():
                    try:
                        cli_ref._voice_start_recording()
                        if hasattr(cli_ref, '_app') and cli_ref._app:
                            cli_ref._app.invalidate()
                    except Exception as e:
                        _cprint(f"\n{_DIM}Voice recording failed: {e}{_RST}")

                threading.Thread(target=_start_recording, daemon=True).start()
                event.app.invalidate()
        from prompt_toolkit.keys import Keys

        @kb.add(Keys.BracketedPaste, eager=True)
        def handle_paste(event):
            """Handle terminal paste — detect clipboard images.

            When the terminal supports bracketed paste, Ctrl+V / Cmd+V
            triggers this with the pasted text. We only auto-attach a
            clipboard image for image-only/empty paste gestures so text
            pastes and dictation do not accidentally attach stale images.

            Large pastes (5+ lines) are collapsed to a file reference
            placeholder while preserving any existing user text in the
            buffer.
            """
            # Diagnostic canary: measure how long the paste handler blocks
            # the prompt_toolkit event loop. If this exceeds ~500ms we log
            # it so recurring "CLI freezes on paste" reports (issue #16263,
            # macOS Tahoe 26 + iTerm2/Ghostty) arrive with data attached.
            _paste_handler_start = time.perf_counter()
            _paste_raw_size = len(event.data or "")
            pasted_text = event.data or ""
            # Normalise line endings — Windows \r\n and old Mac \r both become \n
            # so the 5-line collapse threshold and display are consistent.
            pasted_text = pasted_text.replace('\r\n', '\n').replace('\r', '\n')
            pasted_text = _strip_leaked_bracketed_paste_wrappers(pasted_text)
            pasted_text, _had_mouse_reports = _strip_leaked_terminal_responses_with_meta(pasted_text)
            if _had_mouse_reports:
                self._recover_terminal_input_modes(reason="mouse reports leaked into bracketed paste payload")
            if _should_auto_attach_clipboard_image_on_paste(pasted_text) and self._try_attach_clipboard_image():
                event.app.invalidate()
            if pasted_text:
                # Sanitize surrogate characters (e.g. from Word/Google Docs paste) before writing
                from reymen.sistem.run_agent import _sanitize_surrogates
                pasted_text = _sanitize_surrogates(pasted_text)
                line_count = pasted_text.count('\n')
                buf = event.current_buffer
                threshold = self.config.get("paste_collapse_threshold", 5)
                char_threshold = self.config.get("paste_collapse_char_threshold", 2000)
                lines_hit = threshold > 0 and line_count >= threshold
                chars_hit = char_threshold > 0 and len(pasted_text) >= char_threshold
                if (lines_hit or chars_hit) and not buf.text.strip().startswith('/'):
                    _paste_counter[0] += 1
                    paste_dir = _ReYMeN_home / "pastes"
                    paste_dir.mkdir(parents=True, exist_ok=True)
                    paste_file = paste_dir / f"paste_{_paste_counter[0]}_{datetime.now().strftime('%H%M%S')}.txt"
                    paste_file.write_text(pasted_text, encoding="utf-8")
                    logger.info("Collapsed paste #%d: %d lines, %d chars -> %s", _paste_counter[0], line_count + 1, len(pasted_text), paste_file)
                    placeholder = f"[Pasted text #{_paste_counter[0]}: {line_count + 1} lines \u2192 {paste_file}]"
                    prefix = ""
                    if buf.cursor_position > 0 and buf.text[buf.cursor_position - 1] != '\n':
                        prefix = "\n"
                    _paste_just_collapsed[0] = True
                    buf.insert_text(prefix + placeholder)
                else:
                    buf.insert_text(pasted_text)
            _paste_handler_elapsed_ms = (time.perf_counter() - _paste_handler_start) * 1000.0
            if _paste_handler_elapsed_ms > 500.0:
                logger.warning(
                    "Slow bracketed-paste handler: %.1fms to process %d bytes "
                    "(%d lines) on %s. If the input becomes unresponsive after "
                    "this, attach this log line to the bug report.",
                    _paste_handler_elapsed_ms,
                    _paste_raw_size,
                    pasted_text.count('\n') + 1 if pasted_text else 0,
                    sys.platform,
                )

        @kb.add('c-v')
        def handle_ctrl_v(event):
            """Fallback image paste for terminals without bracketed paste.

            On Linux terminals (GNOME Terminal, Konsole, etc.), Ctrl+V
            sends raw byte 0x16 instead of triggering a paste.  This
            binding catches that and checks the clipboard for images.
            On terminals that DO intercept Ctrl+V for paste (macOS
            Terminal, iTerm2, VSCode, Windows Terminal), the bracketed
            paste handler fires instead and this binding never triggers.
            """
            if self._try_attach_clipboard_image():
                event.app.invalidate()

        @kb.add('escape', 'v')
        def handle_alt_v(event):
            """Alt+V — paste image from clipboard.

            Alt key combos pass through all terminal emulators (sent as
            ESC + key), unlike Ctrl+V which terminals intercept for text
            paste.  This is the reliable way to attach clipboard images
            on WSL2, VSCode, and any terminal over SSH where Ctrl+V
            can't reach the application for image-only clipboard.
            """
            if self._try_attach_clipboard_image():
                event.app.invalidate()
            else:
                # No image found — show a hint
                pass  # silent when no image (avoid noise on accidental press)

        # Dynamic prompt: shows ReYMeN symbol when agent is working,
        # or answer prompt when clarify freetext mode is active.
        cli_ref = self

        def get_prompt():
            return cli_ref._get_tui_prompt_fragments()

        # Create the input area with multiline (Alt+Enter), autocomplete, and paste handling
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory


        _completer = SlashCommandCompleter(
            skill_commands_provider=lambda: get_skill_commands(),
            command_filter=cli_ref._command_available,
            skill_bundles_provider=lambda: get_skill_bundles(),
        )
        input_area = TextArea(
            height=Dimension(min=1, max=8, preferred=1),
            prompt=get_prompt,
            style='class:input-area',
            multiline=True,
            wrap_lines=True,
            read_only=Condition(lambda: bool(cli_ref._command_running)),
            history=FileHistory(str(self._history_file)),
            completer=_completer,
            complete_while_typing=True,
            auto_suggest=SlashCommandAutoSuggest(
                history_suggest=AutoSuggestFromHistory(),
                completer=_completer,
            ),
        )
        # Keep prompt_toolkit on its simple tempfile path. Setting
        # buffer.tempfile = "prompt.md" triggers its complex-tempfile branch,
        # which tries to mkdir() the mkdtemp() directory again and raises
        # EEXIST. The suffix keeps markdown highlighting without that bug.
        input_area.buffer.tempfile_suffix = '.md'

        # Dynamic height: accounts for both explicit newlines AND visual
        # wrapping of long lines so the input area always fits its content.
        def _input_height():
            try:
                from prompt_toolkit.application import get_app
                from prompt_toolkit.utils import get_cwidth

                doc = input_area.buffer.document
                prompt_width = max(2, get_cwidth(self._get_tui_prompt_text()))
                try:
                    available_width = get_app().output.get_size().columns - prompt_width
                except Exception:
                    available_width = shutil.get_terminal_size((80, 24)).columns - prompt_width
                if available_width < 10:
                    available_width = 40
                visual_lines = 0
                for line in doc.lines:
                    # Each logical line takes at least 1 visual row; long lines wrap.
                    # Use prompt_toolkit's cell width so CJK wide characters count as 2.
                    line_width = get_cwidth(line)
                    if line_width <= 0:
                        visual_lines += 1
                    else:
                        visual_lines += max(1, -(-line_width // available_width))  # ceil division
                return min(max(visual_lines, 1), 8)
            except Exception:
                return 1

        input_area.window.height = _input_height

        # Paste collapsing: detect large pastes and save to temp file
        _paste_counter = [0]
        _prev_text_len = [0]
        _prev_newline_count = [0]
        _paste_just_collapsed = [False]
        self._skip_paste_collapse = False

        def _on_text_changed(buf):
            """Detect large pastes and collapse them to a file reference.

            When bracketed paste is available, handle_paste collapses
            large pastes directly.  This handler is a fallback for
            terminals without bracketed paste support.

            Two heuristics (either triggers collapse):
            1. Many characters added at once (chars_added > 1) — works
               when the terminal delivers the paste in one event-loop tick.
            2. Newline count jumped by 4+ in a single text-change event —
               catches terminals that feed characters individually but
               still batch newlines.  Alt+Enter only adds 1 newline per
               event so it never triggers this.
            """
            text = _strip_leaked_bracketed_paste_wrappers(buf.text)
            text, _had_mouse_reports = _strip_leaked_terminal_responses_with_meta(text)
            if _had_mouse_reports:
                self._recover_terminal_input_modes(reason="mouse reports leaked into prompt buffer")
            if text != buf.text:
                cursor = min(buf.cursor_position, len(text))
                _paste_just_collapsed[0] = True
                buf.text = text
                buf.cursor_position = cursor
                _prev_text_len[0] = len(text)
                _prev_newline_count[0] = text.count('\n')
                return
            chars_added = len(text) - _prev_text_len[0]
            _prev_text_len[0] = len(text)
            if _paste_just_collapsed[0] or self._skip_paste_collapse:
                _paste_just_collapsed[0] = False
                self._skip_paste_collapse = False
                _prev_newline_count[0] = text.count('\n')
                return
            line_count = text.count('\n')
            newlines_added = line_count - _prev_newline_count[0]
            _prev_newline_count[0] = line_count
            is_paste = chars_added > 1 or newlines_added >= 4
            threshold = self.config.get("paste_collapse_threshold_fallback", 5)
            char_threshold = self.config.get("paste_collapse_char_threshold", 2000)
            lines_hit = threshold > 0 and line_count >= threshold
            chars_hit = char_threshold > 0 and len(text) >= char_threshold
            if (lines_hit or chars_hit) and is_paste and not text.startswith('/'):
                _paste_counter[0] += 1
                paste_dir = _ReYMeN_home / "pastes"
                paste_dir.mkdir(parents=True, exist_ok=True)
                paste_file = paste_dir / f"paste_{_paste_counter[0]}_{datetime.now().strftime('%H%M%S')}.txt"
                paste_file.write_text(text, encoding="utf-8")
                logger.info("Collapsed paste #%d: %d lines, %d chars -> %s (fallback)", _paste_counter[0], line_count + 1, len(text), paste_file)
                _paste_just_collapsed[0] = True
                buf.text = f"[Pasted text #{_paste_counter[0]}: {line_count + 1} lines \u2192 {paste_file}]"
                buf.cursor_position = len(buf.text)

        input_area.buffer.on_text_changed += _on_text_changed

        # --- Input processors for password masking and inline placeholder ---

        # Mask input with '*' when the sudo password prompt is active
        input_area.control.input_processors.append(
            ConditionalProcessor(
                PasswordProcessor(),
                filter=Condition(
                    lambda: bool(cli_ref._sudo_state) or bool(cli_ref._secret_state)
                ),
            )
        )

        class _PlaceholderProcessor(Processor):
            """Render grayed-out placeholder text inside the input when empty."""
            def __init__(self, get_text):
                self._get_text = get_text

            def apply_transformation(self, ti):
                if not ti.document.text and ti.lineno == 0:
                    text = self._get_text()
                    if text:
                        # Append after existing fragments (preserves the ❯ prompt)
                        return Transformation(fragments=ti.fragments + [('class:placeholder', text)])
                return Transformation(fragments=ti.fragments)

        def _get_placeholder():
            if cli_ref._voice_recording:
                _label = cli_ref._voice_record_key_label()
                return f"recording... {_label} to stop, Ctrl+C to cancel"
            if cli_ref._voice_processing:
                return "transcribing..."
            if cli_ref._sudo_state:
                return "type password (hidden), Enter to submit · ESC to skip"
            if cli_ref._secret_state:
                return "type secret (hidden), Enter to submit · ESC to skip"
            if cli_ref._approval_state:
                return ""
            if cli_ref._slash_confirm_state:
                return "type 1/2/3, or use ↑/↓ then Enter"
            if cli_ref._clarify_freetext:
                return "type your answer here and press Enter"
            if cli_ref._clarify_state:
                return ""
            if cli_ref._command_running:
                frame = cli_ref._command_spinner_frame()
                status = cli_ref._command_status or "Processing command..."
                return f"{frame} {status}"
            if cli_ref._agent_running:
                return "msg=interrupt · /queue · /bg · /steer · Ctrl+C cancel"
            if cli_ref._voice_mode:
                _label = cli_ref._voice_record_key_label()
                return f"type or {_label} to record"
            return ""

        input_area.control.input_processors.append(_PlaceholderProcessor(_get_placeholder))

        # Hint line above input: shown only for interactive prompts that need
        # extra instructions (sudo countdown, approval navigation, clarify).
        # The agent-running interrupt hint is now an inline placeholder above.
        def get_hint_text():
            if cli_ref._sudo_state:
                remaining = max(0, int(cli_ref._sudo_deadline - time.monotonic()))
                return [
                    ('class:hint', '  password hidden · Enter to skip'),
                    ('class:clarify-countdown', f'  ({remaining}s)'),
                ]

            if cli_ref._secret_state:
                remaining = max(0, int(cli_ref._secret_deadline - time.monotonic()))
                return [
                    ('class:hint', '  secret hidden · Enter to skip'),
                    ('class:clarify-countdown', f'  ({remaining}s)'),
                ]

            if cli_ref._approval_state:
                remaining = max(0, int(cli_ref._approval_deadline - time.monotonic()))
                return [
                    ('class:hint', '  ↑/↓ to select, Enter to confirm'),
                    ('class:clarify-countdown', f'  ({remaining}s)'),
                ]

            if cli_ref._slash_confirm_state:
                remaining = max(0, int(cli_ref._slash_confirm_deadline - time.monotonic()))
                return [
                    ('class:hint', '  type 1/2/3, or ↑/↓ to select, Enter to confirm'),
                    ('class:clarify-countdown', f'  ({remaining}s)'),
                ]

            if cli_ref._clarify_state:
                remaining = max(0, int(cli_ref._clarify_deadline - time.monotonic()))
                countdown = f'  ({remaining}s)' if cli_ref._clarify_deadline else ''
                if cli_ref._clarify_freetext:
                    return [
                        ('class:hint', '  type your answer and press Enter'),
                        ('class:clarify-countdown', countdown),
                    ]
                return [
                    ('class:hint', '  ↑/↓ to select, Enter to confirm'),
                    ('class:clarify-countdown', countdown),
                ]

            if cli_ref._command_running:
                frame = cli_ref._command_spinner_frame()
                return [
                    ('class:hint', f'  {frame} command in progress · input temporarily disabled'),
                ]

            return []

        def get_hint_height():
            if cli_ref._sudo_state or cli_ref._secret_state or cli_ref._approval_state or cli_ref._slash_confirm_state or cli_ref._clarify_state or cli_ref._command_running:
                return 1
            # Keep a spacer while the agent runs on roomy terminals, but reclaim
            # the row on narrow/mobile screens where every line matters.
            return cli_ref._agent_spacer_height()

        def get_spinner_text():
            spinner_line = cli_ref._render_spinner_text()
            if not spinner_line:
                return []
            return [('class:hint', spinner_line)]

        def get_spinner_height():
            return cli_ref._spinner_widget_height()

        spinner_widget = Window(
            content=FormattedTextControl(get_spinner_text),
            height=get_spinner_height,
            wrap_lines=True,
        )

        spacer = Window(
            content=FormattedTextControl(get_hint_text),
            height=get_hint_height,
        )

        # --- Clarify tool: dynamic display widget for questions + choices ---

        def _panel_box_width(title: str, content_lines: list[str], min_width: int = 46, max_width: int = 76) -> int:
            """Choose a stable panel width wide enough for the title and content."""
            term_cols = shutil.get_terminal_size((100, 20)).columns
            longest = max([len(title)] + [len(line) for line in content_lines] + [min_width - 4])
            inner = min(max(longest + 4, min_width - 2), max_width - 2, max(24, term_cols - 6))
            return inner + 2  # account for the single leading/trailing spaces inside borders

        def _wrap_panel_text(text: str, width: int, subsequent_indent: str = "") -> list[str]:
            wrapped = textwrap.wrap(
                text,
                width=max(8, width),
                break_long_words=False,
                break_on_hyphens=False,
                subsequent_indent=subsequent_indent,
            )
            return wrapped or [""]

        def _append_panel_line(lines, border_style: str, content_style: str, text: str, box_width: int) -> None:
            inner_width = max(0, box_width - 2)
            lines.append((border_style, "│ "))
            lines.append((content_style, text.ljust(inner_width)))
            lines.append((border_style, " │\n"))

        def _append_blank_panel_line(lines, border_style: str, box_width: int) -> None:
            lines.append((border_style, "│" + (" " * box_width) + "│\n"))

        def _get_clarify_display():
            """Build styled text for the clarify question/choices panel.

            Layout priority: choices + Other option must always render even if
            the question is very long. The question is budgeted to leave enough
            rows for the choices and trailing chrome; anything over the budget
            is truncated with a marker.
            """
            state = cli_ref._clarify_state
            if not state:
                return []

            question = state["question"]
            choices = state.get("choices") or []
            selected = state.get("selected", 0)
            preview_lines = _wrap_panel_text(question, 60)
            for i, choice in enumerate(choices):
                # Show number prefix for quick selection (1-9 for items 1-9, 0 for 10th item)
                if i < 9:
                    num_prefix = str(i + 1)
                elif i == 9:
                    num_prefix = '0'
                else:
                    num_prefix = ' '
                if i == selected and not cli_ref._clarify_freetext:
                    prefix = f"❯ {num_prefix}. "
                else:
                    prefix = f"  {num_prefix}. "
                preview_lines.extend(_wrap_panel_text(f"{prefix}{choice}", 60, subsequent_indent="    "))
            # "Other" option in preview
            other_num = len(choices) + 1
            if other_num < 10:
                other_num_prefix = str(other_num)
            elif other_num == 10:
                other_num_prefix = '0'
            else:
                other_num_prefix = ' '
            other_label = (
                f"❯ {other_num_prefix}. Other (type below)" if cli_ref._clarify_freetext
                else f"❯ {other_num_prefix}. Other (type your answer)" if selected == len(choices)
                else f"  {other_num_prefix}. Other (type your answer)"
            )
            preview_lines.extend(_wrap_panel_text(other_label, 60, subsequent_indent="    "))
            box_width = _panel_box_width("ReYMeN needs your input", preview_lines)
            inner_text_width = max(8, box_width - 2)

            # Pre-wrap choices + Other option — these are mandatory.
            choice_wrapped: list[tuple[int, str]] = []
            if choices:
                for i, choice in enumerate(choices):
                    # Show number prefix for quick selection (1-9 for items 1-9, 0 for 10th item)
                    if i < 9:
                        num_prefix = str(i + 1)
                    elif i == 9:
                        num_prefix = '0'
                    else:
                        num_prefix = ' '
                    if i == selected and not cli_ref._clarify_freetext:
                        prefix = f'❯ {num_prefix}. '
                    else:
                        prefix = f'  {num_prefix}. '
                    for wrapped in _wrap_panel_text(f"{prefix}{choice}", inner_text_width, subsequent_indent="    "):
                        choice_wrapped.append((i, wrapped))
                # Trailing Other row(s)
                other_idx = len(choices)
                other_num = other_idx + 1
                if other_num < 10:
                    other_num_prefix = str(other_num)
                elif other_num == 10:
                    other_num_prefix = '0'
                else:
                    other_num_prefix = ' '
                if selected == other_idx and not cli_ref._clarify_freetext:
                    other_label_mand = f'❯ {other_num_prefix}. Other (type your answer)'
                elif cli_ref._clarify_freetext:
                    other_label_mand = f'❯ {other_num_prefix}. Other (type below)'
                else:
                    other_label_mand = f'  {other_num_prefix}. Other (type your answer)'
                other_wrapped = _wrap_panel_text(other_label_mand, inner_text_width, subsequent_indent="    ")
            elif cli_ref._clarify_freetext:
                # Freetext-only mode: the guidance line takes the place of choices.
                other_wrapped = _wrap_panel_text(
                    "Type your answer in the prompt below, then press Enter.",
                    inner_text_width,
                )
            else:
                other_wrapped = []

            # Budget the question so mandatory rows always render.
            # Chrome layouts:
            #   full : top border + blank_after_title + blank_after_question
            #          + blank_before_bottom + bottom border = 5 rows
            #   tight: top border + bottom border = 2 rows (drop all blanks)
            #
            # reserved_below matches the approval-panel budget (~6 rows for
            # spinner/tool-progress + status + input + separators + prompt).
            term_rows = shutil.get_terminal_size((100, 24)).lines
            chrome_full = 5
            chrome_tight = 2
            reserved_below = 6

            available = max(0, term_rows - reserved_below)
            # The compact decision must reserve room for at least one question
            # row on top of the choices, otherwise full chrome (3 blank
            # separators) gets kept when there is no room for it and the panel
            # overflows the viewport — HSplit then clips the panel's tail,
            # silently dropping the choices (the reported bug).
            mandatory_full = chrome_full + 1 + len(choice_wrapped) + len(other_wrapped)

            use_compact_chrome = mandatory_full > available
            chrome_rows = chrome_tight if use_compact_chrome else chrome_full

            max_question_rows = max(1, available - chrome_rows - len(choice_wrapped) - len(other_wrapped))
            max_question_rows = min(max_question_rows, 12)  # soft cap on huge terminals

            # When the choices alone (plus compact chrome) already exceed the
            # viewport, drop the question entirely — the choices are the only
            # thing the user must see to make a selection. Without this the
            # question would still claim its 1-row floor above and push the
            # tail of the choices off-screen (HSplit clips the overflow).
            choices_overflow = chrome_rows + len(choice_wrapped) + len(other_wrapped) >= available
            if choices_overflow:
                max_question_rows = 0

            question_wrapped = _wrap_panel_text(question, inner_text_width)
            if max_question_rows <= 0:
                question_wrapped = []
            elif len(question_wrapped) > max_question_rows:
                # The truncation marker is itself a row, so it must count
                # against the budget. With a 1-row budget there is no room for
                # both a question line and the marker — show the marker alone
                # so the rendered question never exceeds max_question_rows.
                keep = max(0, max_question_rows - 1)
                question_wrapped = question_wrapped[:keep] + ["… (question truncated)"]

            lines = []
            # Box top border
            lines.append(('class:clarify-border', '╭─ '))
            lines.append(('class:clarify-title', 'ReYMeN needs your input'))
            lines.append(('class:clarify-border', ' ' + ('─' * max(0, box_width - len("ReYMeN needs your input") - 3)) + '╮\n'))
            if not use_compact_chrome:
                _append_blank_panel_line(lines, 'class:clarify-border', box_width)

            # Question text (bounded)
            for wrapped in question_wrapped:
                _append_panel_line(lines, 'class:clarify-border', 'class:clarify-question', wrapped, box_width)
            if not use_compact_chrome:
                _append_blank_panel_line(lines, 'class:clarify-border', box_width)

            if cli_ref._clarify_freetext and not choices:
                for wrapped in other_wrapped:
                    _append_panel_line(lines, 'class:clarify-border', 'class:clarify-choice', wrapped, box_width)
                if not use_compact_chrome:
                    _append_blank_panel_line(lines, 'class:clarify-border', box_width)

            if choices:
                # Multiple-choice mode: show selectable options
                for i, wrapped in choice_wrapped:
                    style = 'class:clarify-selected' if i == selected and not cli_ref._clarify_freetext else 'class:clarify-choice'
                    _append_panel_line(lines, 'class:clarify-border', style, wrapped, box_width)

                # "Other" option (trailing row(s), only shown when choices exist)
                other_idx = len(choices)
                # Calculate number prefix for "Other" option
                other_num = other_idx + 1
                if other_num < 10:
                    other_num_prefix = str(other_num)
                elif other_num == 10:
                    other_num_prefix = '0'
                else:
                    other_num_prefix = ' '
                
                if selected == other_idx and not cli_ref._clarify_freetext:
                    other_style = 'class:clarify-selected'
                elif cli_ref._clarify_freetext:
                    other_style = 'class:clarify-active-other'
                else:
                    other_style = 'class:clarify-choice'
                for wrapped in other_wrapped:
                    _append_panel_line(lines, 'class:clarify-border', other_style, wrapped, box_width)

            if not use_compact_chrome:
                _append_blank_panel_line(lines, 'class:clarify-border', box_width)
            lines.append(('class:clarify-border', '╰' + ('─' * box_width) + '╯\n'))
            return lines

        clarify_widget = ConditionalContainer(
            Window(
                FormattedTextControl(_get_clarify_display),
                wrap_lines=True,
            ),
            filter=Condition(lambda: cli_ref._clarify_state is not None),
        )

        # --- Sudo password: display widget ---

        def _get_sudo_display():
            state = cli_ref._sudo_state
            if not state:
                return []
            title = '🔐 Sudo Password Required'
            body = 'Enter password below (hidden), or press Enter to skip'
            box_width = _panel_box_width(title, [body])
            lines = []
            lines.append(('class:sudo-border', '╭─ '))
            lines.append(('class:sudo-title', title))
            lines.append(('class:sudo-border', ' ' + ('─' * max(0, box_width - len(title) - 3)) + '╮\n'))
            _append_blank_panel_line(lines, 'class:sudo-border', box_width)
            _append_panel_line(lines, 'class:sudo-border', 'class:sudo-text', body, box_width)
            _append_blank_panel_line(lines, 'class:sudo-border', box_width)
            lines.append(('class:sudo-border', '╰' + ('─' * box_width) + '╯\n'))
            return lines

        sudo_widget = ConditionalContainer(
            Window(
                FormattedTextControl(_get_sudo_display),
                wrap_lines=True,
            ),
            filter=Condition(lambda: cli_ref._sudo_state is not None),
        )

        def _get_secret_display():
            state = cli_ref._secret_state
            if not state:
                return []

            title = '🔑 Skill Setup Required'
            prompt = state.get("prompt") or f"Enter value for {state.get('var_name', 'secret')}"
            metadata = state.get("metadata") or {}
            help_text = metadata.get("help")
            body = 'Enter secret below (hidden), ESC or Ctrl+C to skip'
            content_lines = [prompt, body]
            if help_text:
                content_lines.insert(1, str(help_text))
            box_width = _panel_box_width(title, content_lines)
            lines = []
            lines.append(('class:sudo-border', '╭─ '))
            lines.append(('class:sudo-title', title))
            lines.append(('class:sudo-border', ' ' + ('─' * max(0, box_width - len(title) - 3)) + '╮\n'))
            _append_blank_panel_line(lines, 'class:sudo-border', box_width)
            _append_panel_line(lines, 'class:sudo-border', 'class:sudo-text', prompt, box_width)
            if help_text:
                _append_panel_line(lines, 'class:sudo-border', 'class:sudo-text', str(help_text), box_width)
            _append_blank_panel_line(lines, 'class:sudo-border', box_width)
            _append_panel_line(lines, 'class:sudo-border', 'class:sudo-text', body, box_width)
            _append_blank_panel_line(lines, 'class:sudo-border', box_width)
            lines.append(('class:sudo-border', '╰' + ('─' * box_width) + '╯\n'))
            return lines

        secret_widget = ConditionalContainer(
            Window(
                FormattedTextControl(_get_secret_display),
                wrap_lines=True,
            ),
            filter=Condition(lambda: cli_ref._secret_state is not None),
        )

        # --- Dangerous command approval: display widget ---

        def _get_approval_display():
            return cli_ref._get_approval_display_fragments()

        approval_widget = ConditionalContainer(
            Window(
                FormattedTextControl(_get_approval_display),
                wrap_lines=True,
            ),
            filter=Condition(lambda: cli_ref._approval_state is not None),
        )

        def _get_slash_confirm_display():
            return cli_ref._get_slash_confirm_display_fragments()

        slash_confirm_widget = ConditionalContainer(
            Window(
                FormattedTextControl(_get_slash_confirm_display),
                wrap_lines=True,
            ),
            filter=Condition(lambda: cli_ref._slash_confirm_state is not None),
        )

        # --- /model picker: display widget ---
        def _get_model_picker_display():
            state = cli_ref._model_picker_state
            if not state:
                return []
            stage = state.get("stage", "provider")
            if stage == "provider":
                title = "⚙ Model Picker — Select Provider"
                choices = []
                _providers = state.get("providers")
                for p in _providers if isinstance(_providers, list) else []:
                    count = p.get("total_models", len(p.get("models", [])))
                    label = f"{p['name']} ({count} model{'s' if count != 1 else ''})"
                    if p.get("is_current"):
                        label += "  ← current"
                    choices.append(label)
                choices.append("Cancel")
                hint = f"Current: {state.get('current_model', 'unknown')} on {state.get('current_provider', 'unknown')}"
            else:
                provider_data = state.get("provider_data") or {}
                model_list = state.get("model_list") or []
                title = f"⚙ Model Picker — {provider_data.get('name', provider_data.get('slug', 'Provider'))}"
                choices = list(model_list) + ["← Back", "Cancel"]
                if model_list:
                    hint = f"Select a model ({len(model_list)} available)"
                else:
                    hint = "No models listed for this provider. Use Back or Cancel."

            box_width = _panel_box_width(title, [hint] + choices, min_width=46, max_width=84)
            inner_text_width = max(8, box_width - 6)
            selected = state.get("selected", 0)

            # Scrolling viewport: the panel renders into a Window with no max
            # height, so without limiting visible items the bottom border and
            # any items past the available terminal rows get clipped on long
            # provider catalogs (e.g. Ollama Cloud's 36+ models).
            try:
                from prompt_toolkit.application import get_app
                term_rows = get_app().output.get_size().rows
            except Exception:
                term_rows = shutil.get_terminal_size((100, 24)).lines
            scroll_offset, visible = ReYMeNCLI._compute_model_picker_viewport(
                selected, state.get("_scroll_offset", 0), len(choices), term_rows,
            )
            state["_scroll_offset"] = scroll_offset

            lines = []
            lines.append(('class:clarify-border', '╭─ '))
            lines.append(('class:clarify-title', title))
            lines.append(('class:clarify-border', ' ' + ('─' * max(0, box_width - len(title) - 3)) + '╮\n'))
            _append_blank_panel_line(lines, 'class:clarify-border', box_width)
            _append_panel_line(lines, 'class:clarify-border', 'class:clarify-hint', hint, box_width)
            _append_blank_panel_line(lines, 'class:clarify-border', box_width)
            for idx in range(scroll_offset, scroll_offset + visible):
                choice = choices[idx]
                style = 'class:clarify-selected' if idx == selected else 'class:clarify-choice'
                prefix = '❯ ' if idx == selected else '  '
                for wrapped in _wrap_panel_text(prefix + choice, inner_text_width, subsequent_indent='  '):
                    _append_panel_line(lines, 'class:clarify-border', style, wrapped, box_width)
            _append_blank_panel_line(lines, 'class:clarify-border', box_width)
            lines.append(('class:clarify-border', '╰' + ('─' * box_width) + '╯\n'))
            return lines

        model_picker_widget = ConditionalContainer(
            Window(
                FormattedTextControl(_get_model_picker_display),
                wrap_lines=True,
            ),
            filter=Condition(lambda: cli_ref._model_picker_state is not None),
        )

        # Horizontal rules above and below the input.
        # On narrow/mobile terminals we keep the top separator for structure but
        # hide the bottom one to recover a full row for conversation content.
        input_rule_top = Window(
            char='─',
            height=lambda: cli_ref._tui_input_rule_height("top"),
            style='class:input-rule',
        )
        input_rule_bot = Window(
            char='─',
            height=lambda: cli_ref._tui_input_rule_height("bottom"),
            style='class:input-rule',
        )

        # Image attachment indicator — shows badges like [📎 Image #1] above input
        cli_ref = self

        def _get_image_bar():
            if not cli_ref._attached_images:
                return []
            badges = _format_image_attachment_badges(
                cli_ref._attached_images,
                cli_ref._image_counter,
            )
            return [("class:image-badge", f" {badges} ")]

        image_bar = Window(
            content=FormattedTextControl(_get_image_bar),
            height=Condition(lambda: bool(cli_ref._attached_images)),
        )

        # Persistent voice mode status bar (visible only when voice mode is on)
        def _get_voice_status():
            return cli_ref._get_voice_status_fragments()

        voice_status_bar = ConditionalContainer(
            Window(
                FormattedTextControl(_get_voice_status),
                height=1,
            ),
            filter=Condition(lambda: cli_ref._voice_mode),
        )

        status_bar = ConditionalContainer(
            Window(
                content=FormattedTextControl(lambda: cli_ref._get_status_bar_fragments()),
                height=1,
                # Prevent fragments that overflow the terminal width from
                # wrapping onto a second line, which causes the status bar to
                # appear duplicated (one full + one partial row) during long
                # sessions, especially on SSH where shutil.get_terminal_size
                # may return stale values.  _get_status_bar_fragments now reads
                # width from prompt_toolkit's own output object, so fragments
                # will always fit; wrap_lines=False is the belt-and-suspenders
                # guard against any future width mismatch.
                wrap_lines=False,
            ),
            filter=Condition(
                lambda: cli_ref._status_bar_visible
                and not getattr(cli_ref, "_status_bar_suppressed_after_resize", False)
            ),
        )

        # Allow wrapper CLIs to register extra keybindings.
        self._register_extra_tui_keybindings(kb, input_area=input_area)

        # Layout: interactive prompt widgets + ruled input at bottom.
        # The sudo, approval, and clarify widgets appear above the input when
        # the corresponding interactive prompt is active.
        completions_menu = CompletionsMenu(max_height=12, scroll_offset=1)

        layout = Layout(
            HSplit(
                self._build_tui_layout_children(
                    sudo_widget=sudo_widget,
                    secret_widget=secret_widget,
                    approval_widget=approval_widget,
                    slash_confirm_widget=slash_confirm_widget,
                    clarify_widget=clarify_widget,
                    model_picker_widget=model_picker_widget,
                    spinner_widget=spinner_widget,
                    spacer=spacer,
                    status_bar=status_bar,
                    input_rule_top=input_rule_top,
                    image_bar=image_bar,
                    input_area=input_area,
                    input_rule_bot=input_rule_bot,
                    voice_status_bar=voice_status_bar,
                    completions_menu=completions_menu,
                )
            )
        )
        
        # Style for the application
        self._tui_style_base = {
            # Input area / prompt: empty style strings inherit the
            # terminal's default foreground/background, so the typed
            # text is readable in both light and dark Terminal.app
            # color schemes.  (Hardcoding a near-white #FFF8DC made
            # input invisible on light backgrounds.)
            'input-area': '',
            'placeholder': '#888888 italic',
            'prompt': '',
            'prompt-working': '#888888 italic',
            'hint': '#888888 italic',
            'status-bar': 'bg:#1a1a2e #C0C0C0',
            'status-bar-strong': 'bg:#1a1a2e #FFD700 bold',
            'status-bar-dim': 'bg:#1a1a2e #8B8682',
            'status-bar-good': 'bg:#1a1a2e #8FBC8F bold',
            'status-bar-warn': 'bg:#1a1a2e #FFD700 bold',
            'status-bar-bad': 'bg:#1a1a2e #FF8C00 bold',
            'status-bar-critical': 'bg:#1a1a2e #FF6B6B bold',
            'status-bar-yolo': 'bg:#1a1a2e #FF4444 bold',
            # Bronze horizontal rules around the input area
            'input-rule': '#CD7F32',
            # Clipboard image attachment badges
            'image-badge': '#87CEEB bold',
            'completion-menu': 'bg:#1a1a2e #FFF8DC',
            'completion-menu.completion': 'bg:#1a1a2e #FFF8DC',
            'completion-menu.completion.current': 'bg:#333355 #FFD700',
            'completion-menu.meta.completion': 'bg:#1a1a2e #888888',
            'completion-menu.meta.completion.current': 'bg:#333355 #FFBF00',
            # Clarify question panel
            'clarify-border': '#CD7F32',
            'clarify-title': '#FFD700 bold',
            'clarify-question': '#FFF8DC bold',
            'clarify-choice': '#AAAAAA',
            'clarify-selected': '#FFD700 bold',
            'clarify-active-other': '#FFD700 italic',
            'clarify-countdown': '#CD7F32',
            # Sudo password panel
            'sudo-prompt': '#FF6B6B bold',
            'sudo-border': '#CD7F32',
            'sudo-title': '#FF6B6B bold',
            'sudo-text': '#FFF8DC',
            # Dangerous command approval panel
            'approval-border': '#CD7F32',
            'approval-title': '#FF8C00 bold',
            'approval-desc': '#FFF8DC bold',
            'approval-cmd': '#AAAAAA italic',
            'approval-choice': '#AAAAAA',
            'approval-selected': '#FFD700 bold',
            # Voice mode
            'voice-prompt': '#87CEEB',
            'voice-recording': '#FF4444 bold',
            'voice-processing': '#FFA500 italic',
            'voice-status': 'bg:#1a1a2e #87CEEB',
            'voice-status-recording': 'bg:#1a1a2e #FF4444 bold',
        }
        style = PTStyle.from_dict(self._build_tui_style_dict())
        
        # Create the application
        app = Application(
            layout=layout,
            key_bindings=kb,
            style=style,
            full_screen=False,
            mouse_support=False,
            **({'cursor': _STEADY_CURSOR} if _STEADY_CURSOR is not None else {}),
        )
        _disable_prompt_toolkit_cpr_warning(app)
        self._app = app  # Store reference for clarify_callback

        # ── Fix ghost status-bar lines on terminal resize ──────────────
        # Resize handling: monkey-patch prompt_toolkit's _output_screen_diff
        # to suppress the deliberate "reserve vertical space" scroll-up.
        #
        # Background: prompt_toolkit's renderer (renderer.py L232-242)
        # explicitly moves the cursor to the bottom of the canvas after
        # painting "to make sure the terminal scrolls up, even when the
        # lower lines of the canvas just contain whitespace".  In
        # non-fullscreen mode this scrolls chrome content (status bar,
        # input rules) into terminal scrollback on every render.  When
        # the terminal column-shrinks, the emulator reflows the previously
        # rendered full-width rows into multiple narrower rows that get
        # pushed up — leaving ghost duplicates AND polluting scrollback.
        # Same issue as pt #29 (open since 2014), #1675, #1933.
        #
        # Surgical fix: wrap _output_screen_diff so that when its internal
        # `if current_height > previous_screen.height` branch fires (the
        # one that does the bottom-cursor-move), we make it fall through
        # by inflating previous_screen.height first.
        try:
            import prompt_toolkit.renderer as _pt_renderer
            from prompt_toolkit.renderer import _output_screen_diff as _orig_osd

            if not getattr(_pt_renderer, "_ReYMeN_osd_patched", False):
                def _patched_output_screen_diff(
                    app, output, screen, current_pos, color_depth,
                    previous_screen, last_style, is_done, full_screen,
                    attrs_for_style_string, style_string_has_style,
                    size, previous_width,
                ):
                    """Wraps pt's _output_screen_diff to suppress the
                    reserve-vertical-space scroll (renderer.py L232-242).

                    Strategy: ONLY when previous_screen is non-None and
                    its current height is genuinely smaller than the new
                    screen's height, inflate it to match.  This prevents
                    the bottom-cursor-move at L242 without changing any
                    other code path's behavior.

                    Critical: do NOT replace a None previous_screen with
                    a fresh Screen() — that would skip the proper
                    reset_attributes()+erase_down() at L178-185 which
                    fires when previous_screen is None (first-paint /
                    width-change).  Without that reset, ANSI styles
                    leak between renders.
                    """
                    try:
                        if previous_screen is not None and hasattr(previous_screen, "height"):
                            if previous_screen.height < screen.height:
                                previous_screen.height = screen.height
                    except Exception:
                        logger.warning("[fix_01_sessiz_except] Exception")

                    return _orig_osd(
                        app, output, screen, current_pos, color_depth,
                        previous_screen, last_style, is_done, full_screen,
                        attrs_for_style_string, style_string_has_style,
                        size, previous_width,
                    )

                _pt_renderer._output_screen_diff = _patched_output_screen_diff
                _pt_renderer._ReYMeN_osd_patched = True
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")

        # Apply bracketed-paste timeout recovery so torn ESC[201~ end marks
        # don't permanently freeze the input (issue #16263). Idempotent.
        _apply_bracketed_paste_timeout_patch()

        _original_on_resize = app._on_resize

        def _resize_clear_ghosts():
            self._schedule_resize_recovery(app, _original_on_resize)

        app._on_resize = _resize_clear_ghosts

        def spinner_loop():
            while not self._should_exit:
                if not self._app:
                    time.sleep(0.1)
                    continue
                if self._command_running:
                    self._invalidate(min_interval=0.1)
                    time.sleep(0.1)
                else:
                    # Do not repaint the idle prompt every second. In non-full-screen
                    # prompt_toolkit mode, background redraws can fight tmux/Ghostty/cmux
                    # viewport restoration after focus changes and visually move the
                    # command input area. Keep idle stable; input/agent events still
                    # invalidate explicitly when the UI actually changes.
                    time.sleep(0.2)

        spinner_thread = threading.Thread(target=spinner_loop, daemon=True)
        spinner_thread.start()
        
        # Background thread to process inputs and run agent
        def process_loop():
            while not self._should_exit:
                try:
                    # Check for pending input with timeout
                    try:
                        user_input = self._pending_input.get(timeout=0.1)
                    except queue.Empty:
                        # Periodic config watcher — auto-reload MCP on mcp_servers change
                        if not self._agent_running:
                            self._check_config_mcp_changes()
                            # Check for background process notifications (completions
                            # and watch pattern matches) while agent is idle.
                            try:
                                from tools.process_registry import process_registry
                                for _evt, _synth in process_registry.drain_notifications():
                                    self._pending_input.put(_synth)
                            except Exception:
                                logger.warning("[fix_01_sessiz_except] Exception")
                        continue
                    
                    if not user_input:
                        continue

                    # The user has typed and submitted something, so any
                    # post-resize transient suppression should end here.
                    self._status_bar_suppressed_after_resize = False

                    # Unpack image payload: (text, [Path, ...]) or plain str
                    submit_images = []
                    if isinstance(user_input, tuple):
                        user_input, submit_images = user_input

                    if isinstance(user_input, str):
                        user_input = _strip_leaked_bracketed_paste_wrappers(user_input)
                        user_input, _had_mouse_reports = _strip_leaked_terminal_responses_with_meta(user_input)
                        if _had_mouse_reports:
                            self._recover_terminal_input_modes(reason="mouse reports leaked into submitted input")
                    
                    # Check for commands — but detect dragged/pasted file paths first.
                    # See _detect_file_drop() for details.
                    _file_drop = _detect_file_drop(user_input) if isinstance(user_input, str) else None
                    if _file_drop:
                        _drop_path = _file_drop["path"]
                        _remainder = _file_drop["remainder"]
                        if _file_drop["is_image"]:
                            submit_images.append(_drop_path)
                            user_input = _remainder or f"[User attached image: {_drop_path.name}]"
                            _cprint(f"  📎 Auto-attached image: {_drop_path.name}")
                        else:
                            _cprint(f"  📄 Detected file: {_drop_path.name}")
                            user_input = (
                                f"[User attached file: {_drop_path}]"
                                + (f"\n{_remainder}" if _remainder else "")
                            )

                    # A bare number right after a bare `/resume` prompt selects
                    # that session (see #34584). Checked before chat routing so
                    # the digit isn't sent to the agent as a message.
                    if (
                        not _file_drop
                        and self._pending_resume_sessions
                        and isinstance(user_input, str)
                        and self._consume_pending_resume_selection(user_input)
                    ):
                        continue

                    if not _file_drop and isinstance(user_input, str) and _looks_like_slash_command(user_input):
                        _cprint(f"\n⚙️  {user_input}")
                        try:
                            if not self.process_command(user_input):
                                self._should_exit = True
                                # Schedule app exit
                                if app.is_running:
                                    app.exit()
                        except KeyboardInterrupt:
                            # Ctrl+C during a slow slash command (e.g. /skills browse,
                            # /sessions list with a large DB) should interrupt the
                            # command and return to the prompt, NOT exit the entire
                            # session. Without this guard a KeyboardInterrupt unwinds
                            # to the outer prompt_toolkit loop and the session dies.
                            _cprint("\n[dim]Command interrupted.[/dim]")
                        continue
                    
                    # Expand paste references back to full content
                    _paste_ref_re = re.compile(r'\[Pasted text #\d+: \d+ lines \u2192 (.+?)\]')
                    paste_refs = list(_paste_ref_re.finditer(user_input)) if isinstance(user_input, str) else []
                    if paste_refs:
                        user_input = self._expand_paste_references(user_input)
                    print()
                    self._print_user_message_preview(user_input)
                    
                    # Show image attachment count
                    if submit_images:
                        n = len(submit_images)
                        _cprint(f"  {_DIM}📎 {n} image{'s' if n > 1 else ''} attached{_RST}")

                    # Regular chat - run agent
                    self._agent_running = True
                    app.invalidate()  # Refresh status line

                    try:
                        self.chat(user_input, images=submit_images or None)
                    finally:
                        self._agent_running = False
                        self._spinner_text = ""
                        self._tool_start_time = 0.0
                        self._pending_tool_info.clear()
                        self._last_scrollback_tool = ""

                        app.invalidate()  # Refresh status line

                        # Goal continuation: if a standing goal is active, ask
                        # the judge whether the turn satisfied it. If not, and
                        # there's no real user message already queued, push the
                        # continuation prompt back into _pending_input so the
                        # next loop iteration picks it up naturally (and any
                        # user input that arrives in between still preempts).
                        try:
                            self._maybe_continue_goal_after_turn()
                        except Exception as _goal_exc:
                            logging.debug("goal continuation hook failed: %s", _goal_exc)

                        # Continuous voice: auto-restart recording after agent responds.
                        # Dispatch to a daemon thread so play_beep (sd.wait) and
                        # AudioRecorder.start (lock acquire) never block process_loop —
                        # otherwise queued user input would stall silently.
                        if self._voice_mode and self._voice_continuous and not self._voice_recording:
                            def _restart_recording():
                                try:
                                    if self._voice_tts:
                                        self._voice_tts_done.wait(timeout=60)
                                        time.sleep(0.3)
                                    self._voice_start_recording()
                                    app.invalidate()
                                except Exception as e:
                                    _cprint(f"{_DIM}Voice auto-restart failed: {e}{_RST}")
                            threading.Thread(target=_restart_recording, daemon=True).start()

                        # Drain process notifications (completions + watch matches)
                        # that arrived while the agent was running.
                        try:
                            from tools.process_registry import process_registry
                            for _evt, _synth in process_registry.drain_notifications():
                                self._pending_input.put(_synth)
                        except Exception as _e:
                            __import__("logging").getLogger(__name__).warning(
                                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                            )  # Non-fatal — don't break the main loop

                except Exception as e:
                    logger.warning("process_loop unhandled error (msg may be lost): %s", e)
        
        # Start processing thread
        process_thread = threading.Thread(target=process_loop, daemon=True)
        process_thread.start()
        
        # Register atexit cleanup so resources are freed even on unexpected exit
        atexit.register(_run_cleanup)
        
        # Register signal handlers for graceful shutdown on SSH disconnect / SIGTERM
        def _signal_handler(signum, frame):
            """Handle SIGHUP/SIGTERM by triggering graceful cleanup.

            Calls ``self.agent.interrupt()`` first so the agent daemon
            thread's poll loop sees the per-thread interrupt and kills the
            tool's subprocess group via ``_kill_process`` (os.killpg).
            Without this, the main thread dies from KeyboardInterrupt and
            the daemon thread is killed with it — before it can run one
            more poll iteration to clean up the subprocess, which was
            spawned with ``os.setsid`` and therefore survives as an orphan
            with PPID=1.

            Grace window (``ReYMeN_SIGTERM_GRACE``, default 1.5 s) gives
            the daemon time to: detect the interrupt (next 200 ms poll) →
            call _kill_process (SIGTERM + 1 s wait + SIGKILL if needed) →
            return from _wait_for_process.  ``time.sleep`` releases the
            GIL so the daemon actually runs during the window.

            Guarded ``logger.debug``: CPython's ``logging`` module is not
            reentrant-safe.  ``Logger.isEnabledFor`` caches level results
            in ``Logger._cache``; under shutdown races the cache can be
            cleared (``_clear_cache``) or mid-mutation when the signal
            fires, raising ``KeyError: <level_int>`` (e.g. ``KeyError: 10``
            for DEBUG) inside the handler.  That KeyError then escapes
            before ``raise KeyboardInterrupt()`` can fire, which bypasses
            prompt_toolkit's normal interrupt unwind and surfaces as the
            EIO cascade from issue #13710.  Wrap the log in a bare
            ``try/except`` so the handler can never raise through it.
            """
            try:
                logger.debug("Received signal %s, triggering graceful shutdown", signum)
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )  # never let logging raise from a signal handler (#13710 regression)
            try:
                if getattr(self, "agent", None) and getattr(self, "_agent_running", False):
                    self.agent.interrupt(f"received signal {signum}")
                    try:
                        _grace = float(os.getenv("ReYMeN_SIGTERM_GRACE", "1.5"))
                    except (TypeError, ValueError):
                        _grace = 1.5
                    if _grace > 0:
                        time.sleep(_grace)
            except Exception as _e:
                __import__("logging").getLogger(__name__).warning(
                    "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                )  # never block signal handling
            # Prefer a clean prompt_toolkit exit over `raise KeyboardInterrupt()`.
            # Raising KBI from a signal handler unwinds into whatever Python
            # frame the interpreter happens to be running — typically an
            # `await asyncio.sleep()` inside prompt_toolkit's
            # `_poll_output_size` coroutine.  The KBI becomes a Task
            # exception, prompt_toolkit's `_handle_exception` prints
            # "Unhandled exception in event loop" + the full traceback, and
            # parks the terminal on "Press ENTER to continue..." (#13710
            # variant — same root cause, different surface).
            #
            # `app.exit()` scheduled via `call_soon_threadsafe` lets the
            # event loop unwind normally; `app.run()` returns and our
            # existing `except (EOFError, KeyboardInterrupt, BrokenPipeError)`
            # block at the bottom of the input loop handles the rest.
            try:
                from prompt_toolkit.application.current import get_app_or_none
                _app = get_app_or_none()
                if _app is not None:
                    _loop = getattr(_app, "loop", None)
                    if _loop is not None:
                        _loop.call_soon_threadsafe(_app.exit)
                        return  # clean unwind — no traceback, no ENTER pause
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")
            raise KeyboardInterrupt()  # fallback for non-prompt_toolkit contexts
        
        try:
            import signal as _signal
            _signal.signal(_signal.SIGTERM, _signal_handler)
            if hasattr(_signal, 'SIGHUP'):
                _signal.signal(_signal.SIGHUP, _signal_handler)

            # Windows: install a SIGINT handler that absorbs the signal
            # instead of letting Python's default handler raise
            # KeyboardInterrupt in MainThread. Windows Terminal / Win32
            # delivers spurious CTRL_C_EVENT to the ReYMeN process when
            # child processes are spawned from background threads (agent
            # subprocess Popen path). The default Python SIGINT handler
            # would then unwind prompt_toolkit's app.run(), trigger
            # _run_cleanup mid-turn, and close browser sessions mid-open
            # — causing "Daemon process exited during startup" errors.
            #
            # The handler is a silent no-op. Real user Ctrl+C still works
            # because prompt_toolkit binds c-c at the TUI layer and never
            # reaches this OS-signal path. This matches how Claude Code
            # handles the same Windows quirk (cancellation is driven by
            # the TUI key handler, not by OS signals).
            #
            # POSIX: leave the default SIGINT handler alone. prompt_toolkit
            # installs its own handler there and it works as expected.
            if sys.platform == "win32":
                def _sigint_absorb(signum, frame):
                    # Absorb silently. Do NOT call agent.interrupt() here:
                    # Windows fires spurious CTRL_C_EVENT whenever a
                    # background thread spawns a .cmd subprocess, and
                    # interrupt() would inject a fake user message each
                    # time. Real user Ctrl+C routes through prompt_toolkit's
                    # own c-c key binding at the TUI layer (same pattern as
                    # Claude Code's Windows handling).
                    return
                _signal.signal(_signal.SIGINT, _sigint_absorb)
        except Exception as _e:
            __import__("logging").getLogger(__name__).warning(
                "[SessizExcept] %%s: %%s", type(_e).__name__, _e
            )  # Signal handlers may fail in restricted environments
        
        # Install a custom asyncio exception handler that suppresses the
        # "Event loop is closed" RuntimeError from httpx transport cleanup
        # and the "0 is not registered" KeyError from broken stdin (#6393).
        # The RuntimeError fix is defense-in-depth — the primary fix is
        # neuter_async_httpx_del which disables __del__ entirely.  The
        # KeyError fix handles macOS + uv-managed Python environments where
        # fd 0 is not reliably available to the asyncio selector.
        def _suppress_closed_loop_errors(loop, context):
            exc = context.get("exception")
            if isinstance(exc, RuntimeError) and "Event loop is closed" in str(exc):
                return  # silently suppress
            if isinstance(exc, KeyError) and "is not registered" in str(exc):
                return  # suppress selector registration failures (#6393)
            if isinstance(exc, OSError) and getattr(exc, "errno", None) == errno.EIO:
                return  # suppress I/O errors from broken stdout on interrupt (#13710)
            # Fall back to default handler for everything else
            loop.default_exception_handler(context)

        # Validate stdin before launching prompt_toolkit — on macOS with
        # uv-managed Python, fd 0 can be invalid or unregisterable with the
        # asyncio selector, causing "KeyError: '0 is not registered'" (#6393).
        try:
            os.fstat(0)
        except OSError:
            print(
                "Error: stdin (fd 0) is not available.\n"
                "This can happen with certain Python installations (e.g. uv-managed cPython on macOS).\n"
                "Try reinstalling Python via pyenv or Homebrew, then re-run: ReYMeN setup"
            )
            _run_cleanup()
            self._print_exit_summary()
            return

        # On macOS with uv-managed Python, kqueue's selector cannot register
        # fd 0, raising OSError(EINVAL) from kqueue.control() when prompt_toolkit
        # calls loop.add_reader (#6393). Probe kqueue and, if it can't watch
        # stdin, switch to a SelectSelector-backed event loop policy.
        if sys.platform == "darwin":
            try:
                import selectors as _selectors
                if hasattr(_selectors, "KqueueSelector"):
                    _kq = _selectors.KqueueSelector()
                    try:
                        _kq.register(0, _selectors.EVENT_READ)
                        _kq.unregister(0)
                    finally:
                        _kq.close()
            except (OSError, ValueError, KeyError):
                import asyncio as _aio_probe
                import selectors as _selectors

                class _SelectEventLoopPolicy(_aio_probe.DefaultEventLoopPolicy):
                    def new_event_loop(self):
                        return _aio_probe.SelectorEventLoop(_selectors.SelectSelector())

                _aio_probe.set_event_loop_policy(_SelectEventLoopPolicy())

        # Run the application with patch_stdout for proper output handling
        try:
            with patch_stdout():
                # Set the custom handler on prompt_toolkit's event loop
                try:
                    import asyncio as _aio
                    # Use get_running_loop() to avoid DeprecationWarning on
                    # Python 3.10+ when called outside an async context.
                    _loop = _aio.get_running_loop()
                    _loop.set_exception_handler(_suppress_closed_loop_errors)
                except RuntimeError:
                    pass  # No running loop -- nothing to patch
                except Exception:
                    logger.warning("[fix_01_sessiz_except] Exception")
                app.run()
        except (EOFError, KeyboardInterrupt, BrokenPipeError):
            logger.warning("[fix_01_sessiz_except] Exception")
        except (KeyError, OSError) as _stdin_err:
            # Catch selector registration failures from broken stdin (#6393)
            # and I/O errors from broken stdout during interrupt (#13710).
            _errno = getattr(_stdin_err, "errno", None) if isinstance(_stdin_err, OSError) else None
            _msg = str(_stdin_err)
            if _errno == errno.EIO:
                pass  # suppress broken-stdout I/O errors on interrupt (#13710)
            elif (
                _errno in {errno.EINVAL, errno.EBADF}
                or "is not registered" in _msg
                or "Bad file descriptor" in _msg
                or "Invalid argument" in _msg
            ):
                print(
                    f"\nError: stdin is not usable ({_stdin_err}).\n"
                    "This can happen with certain Python installations (e.g. uv-managed cPython on macOS)\n"
                    "where kqueue cannot register fd 0.\n"
                    "Try reinstalling Python via pyenv or Homebrew, then re-run: ReYMeN setup"
                )
            else:
                raise
        finally:
            self._should_exit = True
            # Interrupt the agent immediately so its daemon thread stops making
            # API calls and exits promptly (agent_thread is daemon, so the
            # process will exit once the main thread finishes, but interrupting
            # avoids wasted API calls and lets run_conversation clean up).
            if self.agent and getattr(self, '_agent_running', False):
                try:
                    self.agent.interrupt()
                except Exception:
                    logger.warning("[fix_01_sessiz_except] Exception")
            # Shut down voice recorder (release persistent audio stream)
            if hasattr(self, '_voice_recorder') and self._voice_recorder:
                try:
                    self._voice_recorder.shutdown()
                except Exception:
                    logger.warning("[fix_01_sessiz_except] Exception")
                self._voice_recorder = None
            # Clean up old temp voice recordings
            try:
                from tools.voice_mode import cleanup_temp_recordings
                cleanup_temp_recordings()
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")
            # Unregister callbacks to avoid dangling references
            set_sudo_password_callback(None)
            set_approval_callback(None)
            set_secret_capture_callback(None)
            # Close session in SQLite
            if hasattr(self, '_session_db') and self._session_db and self.agent:
                try:
                    self._session_db.end_session(self.agent.session_id, "cli_close")
                except (Exception, KeyboardInterrupt) as e:
                    logger.debug("Could not close session in DB: %s", e)
                # /exit --delete: also remove the current session's transcripts
                # and SQLite history. Ported from google-gemini/gemini-cli#19332.
                if getattr(self, '_delete_session_on_exit', False):
                    try:
                        from reymen.sistem.ReYMeN_constants import get_reymen_home as _ghh
                        _sessions_dir = _ghh() / "sessions"
                        _sid = self.agent.session_id
                        if self._session_db.delete_session(_sid, sessions_dir=_sessions_dir):
                            _cprint(f"  {_DIM}✓ Session {_escape(_sid)} deleted{_RST}")
                        else:
                            _cprint(f"  {_DIM}✗ Session {_escape(_sid)} not found for deletion{_RST}")
                    except (Exception, KeyboardInterrupt) as e:
                        logger.debug("Could not delete session on exit: %s", e)
            # Plugin hook: on_session_end — safety net for interrupted exits.
            # run_conversation() already fires this per-turn on normal completion,
            # so only fire here if the agent was mid-turn (_agent_running) when
            # the exit occurred, meaning run_conversation's hook didn't fire.
            if self.agent and getattr(self, '_agent_running', False):
                try:
                    from reymen.reymen_cli.plugins import invoke_hook as _invoke_hook
                    _invoke_hook(
                        "on_session_end",
                        session_id=self.agent.session_id,
                        completed=False,
                        interrupted=True,
                        model=getattr(self.agent, 'model', None),
                        platform=getattr(self.agent, 'platform', None) or "cli",
                    )
                except Exception:
                    logger.warning("[fix_01_sessiz_except] Exception")
            _run_cleanup()
            self._print_exit_summary()

        # Deferred relaunch: /update sets _pending_relaunch so the exec
        # happens here — after prompt_toolkit has exited and fully restored
        # terminal modes — rather than from the background process_loop
        # thread (which would skip terminal cleanup on POSIX and only exit
        # the worker thread on Windows).
        if getattr(self, '_pending_relaunch', None):
            from reymen.reymen_cli.relaunch import relaunch
            relaunch(self._pending_relaunch, preserve_inherited=False)


# ============================================================================
# Main Entry Point
# ============================================================================
