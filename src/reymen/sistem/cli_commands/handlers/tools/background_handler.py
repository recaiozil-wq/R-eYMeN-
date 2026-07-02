"""_handle_background_command handler."""

import logging
import sys
import threading
import time
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


def _handle_background_command(cli, cmd: str):
    """Handle /background <prompt> — run a prompt in a separate background session.

    Spawns a new AIAgent in a background thread with its own session.
    When it completes, prints the result to the CLI without modifying
    the active session's conversation history.
    """
    from reymen.sistem.cli_display import _cprint, _accent_hex, _maybe_remap_for_light_mode, _render_final_assistant_content
    from reymen.sistem.cli_stream import ChatConsole
    from reymen.sistem.run_agent import AIAgent
    from rich.markup import escape as _escape
    from rich.panel import Panel
    import rich.box as rich_box
    from ReYMeN_cli.callbacks import (
        set_sudo_password_callback,
        set_approval_callback,
        set_secret_capture_callback,
    )

    parts = cmd.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        _cprint("  Usage: /background <prompt>")
        _cprint("  Example: /background Summarize the top HN stories today")
        _cprint("  The task runs in a separate session and results display here when done.")
        return

    prompt = parts[1].strip()
    cli._background_task_counter += 1
    task_num = cli._background_task_counter
    task_id = f"bg_{datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:6]}"

    # Make sure we have valid credentials
    if not cli._ensure_runtime_credentials():
        _cprint("  (>_<) Cannot start background task: no valid credentials.")
        return

    _cprint(f"  🔄 Background task #{task_num} started: \"{prompt[:60]}{'...' if len(prompt) > 60 else ''}\"")
    _cprint(f"  Task ID: {task_id}")
    _cprint("  You can continue chatting — results will appear when done.\n")

    turn_route = cli._resolve_turn_agent_config(prompt)

    def run_background():
        set_sudo_password_callback(cli._sudo_password_callback)
        set_approval_callback(cli._approval_callback)
        try:
            set_secret_capture_callback(cli._secret_capture_callback)
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")
        try:
            bg_agent = AIAgent(
                model=turn_route["model"],
                api_key=turn_route["runtime"].get("api_key"),
                base_url=turn_route["runtime"].get("base_url"),
                provider=turn_route["runtime"].get("provider"),
                api_mode=turn_route["runtime"].get("api_mode"),
                acp_command=turn_route["runtime"].get("command"),
                acp_args=turn_route["runtime"].get("args"),
                max_iterations=cli.max_turns,
                enabled_toolsets=cli.enabled_toolsets,
                quiet_mode=True,
                verbose_logging=False,
                session_id=task_id,
                platform="cli",
                session_db=cli._session_db,
                reasoning_config=cli.reasoning_config,
                service_tier=cli.service_tier,
                request_overrides=turn_route.get("request_overrides"),
                providers_allowed=cli._providers_only,
                providers_ignored=cli._providers_ignore,
                providers_order=cli._providers_order,
                provider_sort=cli._provider_sort,
                provider_require_parameters=cli._provider_require_params,
                provider_data_collection=cli._provider_data_collection,
                openrouter_min_coding_score=cli._openrouter_min_coding_score,
                fallback_model=cli._fallback_model,
            )
            # Silence raw spinner; route thinking through TUI widget when no foreground agent is active.
            bg_agent._print_fn = lambda *_a, **_kw: None

            def _bg_thinking(text: str) -> None:
                # Concurrent bg tasks may race on _spinner_text; acceptable for best-effort UI.
                if not cli._agent_running:
                    cli._spinner_text = text
                    if cli._app:
                        cli._app.invalidate()

            bg_agent.thinking_callback = _bg_thinking

            result = bg_agent.run_conversation(
                user_message=prompt,
                task_id=task_id,
            )

            response = result.get("final_response", "") if result else ""
            if not response and result and result.get("error"):
                response = f"Error: {result['error']}"

            # Display result in the CLI (thread-safe via patch_stdout).
            # Force a TUI refresh first so spinner/status bar don't overlap
            # with the output (fixes #2718).
            if cli._app:
                cli._app.invalidate()
                time.sleep(0.05)  # brief pause for refresh
            print()
            ChatConsole().print(f"[{_accent_hex()}]{'─' * 40}[/]")
            _cprint(f"  ✅ Background task #{task_num} complete")
            _cprint(f"  Prompt: \"{prompt[:60]}{'...' if len(prompt) > 60 else ''}\"")
            ChatConsole().print(f"[{_accent_hex()}]{'─' * 40}[/]")
            if response:
                try:
                    from reymen.reymen_cli.skin_engine import get_active_skin
                    _skin = get_active_skin()
                    label = _skin.get_branding("response_label", "⚕ ReYMeN")
                    _resp_color = _maybe_remap_for_light_mode(_skin.get_color("response_border", "#CD7F32"))
                    _resp_text = _maybe_remap_for_light_mode(_skin.get_color("banner_text", "#FFF8DC"))
                except Exception:
                    label = "⚕ ReYMeN"
                    _resp_color = "#CD7F32"
                    _resp_text = "#FFF8DC"

                _chat_console = ChatConsole()
                _scroll_width = cli._scrollback_box_width()
                _chat_console.print(Panel(
                    _render_final_assistant_content(response, mode=cli.final_response_markdown),
                    title=f"[{_resp_color} bold]{label} (background #{task_num})[/]",
                    title_align="left",
                    border_style=_resp_color,
                    style=_resp_text,
                    box=rich_box.HORIZONTALS,
                    padding=(1, 4),
                    width=_scroll_width,
                ))
            else:
                _cprint("  (No response generated)")

            # Play bell if enabled
            if cli.bell_on_complete:
                sys.stdout.write("\a")
                sys.stdout.flush()

        except Exception as e:
            # Same TUI refresh pattern as success path (#2718)
            if cli._app:
                cli._app.invalidate()
                time.sleep(0.05)
            print()
            _cprint(f"  ❌ Background task #{task_num} failed: {e}")
        finally:
            try:
                set_sudo_password_callback(None)
                set_approval_callback(None)
                set_secret_capture_callback(None)
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")
            cli._background_tasks.pop(task_id, None)
            # Clear spinner only if no foreground agent owns it
            if not cli._agent_running:
                cli._spinner_text = ""
            if cli._app:
                cli._invalidate(min_interval=0)

    thread = threading.Thread(target=run_background, daemon=True, name=f"bg-task-{task_id}")
    cli._background_tasks[task_id] = thread
    thread.start()
