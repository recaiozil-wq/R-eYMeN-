#!/usr/bin/env python3
"""
ReYMeN Agent CLI - Interactive Terminal Interface (Split Wrapper)

This module re-exports ReYMeNCLI from cli_main.py and provides
the CLI entry point. The actual class implementation is split
across mixin modules in reymen/sistem/cli_mixin_*.py.
"""

import logging
import sys
from typing import Optional, Any, List, Dict, Tuple
logger = logging.getLogger(__name__)

# Import the actual implementation
from src.reymen.sistem.cli_main import ReYMeNCLI

def main(
    query: str = None,
    q: str = None,
    image: str = None,
    toolsets: str = None,
    skills: str | list[str] | tuple[str, ...] = None,
    model: str = None,
    provider: str = None,
    api_key: str = None,
    base_url: str = None,
    max_turns: int = None,
    verbose: Optional[bool] = None,
    quiet: bool = False,
    compact: bool = False,
    list_tools: bool = False,
    list_toolsets: bool = False,
    gateway: bool = False,
    resume: str = None,
    worktree: bool = False,
    w: bool = False,
    checkpoints: bool = False,
    pass_session_id: bool = False,
    ignore_user_config: bool = False,
    ignore_rules: bool = False,
    yolo: bool = False,
):
    """
    ReYMeN Agent CLI - Interactive AI Assistant
    
    Args:
        query: Single query to execute (then exit). Alias: -q
        q: Shorthand for --query
        image: Optional local image path to attach to a single query
        toolsets: Comma-separated list of toolsets to enable (e.g., "web,terminal")
        skills: Comma-separated or repeated list of skills to preload for the session
        model: Model to use (default: anthropic/claude-opus-4-20250514)
        provider: Inference provider ("auto", "openrouter", "nous", "openai-codex", "zai", "kimi-coding", "minimax", "minimax-cn")
        api_key: API key for authentication
        base_url: Base URL for the API
        max_turns: Maximum tool-calling iterations (default: 60)
        verbose: Enable verbose logging
        compact: Use compact display mode
        list_tools: List available tools and exit
        list_toolsets: List available toolsets and exit
        yolo: Enable YOLO mode — skip all dangerous command approval prompts
        resume: Resume a previous session by its ID (e.g., 20260225_143052_a1b2c3)
        worktree: Run in an isolated git worktree (for parallel agents). Alias: -w
        w: Shorthand for --worktree
    
    Examples:
        python cli.py                            # Start interactive mode
        python cli.py --toolsets web,terminal    # Use specific toolsets
        python cli.py --skills ReYMeN-agent-dev,github-auth
        python cli.py -q "What is Python?"       # Single query mode
        python cli.py -q "Describe this" --image ~/storage/shared/Pictures/cat.png
        python cli.py --list-tools               # List tools and exit
        python cli.py --resume 20260225_143052_a1b2c3  # Resume session
        python cli.py -w                         # Start in isolated git worktree
        python cli.py -w -q "Fix issue #123"     # Single query in worktree
    """
    global _active_worktree

    # Force UTF-8 stdio on Windows before any banner/print() runs — the
    # Rich console prints Unicode box-drawing characters that would
    # UnicodeEncodeError on cp1252.  No-op on Linux/macOS.
    try:
        from ReYMeN_cli.stdio import configure_windows_stdio
        configure_windows_stdio()
    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")

    # Signal to terminal_tool that we're in interactive mode
    # This enables interactive sudo password prompts with timeout
    os.environ["ReYMeN_INTERACTIVE"] = "1"

    # --yolo flag: tum tehlikeli komut onaylarini atla
    if yolo:
        os.environ["REYMEN_YOLO_MODE"] = "1"
    
    # approvals.mode = off → YOLO modu (config)
    if not os.environ.get("REYMEN_YOLO_MODE"):
        try:
            from ReYMeN_cli.config import load_config as _load_reymen_config
            _cfg = _load_reymen_config()
            if isinstance(_cfg, dict):
                _approvals = _cfg.get("approvals", {}) or {}
                if _approvals.get("mode") in ("off", "yolo", "dangerous"):
                    os.environ["REYMEN_YOLO_MODE"] = "1"
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")
    
    # Handle gateway mode (messaging + cron)
    if gateway:
        import asyncio
        from gateway.run import start_gateway
        print("Starting ReYMeN Gateway (messaging platforms)...")
        asyncio.run(start_gateway())
        return

    # Skip worktree for list commands (they exit immediately)
    if not list_tools and not list_toolsets:
        # ── Git worktree isolation (#652) ──
        # Create an isolated worktree so this agent instance doesn't collide
        # with other agents working on the same repo.
        use_worktree = worktree or w or CLI_CONFIG.get("worktree", False)
        wt_info = None
        if use_worktree:
            # Prune stale worktrees from crashed/killed sessions
            _repo = _git_repo_root()
            if _repo:
                _prune_stale_worktrees(_repo)
            wt_info = _setup_worktree()
            if wt_info:
                _active_worktree = wt_info
                os.environ["TERMINAL_CWD"] = wt_info["path"]
                atexit.register(_cleanup_worktree, wt_info)
            else:
                # Worktree was explicitly requested but setup failed —
                # don't silently run without isolation.
                return
    else:
        wt_info = None
    
    # Handle query shorthand
    query = query or q
    
    # Parse toolsets - handle both string and tuple/list inputs
    # Default to ReYMeN-cli toolset which includes cronjob management tools
    toolsets_list = None
    if toolsets:
        if isinstance(toolsets, str):
            toolsets_list = [t.strip() for t in toolsets.split(",")]
        elif isinstance(toolsets, (list, tuple)):
            # Fire may pass multiple --toolsets as a tuple
            toolsets_list = []
            for t in toolsets:
                if isinstance(t, str):
                    toolsets_list.extend([x.strip() for x in t.split(",")])
                else:
                    toolsets_list.append(str(t))
    else:
        # Use the shared resolver so MCP servers are included at runtime
        from ReYMeN_cli.tools_config import _get_platform_tools
        toolsets_list = sorted(_get_platform_tools(CLI_CONFIG, "cli"))
    
    parsed_skills = _parse_skills_argument(skills)

    # Create CLI instance
    cli = ReYMeNCLI(
        model=model,
        toolsets=toolsets_list,
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        max_turns=max_turns,
        verbose=verbose,
        compact=compact,
        resume=resume,
        checkpoints=checkpoints,
        pass_session_id=pass_session_id,
        ignore_rules=ignore_rules,
    )

    if parsed_skills:
        skills_prompt, loaded_skills, missing_skills = build_preloaded_skills_prompt(
            parsed_skills,
            task_id=cli.session_id,
        )
        if missing_skills:
            missing_display = ", ".join(missing_skills)
            raise ValueError(f"Unknown skill(s): {missing_display}")
        if skills_prompt:
            cli.system_prompt = "\n\n".join(
                part for part in (cli.system_prompt, skills_prompt) if part
            ).strip()
            cli.preloaded_skills = loaded_skills

    # Inject worktree context into agent's system prompt
    if wt_info:
        wt_note = (
            f"\n\n[System note: You are working in an isolated git worktree at "
            f"{wt_info['path']}. Your branch is `{wt_info['branch']}`. "
            f"Changes here do not affect the main working tree or other agents. "
            f"Remember to commit and push your changes, and create a PR if appropriate. "
            f"The original repo is at {wt_info['repo_root']}.]"
        )
        cli.system_prompt = (cli.system_prompt or "") + wt_note
    
    # Handle list commands (don't init agent for these)
    if list_tools:
        cli.show_banner()
        cli.show_tools()
        sys.exit(0)
    
    if list_toolsets:
        cli.show_banner()
        cli.show_toolsets()
        sys.exit(0)
    
    # Register cleanup for single-query mode (interactive mode registers in run())
    atexit.register(_run_cleanup)

    # Also install signal handlers in single-query / `-q` mode.  Interactive
    # mode registers its own inside ReYMeNCLI.run(), but `-q` runs
    # cli.agent.run_conversation() below and AIAgent spawns worker threads
    # for tools — so when SIGTERM arrives on the main thread, raising
    # KeyboardInterrupt only unwinds the main thread, not the worker
    # running _wait_for_process.  Python then exits, the child subprocess
    # (spawned with os.setsid, its own process group) is reparented to
    # init and keeps running as an orphan.
    #
    # Fix: route SIGTERM/SIGHUP through agent.interrupt() which sets the
    # per-thread interrupt flag the worker's poll loop checks every 200 ms.
    # Give the worker a grace window to call _kill_process (SIGTERM to the
    # process group, then SIGKILL after 1 s), then raise KeyboardInterrupt
    # so main unwinds normally.  ReYMeN_SIGTERM_GRACE overrides the 1.5 s
    # default for debugging.
    def _signal_handler_q(signum, frame):
        logger.debug("Received signal %s in single-query mode", signum)
        try:
            _agent = getattr(cli, "agent", None)
            if _agent is not None:
                _agent.interrupt(f"received signal {signum}")
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
        # Kanban worker exit path (#28181): SIGTERM hits a dispatcher-spawned
        # worker that's likely in a non-daemon thread waiting on a child
        # subprocess in _wait_for_process. Raising KeyboardInterrupt only
        # unwinds the main thread; the worker thread keeps running, the
        # process gets reparented to init, and the dispatcher's _pid_alive
        # check returns True forever — task stuck in 'running' indefinitely.
        # Skip the controlled-unwind dance and call os._exit(0) so the kernel
        # reclaims the PID immediately and detect_crashed_workers can reclaim
        # the stale claim on the next tick. Flush logging + stdout/stderr
        # first so the final debug trace isn't lost; SIGALRM deadman guards
        # the flush against any rare blocking-I/O case (the reporter measured
        # flush in <1ms; the alarm is a failsafe, not the common path).
        if os.environ.get("ReYMeN_KANBAN_TASK"):
            try:
                import signal as _sig_mod
                if hasattr(_sig_mod, "SIGALRM"):
                    # Cancel any pre-existing alarm to avoid colliding with
                    # caller-installed timers.
                    _sig_mod.signal(_sig_mod.SIGALRM, lambda *_: os._exit(0))
                    _sig_mod.alarm(2)
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")
            try:
                import logging as _lg
                _lg.shutdown()
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")
            for _stream in (sys.stdout, sys.stderr):
                try:
                    _stream.flush()
                except Exception:
                    logger.warning("[fix_01_sessiz_except] Exception")
            os._exit(0)
        raise KeyboardInterrupt()
    try:
        import signal as _signal
        _signal.signal(_signal.SIGTERM, _signal_handler_q)
        if hasattr(_signal, "SIGHUP"):
            _signal.signal(_signal.SIGHUP, _signal_handler_q)
    except Exception as _e:
        __import__("logging").getLogger(__name__).warning(
            "[SessizExcept] %%s: %%s", type(_e).__name__, _e
        )  # signal handler may fail in restricted environments
    
    # Handle single query mode
    if query or image:
        query, single_query_images = _collect_query_images(query, image)
        # Kanban workers spawn with ``ReYMeN chat -q "work kanban task <id>"``;
        # the actual task description lives in the task body. Mirror the
        # gateway/CLI behaviour for inbound images by scanning the body for
        # local image paths and http(s) image URLs and attaching them to the
        # worker's first turn. Without this, users who paste a screenshot
        # path or URL into a kanban task body never get it routed to the
        # model's vision input.
        single_query_image_urls: list[str] = []
        _kanban_task_id = os.environ.get("ReYMeN_KANBAN_TASK", "").strip()
        if _kanban_task_id:
            try:
                from ReYMeN_cli import kanban_db as _kb
                from agent.image_routing import extract_image_refs as _extract_refs

                _conn = _kb.connect()
                try:
                    _task = _kb.get_task(_conn, _kanban_task_id)
                finally:
                    try:
                        _conn.close()
                    except Exception:
                        logger.warning("[fix_01_sessiz_except] Exception")
                _body = getattr(_task, "body", "") if _task is not None else ""
                if _body:
                    _kb_paths, _kb_urls = _extract_refs(_body)
                    if _kb_paths:
                        # Dedupe against any --image the user already passed.
                        _seen = {str(p) for p in single_query_images}
                        for _p in _kb_paths:
                            if _p not in _seen:
                                _seen.add(_p)
                                single_query_images.append(Path(_p))
                    if _kb_urls:
                        single_query_image_urls.extend(_kb_urls)
            except Exception as _exc:
                # Best-effort enrichment; never block worker startup on it.
                logger.debug("kanban image-ref extraction failed: %s", _exc)
        if quiet:
            # Quiet mode: suppress banner, spinner, tool previews.
            # Only print the final response and parseable session info.
            cli.tool_progress_mode = "off"
            if cli._ensure_runtime_credentials():
                effective_query: Any = query
                if single_query_images or single_query_image_urls:
                    # Honour the same image-routing decision used by the
                    # interactive path. With a vision-capable model (incl.
                    # custom-provider models declared via
                    # `model.supports_vision: true`), attach images natively
                    # as image_url content parts. Otherwise fall back to the
                    # text-pipeline (vision_analyze pre-description).
                    _img_mode = "text"
                    _build_parts = None
                    try:
                        from agent.image_routing import (
                            build_native_content_parts as _build_parts,  # noqa: F811
                        )
                        from agent.image_routing import decide_image_input_mode
                        from ReYMeN_cli.config import load_config

                        _img_mode = decide_image_input_mode(
                            (cli.provider or "").strip(),
                            (cli.model or "").strip(),
                            load_config(),
                        )
                    except Exception:
                        _img_mode = "text"

                    if _img_mode == "native" and _build_parts is not None:
                        try:
                            _parts, _skipped = _build_parts(
                                query if isinstance(query, str) else "",
                                [str(p) for p in single_query_images],
                                image_urls=list(single_query_image_urls) or None,
                            )
                            if any(p.get("type") == "image_url" for p in _parts):
                                effective_query = _parts
                            else:
                                # All images unreadable — text fallback.
                                # ``_preprocess_images_with_vision`` only knows
                                # about local files; URLs would be lost there,
                                # so keep the original query text intact when
                                # only URLs were supplied.
                                if single_query_images:
                                    effective_query = cli._preprocess_images_with_vision(
                                        query, single_query_images, announce=False,
                                    )
                        except Exception:
                            if single_query_images:
                                effective_query = cli._preprocess_images_with_vision(
                                    query, single_query_images, announce=False,
                                )
                    elif single_query_images:
                        effective_query = cli._preprocess_images_with_vision(
                            query,
                            single_query_images,
                            announce=False,
                        )
                turn_route = cli._resolve_turn_agent_config(effective_query)
                if turn_route["signature"] != cli._active_agent_route_signature:
                    cli.agent = None
                if cli._init_agent(
                    model_override=turn_route["model"],
                    runtime_override=turn_route["runtime"],
                    request_overrides=turn_route.get("request_overrides"),
                ):
                    cli.agent.quiet_mode = True
                    cli.agent.suppress_status_output = True
                    # Suppress streaming display callbacks so stdout stays
                    # machine-readable (no styled "ReYMeN" box, no tool-gen
                    # status lines).  The response is printed once below.
                    cli.agent.stream_delta_callback = None
                    cli.agent.tool_gen_callback = None
                    result = cli.agent.run_conversation(
                        user_message=effective_query,
                        conversation_history=cli.conversation_history,
                    )
                    # Sync session_id if mid-run compression created a
                    # continuation session. The exit line below reports
                    # session_id to stderr for automation wrappers; without
                    # this sync it would point at the ended parent.
                    if (
                        getattr(cli.agent, "session_id", None)
                        and cli.agent.session_id != cli.session_id
                    ):
                        cli.session_id = cli.agent.session_id
                    response = result.get("final_response", "") if isinstance(result, dict) else str(result)
                    # Surface backend errors that produced no visible output
                    # (e.g. invalid model slug → provider 4xx). Mirrors the
                    # interactive CLI path. Write to stderr so piped stdout
                    # stays clean for automation wrappers.
                    if (
                        not response
                        and isinstance(result, dict)
                        and result.get("error")
                        and (result.get("failed") or result.get("partial"))
                    ):
                        print(f"Error: {result['error']}", file=sys.stderr)
                    elif response:
                        print(response)

                    # Kanban goal-loop mode: a worker spawned for a
                    # goal_mode card keeps working in THIS session until an
                    # auxiliary judge agrees the card is done, the worker
                    # terminates the task itself, or the turn budget runs
                    # out (→ sticky block). Gated on the env vars the
                    # dispatcher sets in `_default_spawn`; a no-op for every
                    # normal worker and every non-kanban `-q` run.
                    if os.environ.get("ReYMeN_KANBAN_GOAL_MODE") == "1":
                        try:
                            _run_kanban_goal_loop_q(cli, response)
                        except Exception as _goal_exc:
                            logger.debug("kanban goal loop failed: %s", _goal_exc)

                    # Session ID goes to stderr so piped stdout is clean.
                    print(f"\nsession_id: {cli.session_id}", file=sys.stderr)
                    
                    # Ensure proper exit code for automation wrappers
                    sys.exit(1 if isinstance(result, dict) and result.get("failed") else 0)
            
            # Exit with error code if credentials or agent init fails
            sys.exit(1)
        else:
            # Single-query mode (`ReYMeN chat -q "…"`): skip the welcome
            # banner. Building the banner takes ~420 ms on cold start —
            # ~200 ms of that is the version-update check, the rest is
            # toolset / skill enumeration and Rich panel rendering. None
            # of that is useful for a one-shot query: the user already
            # picked the prompt, doesn't need a toolset reference, and
            # gets the session ID + resume hint from
            # ``_print_exit_summary()`` after the response prints.
            #
            # The fully-quiet ``-Q`` / ``--quiet`` machine-readable path
            # above was already banner-free; this brings the human-
            # facing single-query path in line so all non-interactive
            # invocations are fast.
            _query_label = query or ("[image attached]" if single_query_images else "")
            if _query_label:
                cli.console.print(f"[bold blue]Query:[/] {_query_label}")
            # Surface security advisories before the agent runs — short
            # banner, doesn't depend on the welcome banner being shown.
            cli._show_security_advisories()
            cli.chat(query, images=single_query_images or None)
            cli._print_exit_summary()
        return
    
    # Run interactive mode
    cli.run()

if __name__ == "__main__":
    import fire

    fire.Fire(main)
