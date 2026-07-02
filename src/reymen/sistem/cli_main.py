import json
import shutil
import textwrap
from functools import partial
from pathlib import Path
from datetime import datetime
from typing import List
from typing import Dict
from typing import Optional
from typing import Any
from contextlib import contextmanager

from src.reymen.sistem.cli_mixin_display import MixinDisplay
from src.reymen.sistem.cli_mixin_stream import MixinStream
from src.reymen.sistem.cli_mixin_voice import MixinVoice
from src.reymen.sistem.cli_mixin_approval import MixinApproval
from src.reymen.sistem.cli_mixin_commands import MixinCommands
from src.reymen.sistem.cli_mixin_core import MixinCore
from src.reymen.sistem.cli_mixin_fileops import MixinFileOps
from src.reymen.sistem.cli_mixin_media import MixinMedia
from src.reymen.sistem.cli_mixin_agentsettings import MixinAgentSettings
from src.reymen.sistem.cli_mixin_browser import MixinBrowser
from src.reymen.sistem.cli_mixin_goals import MixinGoals
from src.reymen.sistem.cli_mixin_skillstools import MixinSkillsTools
from src.reymen.sistem.cli_mixin_ui import MixinUI

# Extracted CLI modules (Phase 2 - TUI and Agent mixins)
from src.reymen.sistem.cli_tui import TUIMixin
from src.reymen.sistem.cli_agent import AgentMixin

# Extracted CLI modules (Phase 2 - Session mixin)
from src.reymen.sistem.cli_session import SessionMixin


# Initialize centralized logging early — agent.log + errors.log in ~/.ReYMeN/logs/.
# This ensures CLI sessions produce a log trail even before AIAgent is instantiated.
try:
    from reymen.sistem.ReYMeN_logging import setup_logging
    setup_logging(mode="cli")
except Exception as _e:
    __import__("logging").getLogger(__name__).warning(
        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
    )  # Logging setup is best-effort — don't crash the CLI

# Validate config structure early — print warnings before user hits cryptic errors
try:
    from reymen.reymen_cli.config import print_config_warnings
    print_config_warnings(sys.argv[1:] if len(sys.argv) > 1 else [])
except Exception:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("[fix_01_sessiz_except] Exception")

# Initialize the skin engine from config
try:
    from reymen.ReYMeN_cli.skin_engine import init_skin_from_config
    init_skin_from_config(CLI_CONFIG)
except Exception as _e:
    __import__("logging").getLogger(__name__).warning(
        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
    )  # Skin engine is optional — default skin used if unavailable

# Initialize tool preview length from config
try:
    from agent.display import set_tool_preview_max_len
    _tpl = CLI_CONFIG.get("display", {}).get("tool_preview_length", 0)
    set_tool_preview_max_len(int(_tpl) if _tpl else 0)
except Exception:
    logger.warning("[fix_01_sessiz_except] Exception")

# Neuter AsyncHttpxClientWrapper.__del__ before any AsyncOpenAI clients are
# created.  The SDK's __del__ schedules aclose() on asyncio.get_running_loop()
# which, during CLI idle time, finds prompt_toolkit's event loop and tries to
# close TCP transports bound to dead worker loops — producing
# "Event loop is closed" / "Press ENTER to continue..." errors.
#
# We install a sys.meta_path finder that defers the actual import + patch
# until ``openai._base_client`` is first loaded by the rest of the codebase.
# Eagerly importing it here (the old approach) cost ~166ms / ~30MB on every
# cold CLI start because openai's type tree (responses/*, graders/*) is huge.
# The finder approach pays nothing until the SDK is genuinely needed and
# still guarantees the patch is applied before any AsyncOpenAI instance can
# be constructed (the import-then-instantiate ordering is enforced by
# Python's import system).
try:
    import sys as _httpx_neuter_sys
    import importlib.util as _httpx_neuter_imp_util

    class _AsyncHttpxDelNeuter:
        """Defer ``AsyncHttpxClientWrapper.__del__`` neutering until import.

        Saves ~166ms on cold CLI start where openai is never used (e.g.
        ``ReYMeN --help`` paths inside the chat command flow).  See
        ``agent.auxiliary_client.neuter_async_httpx_del`` for full rationale
        on why ``__del__`` must be a no-op.
        """

        _armed = True

        def find_spec(self, fullname, path=None, target=None):
            if not self._armed or fullname != "openai._base_client":
                return None
            # Disarm before delegating so the recursive find_spec call
            # below doesn't loop through us.
            self._armed = False
            try:
                _httpx_neuter_sys.meta_path.remove(self)
            except ValueError:
                logger.warning("[fix_01_sessiz_except] ValueError")
            spec = _httpx_neuter_imp_util.find_spec(fullname)
            if spec is None or spec.loader is None:
                return None
            _orig_exec = spec.loader.exec_module

            def _patched_exec(module):
                _orig_exec(module)
                try:
                    cls = getattr(module, "AsyncHttpxClientWrapper", None)
                    if cls is not None:
                        cls.__del__ = lambda self: None  # type: ignore[assignment]
                except Exception:
                    logger.warning("[fix_01_sessiz_except] Exception")

            spec.loader.exec_module = _patched_exec  # type: ignore[method-assign]
            return spec

    _httpx_neuter_sys.meta_path.insert(0, _AsyncHttpxDelNeuter())
except Exception:
    logger.warning("[fix_01_sessiz_except] Exception")

from rich import box as rich_box
from rich.console import Console
from rich.markup import escape as _escape
from rich.panel import Panel
from rich.text import Text as _RichText

# Import agent and tool systems lazily. Bare interactive startup only needs the
# prompt; the full agent/tool registry is initialized on first use.
def AIAgent(*args, **kwargs):
    from reymen.sistem.run_agent import AIAgent as _AIAgent

    return _AIAgent(*args, **kwargs)


def get_tool_definitions(*args, **kwargs):
    from reymen.reymen_cli.mcp_startup import wait_for_mcp_discovery
    from reymen.sistem.model_tools import get_tool_definitions as _get_tool_definitions

    wait_for_mcp_discovery()
    return _get_tool_definitions(*args, **kwargs)


def get_toolset_for_tool(*args, **kwargs):
    from reymen.sistem.model_tools import get_toolset_for_tool as _get_toolset_for_tool

    return _get_toolset_for_tool(*args, **kwargs)

# Extracted CLI modules (Phase 3)
from src.reymen.cli.banner import build_welcome_banner
from src.reymen.cli.commands import SlashCommandCompleter, SlashCommandAutoSuggest

from src.reymen.sistem.cli_helpers import *
from src.reymen.sistem.cli_display import *
from src.reymen.sistem.cli_commands import *
from src.reymen.sistem.cli_auth import *
from src.reymen.sistem.cli_maintenance import *
from src.reymen.sistem.cli_stream import *


def get_all_toolsets(*args, **kwargs):
    from reymen.sistem.toolsets import get_all_toolsets as _get_all_toolsets

    return _get_all_toolsets(*args, **kwargs)


def get_toolset_info(*args, **kwargs):
    from reymen.sistem.toolsets import get_toolset_info as _get_toolset_info

    return _get_toolset_info(*args, **kwargs)


def validate_toolset(*args, **kwargs):
    from reymen.sistem.toolsets import validate_toolset as _validate_toolset

    return _validate_toolset(*args, **kwargs)



def _prepare_deferred_agent_startup() -> None:
    """Run Termux-deferred agent discovery before the first real agent turn."""
    global _deferred_agent_startup_done
    if _deferred_agent_startup_done:
        return
    if os.environ.get("ReYMeN_DEFER_AGENT_STARTUP") != "1":
        return
    _deferred_agent_startup_done = True
    _accept_hooks = os.environ.get("ReYMeN_ACCEPT_HOOKS", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    try:
        from reymen.reymen_cli.plugins import discover_plugins

        discover_plugins()
    except Exception:
        logger.warning(
            "plugin discovery failed at deferred CLI startup",
            exc_info=True,
        )
    try:
        from reymen.reymen_cli.mcp_startup import start_background_mcp_discovery

        start_background_mcp_discovery(
            logger=logger,
            thread_name="termux-cli-mcp-discovery",
        )
    except Exception:
        logger.debug(
            "MCP tool discovery failed at deferred CLI startup",
            exc_info=True,
        )
    try:
        from agent.shell_hooks import register_from_config
        from reymen.reymen_cli.config import load_config

        register_from_config(load_config(), accept_hooks=_accept_hooks)
    except Exception:
        logger.debug(
            "shell-hook registration failed at deferred CLI startup",
            exc_info=True,
        )

def _run_cleanup():
    """Run resource cleanup exactly once."""
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True

    try:
        _cleanup_all_terminals()
    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")
    try:
        _cleanup_all_browsers()
    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")
    try:
        from tools.mcp_tool import shutdown_mcp_servers
        shutdown_mcp_servers()
    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")
    # Close cached auxiliary LLM clients (sync + async) so that
    # AsyncHttpxClientWrapper.__del__ doesn't fire on a closed event loop
    # and trigger prompt_toolkit's "Press ENTER to continue..." handler.
    try:
        from agent.auxiliary_client import shutdown_cached_clients
        shutdown_cached_clients()
    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")
    # Shut down memory provider (on_session_end + shutdown_all) at actual
    # session boundary — NOT per-turn inside run_conversation().
    try:
        from reymen.reymen_cli.plugins import invoke_hook as _invoke_hook
        _invoke_hook("on_session_finalize", session_id=_active_agent_ref.session_id if _active_agent_ref else None, platform="cli")
    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")
    try:
        if _active_agent_ref and hasattr(_active_agent_ref, 'shutdown_memory_provider'):
            # Forward the agent's own transcript so memory providers'
            # ``on_session_end`` hooks see the real conversation instead of
            # an empty list (#15165). ``_session_messages`` is set on
            # ``AIAgent.__init__`` and refreshed every turn via
            # ``_persist_session``. Fall back to no-arg on test stubs /
            # partially-initialised agents where the attribute is missing.
            _session_msgs = getattr(_active_agent_ref, '_session_messages', None)
            if isinstance(_session_msgs, list):
                _active_agent_ref.shutdown_memory_provider(_session_msgs)
            else:
                _active_agent_ref.shutdown_memory_provider()
    except Exception:
        logger.warning("[fix_01_sessiz_except] Exception")


# =============================================================================
# Git Worktree Isolation (#652)
# =============================================================================

# Tracks the active worktree for cleanup on exit
_active_worktree: Optional[Dict[str, str]] = None



class ReYMeNCLI(TUIMixin, AgentMixin, SessionMixin, MixinDisplay, MixinStream, MixinVoice, MixinApproval, MixinCommands, MixinCore, MixinFileOps, MixinMedia, MixinAgentSettings, MixinBrowser, MixinGoals, MixinSkillsTools, MixinUI):
    """
    Interactive CLI for the ReYMeN Agent.
    
    Provides a REPL interface with rich formatting, command history,
    and tool execution capabilities.
    """
    
    def __init__(
        self,
        model: str = None,
        toolsets: List[str] = None,
        provider: str = None,
        api_key: str = None,
        base_url: str = None,
        max_turns: int = None,
        verbose: Optional[bool] = None,
        compact: bool = False,
        resume: str = None,
        checkpoints: bool = False,
        pass_session_id: bool = False,
        ignore_rules: bool = False,
    ):
        """
        Initialize the ReYMeN CLI.

        Args:
            model: Model to use (default: from env or claude-sonnet)
            toolsets: List of toolsets to enable (default: all)
            provider: Inference provider ("auto", "openrouter", "nous", "openai-codex", "zai", "kimi-coding", "minimax", "minimax-cn")
            api_key: API key (default: from environment)
            base_url: API base URL (default: OpenRouter)
            max_turns: Maximum tool-calling iterations shared with subagents (default: 90)
            verbose: Enable verbose logging
            compact: Use compact display mode
            resume: Session ID to resume (restores conversation history from SQLite)
            pass_session_id: Include the session ID in the agent's system prompt
        """
        # Initialize Rich console
        self.console = Console()
        self.config = CLI_CONFIG
        self.compact = compact if compact is not None else CLI_CONFIG["display"].get("compact", False)
        # tool_progress: "off", "new", "all", "verbose" (from config.yaml display section)
        # YAML 1.1 parses bare `off` as boolean False — normalise to string.
        _raw_tp = CLI_CONFIG["display"].get("tool_progress", "all")
        self.tool_progress_mode = "off" if _raw_tp is False else str(_raw_tp)
        # resume_display: "full" (show history) | "minimal" (one-liner only)
        self.resume_display = CLI_CONFIG["display"].get("resume_display", "full")
        # bell_on_complete: play terminal bell (\a) when agent finishes a response
        self.bell_on_complete = CLI_CONFIG["display"].get("bell_on_complete", False)
        # show_reasoning: display model thinking/reasoning before the response
        self.show_reasoning = CLI_CONFIG["display"].get("show_reasoning", False)
        _configure_output_history(
            enabled=CLI_CONFIG["display"].get("persistent_output", True),
            max_lines=CLI_CONFIG["display"].get("persistent_output_max_lines", 200),
        )
        # busy_input_mode: "interrupt" (Enter interrupts current run),
        # "queue" (Enter queues for next turn), or "steer" (Enter injects
        # mid-run via /steer, arriving after the next tool call).
        _bim = str(CLI_CONFIG["display"].get("busy_input_mode", "interrupt")).strip().lower()
        if _bim == "queue":
            self.busy_input_mode = "queue"
        elif _bim == "steer":
            self.busy_input_mode = "steer"
        else:
            self.busy_input_mode = "interrupt"

        # self.verbose ONLY controls global DEBUG logging (root logger level).
        # display.tool_progress="verbose" controls tool-call rendering (full args,
        # results, think blocks) and is independent — see _apply_logging_levels.
        # Coupling the two (PR #6a1aa420e) caused all module DEBUG logs to spew
        # to console whenever a user set tool_progress: verbose in config.
        self.verbose = bool(verbose) if verbose is not None else False
        
        # streaming: stream tokens to the terminal as they arrive (display.streaming in config.yaml)
        self.streaming_enabled = CLI_CONFIG["display"].get("streaming", False)
        # show_timestamps: prefix user and assistant labels with [HH:MM]
        self.show_timestamps = CLI_CONFIG["display"].get("timestamps", False)
        self.final_response_markdown = str(
            CLI_CONFIG["display"].get("final_response_markdown", "strip")
        ).strip().lower() or "strip"
        if self.final_response_markdown not in {"render", "strip", "raw"}:
            self.final_response_markdown = "strip"

        # Inline diff previews for write actions (display.inline_diffs in config.yaml)
        self._inline_diffs_enabled = CLI_CONFIG["display"].get("inline_diffs", True)

        # Submitted multiline user-message preview (display.user_message_preview in config.yaml)
        _ump = CLI_CONFIG["display"].get("user_message_preview", {})
        if not isinstance(_ump, dict):
            _ump = {}
        try:
            _ump_first_lines = int(_ump.get("first_lines", 2))
        except (TypeError, ValueError):
            _ump_first_lines = 2
        try:
            _ump_last_lines = int(_ump.get("last_lines", 2))
        except (TypeError, ValueError):
            _ump_last_lines = 2
        self.user_message_preview_first_lines = max(1, _ump_first_lines)
        self.user_message_preview_last_lines = max(0, _ump_last_lines)

        # Streaming display state
        self._stream_buf = ""        # Partial line buffer for line-buffered rendering
        self._stream_started = False  # True once first delta arrives
        self._stream_box_opened = False  # True once the response box header is printed
        self._reasoning_preview_buf = ""  # Coalesce tiny reasoning chunks for [thinking] output
        # Table-row buffer.  When a streamed line looks like it could be
        # part of a markdown table, hold it here until the block ends so
        # we can re-pad with wcwidth-aware widths.  Empty by default;
        # populated only while `_in_stream_table` is True.
        self._stream_table_buf: list[str] = []
        self._in_stream_table = False
        self._pending_edit_snapshots = {}
        self._last_input_mode_recovery = 0.0
        self._input_mode_recovery_notice_shown = False
        
        # Configuration - priority: CLI args > env vars > config file
        # Model comes from: CLI arg or config.yaml (single source of truth).
        # LLM_MODEL/OPENAI_MODEL env vars are NOT checked — config.yaml is
        # authoritative.  This avoids conflicts in multi-agent setups where
        # env vars would stomp each other.
        _model_config = CLI_CONFIG.get("model", {})
        _config_model = (_model_config.get("default") or _model_config.get("model") or "") if isinstance(_model_config, dict) else (_model_config or "")
        _DEFAULT_CONFIG_MODEL = ""
        self.model = model or _config_model or _DEFAULT_CONFIG_MODEL
        # Auto-detect model from local server if still on default
        if self.model == _DEFAULT_CONFIG_MODEL:
            _base_url = (_model_config.get("base_url") or "") if isinstance(_model_config, dict) else ""
            if "localhost" in _base_url or "127.0.0.1" in _base_url:
                from reymen.reymen_cli.runtime_provider import _auto_detect_local_model
                _detected = _auto_detect_local_model(_base_url)
                if _detected:
                    self.model = _detected
        # Track whether model was explicitly chosen by the user or fell back
        # to the global default.  Provider-specific normalisation may override
        # the default silently but should warn when overriding an explicit choice.
        # A config model that matches the global fallback is NOT considered an
        # explicit choice — the user just never changed it.  But a config model
        # like "gpt-5.3-codex" IS explicit and must be preserved.
        self._model_is_default = not model and (
            not _config_model or _config_model == _DEFAULT_CONFIG_MODEL
        )

        self._explicit_api_key = api_key
        self._explicit_base_url = base_url

        # Provider selection is resolved lazily at use-time via _ensure_runtime_credentials().
        self.requested_provider = (
            provider
            or CLI_CONFIG["model"].get("provider")
            or os.getenv("ReYMeN_INFERENCE_PROVIDER")
            or "auto"
        )
        self._provider_source: Optional[str] = None
        self.provider = self.requested_provider
        self.api_mode = "chat_completions"
        self.acp_command: Optional[str] = None
        self.acp_args: list[str] = []
        self.base_url = (
            base_url
            or CLI_CONFIG["model"].get("base_url", "")
            or os.getenv("OPENROUTER_BASE_URL", "")
        ) or None
        # Match key to resolved base_url: OpenRouter URL → prefer OPENROUTER_API_KEY,
        # custom endpoint → prefer OPENAI_API_KEY (issue #560).
        # Note: _ensure_runtime_credentials() re-resolves this before first use.
        if self.base_url and base_url_host_matches(self.base_url, "openrouter.ai"):
            self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        else:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        # Max turns priority: CLI arg > config file > env var > default
        if max_turns is not None:  # CLI arg was explicitly set
            self.max_turns = max_turns
        elif CLI_CONFIG["agent"].get("max_turns"):
            self.max_turns = CLI_CONFIG["agent"]["max_turns"]
        elif CLI_CONFIG.get("max_turns"):  # Backwards compat: root-level max_turns
            self.max_turns = CLI_CONFIG["max_turns"]
        elif os.getenv("ReYMeN_MAX_ITERATIONS"):
            try:
                self.max_turns = int(os.getenv("ReYMeN_MAX_ITERATIONS", ""))
            except (TypeError, ValueError):
                self.max_turns = 90
        else:
            self.max_turns = 90
        
        # Parse and validate toolsets
        self.enabled_toolsets = toolsets
        self.disabled_toolsets = CLI_CONFIG["agent"].get("disabled_toolsets") or []

        if toolsets and "all" not in toolsets and "*" not in toolsets:
            # Validate each toolset — MCP server names are resolved via
            # live registry aliases (registered during discover_mcp_tools),
            # but discovery hasn't run yet at this point, so exclude them.
            mcp_names = set((CLI_CONFIG.get("mcp_servers") or {}).keys())
            invalid = [t for t in toolsets if not validate_toolset(t) and t not in mcp_names]
            if invalid:
                self._console_print(f"[bold red]Warning: Unknown toolsets: {', '.join(invalid)}[/]")
        
        # Filesystem checkpoints: CLI flag > config
        cp_cfg = CLI_CONFIG.get("checkpoints", {})
        if isinstance(cp_cfg, bool):
            cp_cfg = {"enabled": cp_cfg}
        self.checkpoints_enabled = checkpoints or cp_cfg.get("enabled", False)
        self.checkpoint_max_snapshots = cp_cfg.get("max_snapshots", 20)
        self.checkpoint_max_total_size_mb = cp_cfg.get("max_total_size_mb", 500)
        self.checkpoint_max_file_size_mb = cp_cfg.get("max_file_size_mb", 10)
        self.pass_session_id = pass_session_id
        # --ignore-rules: honor either the constructor flag or the env var set
        # by `ReYMeN chat --ignore-rules` in ReYMeN_cli/main.py. When true we
        # pass skip_context_files=True and skip_memory=True to AIAgent so
        # AGENTS.md/SOUL.md/.cursorrules and persistent memory are not loaded.
        self.ignore_rules = ignore_rules or os.environ.get("ReYMeN_IGNORE_RULES") == "1"
        
        # Ephemeral system prompt: env var takes precedence, then config
        self.system_prompt = (
            os.getenv("ReYMeN_EPHEMERAL_SYSTEM_PROMPT", "")
            or CLI_CONFIG["agent"].get("system_prompt", "")
        )
        self.personalities = CLI_CONFIG["agent"].get("personalities", {})
        
        # Ephemeral prefill messages (few-shot priming, never persisted)
        self.prefill_messages = _load_prefill_messages(
            CLI_CONFIG["agent"].get("prefill_messages_file", "")
        )
        
        # Reasoning config (OpenRouter reasoning effort level)
        self.reasoning_config = _parse_reasoning_config(
            CLI_CONFIG["agent"].get("reasoning_effort", "")
        )
        self.service_tier = _parse_service_tier_config(
            CLI_CONFIG["agent"].get("service_tier", "")
        )
        
        # OpenRouter provider routing preferences
        pr = CLI_CONFIG.get("provider_routing", {}) or {}
        self._provider_sort = pr.get("sort")
        self._providers_only = pr.get("only")
        self._providers_ignore = pr.get("ignore")
        self._providers_order = pr.get("order")
        self._provider_require_params = pr.get("require_parameters", False)
        self._provider_data_collection = pr.get("data_collection")

        # OpenRouter Pareto Code router knob — coding-score floor (0.0-1.0).
        # Only applied when model.model == "openrouter/pareto-code".
        # Empty string / None / out-of-range = unset (let OR pick strongest coder).
        _or_cfg = CLI_CONFIG.get("openrouter", {}) or {}
        _raw_score = _or_cfg.get("min_coding_score")
        self._openrouter_min_coding_score: Optional[float] = None
        if _raw_score not in {None, ""}:
            try:
                _f = float(_raw_score)
                if 0.0 <= _f <= 1.0:
                    self._openrouter_min_coding_score = _f
            except (TypeError, ValueError):
                logger.warning("[fix_01_sessiz_except] Exception")
        
        # Fallback provider chain — tried in order when primary fails after retries.
        # Merge new ``fallback_providers`` entries with any legacy
        # ``fallback_model`` entries so old configs still participate.
        self._fallback_model = get_fallback_chain(CLI_CONFIG)

        # Signature of the currently-initialised agent's runtime.  Used to
        # rebuild the agent when provider / model / base_url changes across
        # turns (e.g. after /model or credential rotation).
        self._active_agent_route_signature = None

        # Agent will be initialized on first use
        self.agent: Optional[Any] = None
        self._tool_callbacks_installed = False
        self._tirith_security_checked = False
        self._app = None  # prompt_toolkit Application (set in run())
        
        # Conversation state
        self.conversation_history: List[Dict[str, Any]] = []
        self.session_start = datetime.now()
        self._resumed = False
        # Per-prompt elapsed timer — started at the beginning of each chat turn,
        # frozen when the agent thread completes, displayed in the status bar.
        self._prompt_start_time: Optional[float] = None  # time.time() when turn started
        self._prompt_duration: float = 0.0  # frozen duration of last completed turn
        # Initialize SQLite session store early so /title works before first message
        self._session_db = None
        try:
            from reymen.sistem.ReYMeN_state import SessionDB
            self._session_db = SessionDB()
        except Exception as e:
            logger.warning("Failed to initialize SessionDB — session will NOT be indexed for search: %s", e)

        # Opportunistic state.db maintenance — runs at most once per
        # min_interval_hours, tracked via state_meta in state.db itself so
        # it's shared across all ReYMeN processes for this ReYMeN_HOME.
        # Never blocks startup on failure.
        _run_state_db_auto_maintenance(self._session_db)

        # Opportunistic shadow-repo cleanup — deletes orphan/stale
        # checkpoint repos under ~/.ReYMeN/checkpoints/.  Opt-in via
        # checkpoints.auto_prune, idempotent via .last_prune marker.
        _run_checkpoint_auto_maintenance()

        # Deferred title: stored in memory until the session is created in the DB
        self._pending_title: Optional[str] = None
        
        # Session ID: reuse existing one when resuming, otherwise generate fresh
        if resume:
            self.session_id = resume
            self._resumed = True
        else:
            timestamp_str = self.session_start.strftime("%Y%m%d_%H%M%S")
            short_uuid = uuid.uuid4().hex[:6]
            self.session_id = f"{timestamp_str}_{short_uuid}"
        
        # History file for persistent input recall across sessions
        self._history_file = _ReYMeN_home / ".ReYMeN_history"
        self._last_invalidate: float = 0.0  # throttle UI repaints
        self._app = None

        # State shared by interactive run() and single-query chat mode.
        # These must exist before any direct chat() call because single-query
        # mode does not go through run().
        self._agent_running = False
        self._pending_input = queue.Queue()
        self._interrupt_queue = queue.Queue()
        # Tracks whether the turn that just finished was interrupted via
        # Ctrl+C. Consumed by _maybe_continue_goal_after_turn so /goal loops
        # don't auto-queue another continuation on top of a user-cancelled
        # turn (which would make Ctrl+C feel like it did nothing).
        self._last_turn_interrupted = False
        self._should_exit = False
        # /exit --delete: when True, the current session's SQLite history and
        # on-disk transcripts are deleted during shutdown. Set by
        # process_command() when the user runs /exit --delete or /quit --delete.
        # Ported from google-gemini/gemini-cli#19332.
        self._delete_session_on_exit = False
        # /update: when set, run() executes relaunch() after prompt_toolkit
        # has fully exited and cleaned up terminal modes.  Set by
        # _handle_update_command() so the relaunch happens on the main thread,
        # not the background process_loop thread.
        self._pending_relaunch: list[str] | None = None
        self._last_ctrl_c_time = 0
        self._clarify_state = None
        self._clarify_freetext = False
        self._clarify_deadline = 0
        self._sudo_state = None
        self._sudo_deadline = 0
        self._modal_input_snapshot = None
        self._approval_state = None
        self._approval_deadline = 0
        self._approval_lock = threading.Lock()
        self._slash_confirm_state = None
        self._slash_confirm_deadline = 0
        self._model_picker_state = None
        # Armed when a bare `/resume` prints the recent-sessions list so the
        # very next bare numeric input (e.g. `3`) resolves to that session.
        # Holds the exact list used for index resolution; one-shot (cleared on
        # the next submitted input, whether it's the selection or anything
        # else). See #34584.
        self._pending_resume_sessions = None
        self._secret_state = None
        self._secret_deadline = 0
        self._spinner_text: str = ""  # thinking spinner text for TUI
        self._tool_start_time: float = 0.0  # monotonic timestamp when current tool started (for live elapsed)
        self._pending_tool_info: dict = {}  # function_name -> list of (preview, args) for stacked scrollback
        self._last_scrollback_tool: str = ""  # last tool name printed to scrollback (for "new" dedup)
        self._command_running = False
        self._command_status = ""
        self._attached_images: list[Path] = []
        self._image_counter = 0
        self.preloaded_skills: list[str] = []
        self._startup_skills_line_shown = False

        # Voice mode state (also reinitialized inside run() for interactive TUI).
        self._voice_lock = threading.Lock()
        self._voice_mode = False
        self._voice_tts = False
        self._voice_recorder = None
        self._voice_recording = False
        self._voice_processing = False
        self._voice_continuous = False
        self._voice_tts_done = threading.Event()
        self._voice_tts_done.set()

        # Status bar visibility (toggled via /statusbar)
        self._status_bar_visible = True
        # When True, the input separator rules and the dynamic status bar are
        # hidden until the next user input. Set by _recover_after_resize() so a
        # SIGWINCH cannot stamp a freshly-drawn status bar on top of one that
        # the terminal just reflowed into scrollback — the cause of duplicated
        # bars / "blank line flooding" reports (#19280, #22976).
        self._status_bar_suppressed_after_resize = False
        self._resize_recovery_lock = threading.Lock()
        self._resize_recovery_timer = None
        self._resize_recovery_pending = False

        # Background task tracking: {task_id: threading.Thread}
        self._background_tasks: Dict[str, threading.Thread] = {}
        self._background_task_counter = 0

    def show_banner(self):
        """Display the welcome banner in Claude Code style."""
        self.console.clear()
        ctx_len = None
        if hasattr(self, 'agent') and self.agent and hasattr(self.agent, 'context_compressor'):
            ctx_len = self.agent.context_compressor.context_length
        
        # Auto-compact for narrow terminals — the full banner with caduceus
        # + tool list needs ~80 columns minimum to render without wrapping.
        term_width = shutil.get_terminal_size().columns
        use_compact = self.compact or term_width < 80
        
        if use_compact:
            self._console_print(_build_compact_banner())
            self._show_status()
        else:
            # Get tools for display
            tools = get_tool_definitions(enabled_toolsets=self.enabled_toolsets, quiet_mode=True)
            
            # Get terminal working directory (where commands will execute)
            cwd = os.getenv("TERMINAL_CWD", os.getcwd())
            
            # Build and display the banner
            build_welcome_banner(
                console=self.console,
                model=self.model,
                cwd=cwd,
                tools=tools,
                enabled_toolsets=self.enabled_toolsets,
                session_id=self.session_id,
                context_length=ctx_len,
            )
        
        # Tool discovery is intentionally deferred on the Termux bare prompt
        # path; availability warnings are shown once tools are initialized.
        if os.environ.get("ReYMeN_DEFER_AGENT_STARTUP") != "1":
            self._show_tool_availability_warnings()

        # Warn about low context lengths (common with local servers). Keep
        # this tied to the runtime guard so guidance cannot drift again.
        from agent.model_metadata import MINIMUM_CONTEXT_LENGTH
        if ctx_len and ctx_len < MINIMUM_CONTEXT_LENGTH:
            self._console_print()
            self._console_print(
                f"[yellow]⚠️  Context length is only {ctx_len:,} tokens — "
                f"this is likely too low for agent use with tools.[/]"
            )
            self._console_print(
                f"[dim]   ReYMeN needs at least {MINIMUM_CONTEXT_LENGTH:,} tokens. Tool schemas + system prompt use a large fixed prefix.[/]"
            )
            base_url = getattr(self, "base_url", "") or ""
            if "11434" in base_url or "ollama" in base_url.lower():
                self._console_print(
                    f"[dim]   Ollama fix: OLLAMA_CONTEXT_LENGTH={MINIMUM_CONTEXT_LENGTH} ollama serve[/]"
                )
            elif "1234" in base_url:
                self._console_print(
                    "[dim]   LM Studio fix: Set context length in model settings → reload model[/]"
                )
            else:
                self._console_print(
                    "[dim]   Fix: Set model.context_length in config.yaml, or increase your server's context setting[/]"
                )

        # Warn if the configured model is a Nous ReYMeN LLM (not agentic)
        from reymen.reymen_cli.model_switch import is_nous_ReYMeN_non_agentic

        model_name = getattr(self, "model", "") or ""
        if is_nous_ReYMeN_non_agentic(model_name):
            self._console_print()
            self._console_print(
                "[bold yellow]⚠  Nous Research ReYMeN 3 & 4 models are NOT agentic and are not "
                "designed for use with ReYMeN Agent.[/]"
            )
            self._console_print(
                "[dim]   They lack tool-calling capabilities required for agent workflows. "
                "Consider using an agentic model (Claude, GPT, Gemini, DeepSeek, etc.).[/]"
            )
            self._console_print(
                "[dim]   Switch with: /model sonnet  or  /model gpt5[/]"
            )

        self._console_print()

    def _display_resumed_history(self):
        """Render a compact recap of previous conversation messages.

        Uses Rich markup with dim/muted styling so the recap is visually
        distinct from the active conversation.  Caps the display at the
        last ``MAX_DISPLAY_EXCHANGES`` user/assistant exchanges and shows
        an indicator for earlier hidden messages.
        """
        if not self.conversation_history:
            return

        # Check config: resume_display setting
        if self.resume_display == "minimal":
            return

        # Read limits from config (with hardcoded defaults)
        _disp = CLI_CONFIG.get("display", {})
        MAX_DISPLAY_EXCHANGES = int(_disp.get("resume_exchanges", 10))
        MAX_USER_LEN = int(_disp.get("resume_max_user_chars", 300))
        MAX_ASST_LEN = int(_disp.get("resume_max_assistant_chars", 200))
        MAX_ASST_LINES = int(_disp.get("resume_max_assistant_lines", 3))
        SKIP_TOOL_ONLY = _disp.get("resume_skip_tool_only", True)

        # Collect displayable entries (skip system, tool-result messages)
        entries = []  # list of (role, display_text)
        _last_asst_idx = None       # index of last assistant entry
        _last_asst_full = None      # un-truncated display text for last assistant
        for msg in self.conversation_history:
            role = msg.get("role", "")
            content = msg.get("content")
            tool_calls = msg.get("tool_calls") or []

            if role == "system":
                continue
            if role == "tool":
                continue

            if role == "user":
                text = "" if content is None else str(content)
                # Handle multimodal content (list of dicts)
                if isinstance(content, list):
                    parts = []
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            parts.append(part.get("text", ""))
                        elif isinstance(part, dict) and part.get("type") == "image_url":
                            parts.append("[image]")
                    text = " ".join(parts)
                if len(text) > MAX_USER_LEN:
                    text = text[:MAX_USER_LEN] + "..."
                entries.append(("user", text))

            elif role == "assistant":
                text = "" if content is None else str(content)
                text = _strip_reasoning_tags(text)
                parts = []
                full_parts = []  # un-truncated version
                if text:
                    full_parts.append(text)
                    lines = text.splitlines()
                    if len(lines) > MAX_ASST_LINES:
                        text = "\n".join(lines[:MAX_ASST_LINES]) + " ..."
                    if len(text) > MAX_ASST_LEN:
                        text = text[:MAX_ASST_LEN] + "..."
                    parts.append(text)
                if tool_calls:
                    tc_count = len(tool_calls)
                    # Extract tool names
                    names = []
                    for tc in tool_calls:
                        fn = tc.get("function", {})
                        name = fn.get("name", "unknown") if isinstance(fn, dict) else "unknown"
                        if name not in names:
                            names.append(name)
                    names_str = ", ".join(names[:4])
                    if len(names) > 4:
                        names_str += ", ..."
                    noun = "call" if tc_count == 1 else "calls"
                    tc_summary = f"[{tc_count} tool {noun}: {names_str}]"
                    parts.append(tc_summary)
                    full_parts.append(tc_summary)
                if not parts:
                    # Skip pure-reasoning messages that have no visible output
                    continue
                # Skip tool-call-only entries when SKIP_TOOL_ONLY is enabled
                has_text = bool(text)
                if SKIP_TOOL_ONLY and not has_text and tool_calls:
                    continue
                entries.append(("assistant", " ".join(parts)))
                _last_asst_idx = len(entries) - 1
                _last_asst_full = " ".join(full_parts)

        if not entries:
            return

        # Determine if we need to truncate
        skipped = 0
        if len(entries) > MAX_DISPLAY_EXCHANGES * 2:
            skipped = len(entries) - MAX_DISPLAY_EXCHANGES * 2
            entries = entries[skipped:]

        # Replace last assistant entry with full (un-truncated) text
        # so the user can see where they left off without wasting tokens.
        if _last_asst_idx is not None and _last_asst_full:
            adj_idx = _last_asst_idx - skipped
            if 0 <= adj_idx < len(entries):
                entries[adj_idx] = ("assistant_last", _last_asst_full)

        # Build the display using Rich
        from rich.panel import Panel
        from rich.text import Text

        try:
            from reymen.reymen_cli.skin_engine import get_active_skin
            _skin = get_active_skin()
            _history_text_c = _skin.get_color("banner_text", "#FFF8DC")
            _session_label_c = _skin.get_color("session_label", "#DAA520")
            _session_border_c = _skin.get_color("session_border", "#8B8682")
            _assistant_label_c = _skin.get_color("ui_ok", "#8FBC8F")
        except Exception:
            _history_text_c = "#FFF8DC"
            _session_label_c = "#DAA520"
            _session_border_c = "#8B8682"
            _assistant_label_c = "#8FBC8F"

        lines = Text()
        if skipped:
            lines.append(
                f"  ... {skipped} earlier messages ...\n\n",
                style="dim italic",
            )

        for i, (role, text) in enumerate(entries):
            if role == "user":
                lines.append("  ● You: ", style=f"dim bold {_session_label_c}")
                # Show first line inline, indent rest
                msg_lines = text.splitlines()
                lines.append(msg_lines[0] + "\n", style="dim")
                for ml in msg_lines[1:]:
                    lines.append(f"         {ml}\n", style="dim")
            elif role == "assistant_last":
                # Last assistant response shown in full, non-dim
                lines.append("  ◆ ReYMeN: ", style=f"bold {_assistant_label_c}")
                msg_lines = text.splitlines()
                lines.append(msg_lines[0] + "\n", style="")
                for ml in msg_lines[1:]:
                    lines.append(f"            {ml}\n", style="")
            else:
                lines.append("  ◆ ReYMeN: ", style=f"dim bold {_assistant_label_c}")
                msg_lines = text.splitlines()
                lines.append(msg_lines[0] + "\n", style="dim")
                for ml in msg_lines[1:]:
                    lines.append(f"            {ml}\n", style="dim")
            if i < len(entries) - 1:
                lines.append("")  # small gap

        panel = Panel(
            lines,
            title=f"[dim {_session_label_c}]Previous Conversation[/]",
            border_style=f"dim {_session_border_c}",
            padding=(0, 1),
            style=_history_text_c,
        )
        _record_output_history_entry(lambda: self._render_resume_history_panel_lines(panel))
        with _suspend_output_history():
            self._console_print(panel)

    def _try_attach_clipboard_image(self) -> bool:
        """Check clipboard for an image and attach it if found.

        Saves the image to ~/.ReYMeN/images/ and appends the path to
        ``_attached_images``.  Returns True if an image was attached.
        """
        from reymen.reymen_cli.clipboard import save_clipboard_image

        img_dir = get_reymen_home() / "images"
        self._image_counter += 1
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_path = img_dir / f"clip_{ts}_{self._image_counter}.png"

        if save_clipboard_image(img_path):
            self._attached_images.append(img_path)
            return True
        self._image_counter -= 1
        return False

    # Moved to cli_mixin_fileops.py (MixinFileOps._handle_rollback_command)


    def _resolve_checkpoint_ref(self, ref: str, checkpoints: list) -> str | None:
        """Resolve a checkpoint number or hash to a full commit hash."""
        try:
            idx = int(ref) - 1  # 1-indexed for user
            if 0 <= idx < len(checkpoints):
                return checkpoints[idx]["hash"]
            else:
                print(f"  Invalid checkpoint number. Use 1-{len(checkpoints)}.")
                return None
        except ValueError:
            # Treat as a git hash
            return ref

    # Moved to cli_mixin_fileops.py (MixinFileOps._handle_snapshot_command)


    # Moved to cli_mixin_fileops.py (MixinFileOps._handle_stop_command)


    # Moved to cli_mixin_ui.py (MixinUI._handle_agents_command)


    # Moved to cli_mixin_media.py (MixinMedia._handle_paste_command)


    def _write_osc52_clipboard(self, text: str) -> None:
        """Copy *text* to terminal clipboard via OSC 52."""
        payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
        seq = f"\x1b]52;c;{payload}\x07"
        out = getattr(self, "_app", None)
        output = getattr(out, "output", None) if out else None
        if output and hasattr(output, "write_raw"):
            output.write_raw(seq)
            output.flush()
            return
        if output and hasattr(output, "write"):
            output.write(seq)
            output.flush()
            return
        sys.stdout.write(seq)
        sys.stdout.flush()

    def _recover_terminal_input_modes(self, *, reason: str) -> None:
        """Best-effort reset when leaked mouse reports indicate mode drift."""
        now = time.monotonic()
        # Rate-limit to avoid thrashing if a terminal floods reports.
        if now - self._last_input_mode_recovery < 0.5:
            return
        self._last_input_mode_recovery = now

        out = getattr(self, "_app", None)
        output = getattr(out, "output", None) if out else None
        try:
            if output and hasattr(output, "write_raw"):
                output.write_raw(_TERMINAL_INPUT_MODE_RESET_SEQ)
                output.flush()
            elif output and hasattr(output, "write"):
                output.write(_TERMINAL_INPUT_MODE_RESET_SEQ)
                output.flush()
            else:
                sys.stdout.write(_TERMINAL_INPUT_MODE_RESET_SEQ)
                sys.stdout.flush()
        except Exception:
            return

        logger.warning("Recovered terminal input modes after leak: %s", reason)
        if not self._input_mode_recovery_notice_shown:
            self._input_mode_recovery_notice_shown = True
            _cprint(
                f"  {_DIM}Recovered terminal input modes after leaked mouse reports. "
                f"If this repeats, run /new or restart this tab.{_RST}"
            )

    # Moved to cli_mixin_media.py (MixinMedia._handle_copy_command)


    # Moved to cli_mixin_media.py (MixinMedia._handle_image_command)

    def _preprocess_images_with_vision(self, text: str, images: list, *, announce: bool = True) -> str:
        """Analyze attached images via the vision tool and return enriched text.

        Instead of embedding raw base64 ``image_url`` content parts in the
        conversation (which only works with vision-capable models), this
        pre-processes each image through the auxiliary vision model (Gemini
        Flash) and prepends the descriptions to the user's message — the
        same approach the messaging gateway uses.

        The local file path is included so the agent can re-examine the
        image later with ``vision_analyze`` if needed.
        """
        import asyncio as _asyncio
        from tools.vision_tools import vision_analyze_tool

        analysis_prompt = (
            "Describe everything visible in this image in thorough detail. "
            "Include any text, code, data, objects, people, layout, colors, "
            "and any other notable visual information."
        )

        enriched_parts = []
        for img_path in images:
            if not img_path.exists():
                continue
            size_kb = img_path.stat().st_size // 1024
            if announce:
                _cprint(f"  {_DIM}👁️  analyzing {img_path.name} ({size_kb}KB)...{_RST}")
            try:
                result_json = _asyncio.run(
                    vision_analyze_tool(image_url=str(img_path), user_prompt=analysis_prompt)
                )
                result = json.loads(result_json)
                if result.get("success"):
                    description = result.get("analysis", "")
                    enriched_parts.append(
                        f"[The user attached an image. Here's what it contains:\n{description}]\n"
                        f"[If you need a closer look, use vision_analyze with "
                        f"image_url: {img_path}]"
                    )
                    if announce:
                        _cprint(f"  {_DIM}✓ image analyzed{_RST}")
                else:
                    enriched_parts.append(
                        f"[The user attached an image but it couldn't be analyzed. "
                        f"You can try examining it with vision_analyze using "
                        f"image_url: {img_path}]"
                    )
                    if announce:
                        _cprint(f"  {_DIM}⚠ vision analysis failed — path included for retry{_RST}")
            except Exception as e:
                enriched_parts.append(
                    f"[The user attached an image but analysis failed ({e}). "
                    f"You can try examining it with vision_analyze using "
                    f"image_url: {img_path}]"
                )
                if announce:
                    _cprint(f"  {_DIM}⚠ vision analysis error — path included for retry{_RST}")

        # Combine: vision descriptions first, then the user's original text
        user_text = text if isinstance(text, str) and text else ""
        if enriched_parts:
            prefix = "\n\n".join(enriched_parts)
            return f"{prefix}\n\n{user_text}" if user_text else prefix
        return user_text or "What do you see in this image?"

    def show_help(self):
        """Display help information with categorized commands."""
        from reymen.reymen_cli.commands import COMMANDS_BY_CATEGORY

        try:
            from reymen.reymen_cli.skin_engine import get_active_help_header
            header = get_active_help_header("(^_^)? Available Commands")
        except Exception:
            header = "(^_^)? Available Commands"
        header = (header or "").strip() or "(^_^)? Available Commands"
        inner_width = 55
        if len(header) > inner_width:
            header = header[:inner_width]
        _cprint(f"\n{_BOLD}+{'-' * inner_width}+{_RST}")
        _cprint(f"{_BOLD}|{header:^{inner_width}}|{_RST}")
        _cprint(f"{_BOLD}+{'-' * inner_width}+{_RST}")

        for category, commands in COMMANDS_BY_CATEGORY.items():
            _cprint(f"\n  {_BOLD}── {category} ──{_RST}")
            for cmd, desc in commands.items():
                if not self._command_available(cmd):
                    continue
                ChatConsole().print(f"    [bold {_accent_hex()}]{cmd:<15}[/] [dim]-[/] {_escape(desc)}")

        skill_commands = _ensure_skill_commands()
        if skill_commands:
            _cprint(f"\n  ⚡ {_BOLD}Skill Commands{_RST} ({len(skill_commands)} installed):")
            for cmd, info in sorted(skill_commands.items()):
                ChatConsole().print(
                    f"    [bold {_accent_hex()}]{cmd:<22}[/] [dim]-[/] {_escape(info['description'])}"
                )

        _bundles_now = get_skill_bundles()
        if _bundles_now:
            _cprint(f"\n  ▣ {_BOLD}Skill Bundles{_RST} ({len(_bundles_now)} installed):")
            for cmd, info in sorted(_bundles_now.items()):
                skill_count = len(info.get("skills", []))
                desc = info.get("description") or f"Load {skill_count} skills"
                ChatConsole().print(
                    f"    [bold {_accent_hex()}]{cmd:<22}[/] [dim]-[/] "
                    f"{_escape(desc)} [dim]({skill_count} skills)[/]"
                )

        _cprint(f"\n  {_DIM}Tip: Just type your message to chat with ReYMeN!{_RST}")
        _cprint(f"  {_DIM}Multi-line: Alt+Enter for a new line{_RST}")
        _cprint(f"  {_DIM}Draft editor: Ctrl+G (Alt+G in VSCode/Cursor){_RST}")
        if _is_termux_environment():
            _cprint(f"  {_DIM}Attach image: /image {_termux_example_image_path()} or start your prompt with a local image path{_RST}\n")
        else:
            _cprint(f"  {_DIM}Paste image: Alt+V (or /paste){_RST}\n")
    
    def show_tools(self):
        """Display available tools with kawaii ASCII art."""
        tools = get_tool_definitions(enabled_toolsets=self.enabled_toolsets, quiet_mode=True)
        
        if not tools:
            print("(;_;) No tools available")
            return
        
        # Header
        print()
        title = "(^_^)/ Available Tools"
        width = 78
        pad = width - len(title)
        print("+" + "-" * width + "+")
        print("|" + " " * (pad // 2) + title + " " * (pad - pad // 2) + "|")
        print("+" + "-" * width + "+")
        print()
        
        # Group tools by toolset
        toolsets = {}
        for tool in sorted(tools, key=lambda t: t["function"]["name"]):
            name = tool["function"]["name"]
            toolset = get_toolset_for_tool(name) or "unknown"
            if toolset not in toolsets:
                toolsets[toolset] = []
            desc = tool["function"].get("description", "")
            # First sentence: split on ". " (period+space) to avoid breaking on "e.g." or "v2.0"
            desc = desc.split("\n")[0]
            if ". " in desc:
                desc = desc[:desc.index(". ") + 1]
            toolsets[toolset].append((name, desc))
        
        # Display by toolset
        for toolset in sorted(toolsets.keys()):
            print(f"  [{toolset}]")
            for name, desc in toolsets[toolset]:
                print(f"    * {name:<20} - {desc}")
            print()
        
        print(f"  Total: {len(tools)} tools  ヽ(^o^)ノ")
        print()

    # Moved to cli_mixin_skillstools.py (MixinSkillsTools._handle_tools_command)

    def show_toolsets(self):
        """Display available toolsets with kawaii ASCII art."""
        all_toolsets = get_all_toolsets()
        
        # Header
        print()
        title = "(^_^)b Available Toolsets"
        width = 58
        pad = width - len(title)
        print("+" + "-" * width + "+")
        print("|" + " " * (pad // 2) + title + " " * (pad - pad // 2) + "|")
        print("+" + "-" * width + "+")
        print()
        
        for name in sorted(all_toolsets.keys()):
            info = get_toolset_info(name)
            if info:
                tool_count = info["tool_count"]
                desc = info["description"]
                
                # Mark if currently enabled
                marker = "(*)" if self.enabled_toolsets and name in self.enabled_toolsets else "   "
                print(f"  {marker} {name:<18} [{tool_count:>2} tools] - {desc}")
        
        print()
        print("  (*) = currently enabled")
        print()
        print("  Tip: Use 'all' or '*' to enable all toolsets")
        print("  Example: python cli.py --toolsets web,terminal")
        print()
    
    # Moved to cli_mixin_agentsettings.py (MixinAgentSettings._handle_profile_command)


    def show_config(self):
        """Display current configuration with kawaii ASCII art."""
        # Get terminal config from environment (which was set from cli-config.yaml)
        terminal_env = os.getenv("TERMINAL_ENV", "local")
        terminal_cwd = os.getenv("TERMINAL_CWD", os.getcwd())
        terminal_timeout = os.getenv("TERMINAL_TIMEOUT", "60")
        
        user_config_path = _ReYMeN_home / 'config.yaml'
        project_config_path = Path(__file__).parent / 'cli-config.yaml'
        if user_config_path.exists():
            config_path = user_config_path
        else:
            config_path = project_config_path
        config_status = "(loaded)" if config_path.exists() else "(not found)"
        
        # ``self.api_key`` may be a callable (Azure Foundry Entra ID bearer
        # provider). Never invoke it; just identify the auth surface.
        from agent.azure_identity_adapter import is_token_provider
        if is_token_provider(self.api_key):
            api_key_display = "Microsoft Entra ID"
        elif isinstance(self.api_key, str) and len(self.api_key) > 12:
            api_key_display = f"{self.api_key[:8]}...{self.api_key[-4:]}"
        else:
            api_key_display = "Not set!"
        
        print()
        title = "(^_^) Configuration"
        width = 50
        pad = width - len(title)
        print("+" + "-" * width + "+")
        print("|" + " " * (pad // 2) + title + " " * (pad - pad // 2) + "|")
        print("+" + "-" * width + "+")
        print()
        print("  -- Model --")
        print(f"  Model:     {self.model}")
        print(f"  Base URL:  {self.base_url}")
        print(f"  API Key:   {api_key_display}")
        print()
        print("  -- Terminal --")
        print(f"  Environment:  {terminal_env}")
        if terminal_env == "ssh":
            ssh_host = os.getenv("TERMINAL_SSH_HOST", "not set")
            ssh_user = os.getenv("TERMINAL_SSH_USER", "not set")
            ssh_port = os.getenv("TERMINAL_SSH_PORT", "22")
            print(f"  SSH Target:   {ssh_user}@{ssh_host}:{ssh_port}")
        print(f"  Working Dir:  {terminal_cwd}")
        print(f"  Timeout:      {terminal_timeout}s")
        print()
        print("  -- Agent --")
        print(f"  Max Turns:  {self.max_turns}")
        print(f"  Toolsets:   {', '.join(self.enabled_toolsets) if self.enabled_toolsets else 'all'}")
        print(f"  Verbose:    {self.verbose}")
        print()
        print("  -- Session --")
        print(f"  Started:     {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Config File: {config_path} {config_status}")
        print()
    
    def _prefill_input_buffer(self, text: str) -> None:
        """Place ``text`` in the active prompt_toolkit buffer, editable."""
        app = getattr(self, "_app", None)
        if app is None:
            return
        try:
            buf = app.current_buffer
            buf.text = text
            if hasattr(buf, "cursor_position"):
                buf.cursor_position = len(text)
            app.invalidate()
        except Exception as e:
            logger.debug("undo: prefill buffer failed: %s", e)
    
    def _run_curses_picker(self, title: str, items: list[str], default_index: int = 0) -> int | None:
        """Run curses_single_select via run_in_terminal so prompt_toolkit handles terminal ownership cleanly."""
        import threading
        from reymen.reymen_cli.curses_ui import curses_single_select

        result = [None]

        def _pick():
            result[0] = curses_single_select(title, items, default_index=default_index)

        # run_in_terminal requires an asyncio event loop — only exists in the
        # main prompt_toolkit thread.  If we're in a background thread (e.g.
        # process_loop), fall back to direct curses call.
        in_main_thread = threading.current_thread() is threading.main_thread()

        if self._app and in_main_thread:
            from prompt_toolkit.application import run_in_terminal
            was_visible = self._status_bar_visible
            self._status_bar_visible = False
            self._app.invalidate()
            try:
                run_in_terminal(_pick)
            finally:
                self._status_bar_visible = was_visible
                self._app.invalidate()
        else:
            _pick()

        return result[0]

    def _prompt_text_input(self, prompt_text: str) -> str | None:
        """Prompt for free-text input safely inside or outside prompt_toolkit.

        Mirrors the thread-aware guard in ``_run_curses_picker``: ``run_in_terminal``
        returns a coroutine that must be awaited by the prompt_toolkit event loop,
        which only exists on the main thread.  Slash commands are dispatched from
        the ``process_loop`` daemon thread (see issue #23185), so calling
        ``run_in_terminal`` from there orphans the coroutine — ``_ask`` never runs,
        and user keystrokes leak into the composer instead.  Fall back to a direct
        ``input()`` when we're off the main thread.
        """
        import threading
        result = [None]

        def _ask():
            try:
                result[0] = input(prompt_text).strip() or None
            except (KeyboardInterrupt, EOFError):
                logger.warning("[fix_01_sessiz_except] Exception")

        in_main_thread = threading.current_thread() is threading.main_thread()

        if self._app and in_main_thread:
            from prompt_toolkit.application import run_in_terminal
            was_visible = self._status_bar_visible
            self._status_bar_visible = False
            self._app.invalidate()
            try:
                run_in_terminal(_ask)
            except Exception:
                # WSL / Warp / certain terminal emulators silently drop the
                # scheduled coroutine.  Fall back to a direct input() so the
                # user's keystrokes don't leak into the agent buffer.
                try:
                    _ask()
                except Exception:
                    logger.warning("[fix_01_sessiz_except] Exception")
            finally:
                self._status_bar_visible = was_visible
                self._app.invalidate()
        else:
            _ask()
        return result[0]

    def _prompt_text_input_modal(
        self,
        *,
        title: str,
        detail: str,
        choices: list[tuple[str, str, str]],
        timeout: float = 120,
    ) -> str | None:
        """Prompt through the prompt_toolkit composer instead of raw input().

        This is for CLI slash-command confirmations.  The old raw input() path
        fought prompt_toolkit's active stdin ownership: in some terminals the
        prompt appeared above the TUI, choices were redrawn later, and Enter
        could be interpreted as EOF/exit.  A first-class modal state keeps the
        choices visible and lets the normal Enter key binding submit the typed
        or highlighted choice.

        **Platform note (Windows dead-lock — issue #30768):**
        The queue-based modal relies on prompt_toolkit key bindings receiving
        keyboard events and calling ``_submit_slash_confirm_response``.  On
        Windows (PowerShell / Windows Terminal) the prompt_toolkit input
        channel can become unresponsive when the modal is entered from the
        ``process_loop`` daemon thread, causing a dead-lock: the user sees the
        confirmation panel but keystrokes never reach the key bindings and the
        ``response_queue.get()`` blocks until the 120-second timeout expires.

        To avoid this, we fall back to ``_prompt_text_input`` (a simple
        ``input()``-based prompt) when any of these conditions hold:

        * ``sys.platform == "win32"`` — native Windows console (ConPTY /
          win32_input) does not support the modal reliably.
        * ``self._app`` is not set — unit tests / non-interactive contexts.

        On non-Windows platforms the modal itself is still safe from the
        ``process_loop`` daemon thread as long as the main-thread event loop
        owns the prompt_toolkit buffer mutations.  When we are off the main
        thread, schedule the modal snapshot / restore work on ``self._app.loop``
        via ``call_soon_threadsafe`` and keep the queue-based response path.
        """
        import threading
        import time as _time

        if not choices:
            return None

        # If prompt_toolkit is not running (unit tests / non-interactive calls),
        # keep the simple stdin fallback.
        if not getattr(self, "_app", None):
            return self._prompt_text_input("Choice [1/2/3]: ")

        # On Windows the prompt_toolkit input channel can deadlock when the
        # modal is entered from the process_loop daemon thread — keystrokes
        # never reach the key bindings, so response_queue.get() blocks for
        # the full timeout (issue #30768).  Fall back to the simpler
        # stdin-based prompt which works reliably on Windows.
        if sys.platform == "win32":
            return self._prompt_text_input("Choice [1/2/3]: ")

        try:
            app_loop = self._app.loop
        except Exception:
            app_loop = None

        in_main_thread = threading.current_thread() is threading.main_thread()
        if not in_main_thread and app_loop is None:
            return self._prompt_text_input("Choice [1/2/3]: ")

        response_queue = queue.Queue()

        def _setup_modal() -> None:
            self._capture_modal_input_snapshot()
            self._slash_confirm_state = {
                "title": title,
                "detail": detail,
                "choices": choices,
                "selected": 0,
                "response_queue": response_queue,
            }
            self._slash_confirm_deadline = _time.monotonic() + timeout
            self._invalidate()

        def _teardown_modal() -> None:
            self._slash_confirm_state = None
            self._slash_confirm_deadline = 0
            self._restore_modal_input_snapshot()
            self._invalidate()

        def _run_on_app_loop(fn) -> bool:
            if in_main_thread or app_loop is None:
                fn()
                return True
            ready = threading.Event()

            def _wrapped() -> None:
                try:
                    fn()
                finally:
                    ready.set()

            try:
                app_loop.call_soon_threadsafe(_wrapped)
            except Exception:
                return False
            return ready.wait(timeout=5)

        if not _run_on_app_loop(_setup_modal):
            return self._prompt_text_input("Choice [1/2/3]: ")

        _last_countdown_refresh = _time.monotonic()
        try:
            while True:
                try:
                    result = response_queue.get(timeout=1)
                    _run_on_app_loop(_teardown_modal)
                    return result
                except queue.Empty:
                    remaining = self._slash_confirm_deadline - _time.monotonic()
                    if remaining <= 0:
                        break
                    now = _time.monotonic()
                    if now - _last_countdown_refresh >= 5.0:
                        _last_countdown_refresh = now
                        self._invalidate()
        finally:
            if self._slash_confirm_state is not None:
                _run_on_app_loop(_teardown_modal)
        return None

    def _handle_codex_runtime(self, cmd_original: str) -> None:
        """Handle /codex-runtime — toggle the codex app-server runtime opt-in.

        Usage:
            /codex-runtime                       — show current state
            /codex-runtime auto                  — ReYMeN default (chat_completions)
            /codex-runtime codex_app_server      — hand turns to codex subprocess
            /codex-runtime on / off              — synonyms for the above
        """
        from ReYMeN_cli import codex_runtime_switch as crs

        parts = cmd_original.split(None, 1)
        raw_args = parts[1].strip() if len(parts) > 1 else ""
        new_value, errors = crs.parse_args(raw_args)
        if errors:
            for err in errors:
                _cprint(f"❌ {err}")
            return

        # Load + persist via the existing config helpers
        try:
            from reymen.reymen_cli.config import load_config, save_config
        except Exception as exc:
            _cprint(f"❌ could not load config: {exc}")
            return
        cfg = load_config()

        result = crs.apply(
            cfg,
            new_value,
            persist_callback=(save_config if new_value is not None else None),
        )

        prefix = "✓" if result.success else "✗"
        for line in result.message.splitlines():
            _cprint(f"  {prefix} {line}" if line.startswith("openai_runtime")
                    else f"    {line}")
        if result.success and result.requires_new_session:
            _cprint("    Tip: `/reset` starts a new session immediately.")

    def _output_console(self):
        """Use prompt_toolkit-safe Rich rendering once the TUI is live."""
        if getattr(self, "_app", None):
            return ChatConsole()
        return self.console

    # Moved to cli_mixin_agentsettings.py (MixinAgentSettings._handle_gquota_command)


    # Moved to cli_mixin_agentsettings.py (MixinAgentSettings._handle_personality_command)


    # Moved to cli_mixin_skillstools.py (MixinSkillsTools._handle_cron_command)


    # Moved to cli_mixin_skillstools.py (MixinSkillsTools._handle_curator_command)


    # Moved to cli_mixin_ui.py (MixinUI._handle_kanban_command)


    # Moved to cli_mixin_skillstools.py (MixinSkillsTools._handle_skills_command)


    # Moved to cli_mixin_skillstools.py (MixinSkillsTools._handle_background_command)


    def _try_launch_chrome_debug(port: int, system: str) -> bool:
        """Try to launch a Chromium-family browser with remote debugging enabled.

        Uses a dedicated user-data-dir so the debug instance doesn't conflict
        with an already-running browser using the default profile.

        Returns True if a launch command was executed (doesn't guarantee success).
        """
        return try_launch_chrome_debug(port, system)

    # Moved to cli_mixin_skillstools.py (MixinSkillsTools._handle_bundles_command)


    # Moved to cli_mixin_browser.py (MixinBrowser._handle_browser_command)


    def _get_goal_manager(self):
        """Return the GoalManager bound to the current session_id.

        Cached on ``self._goal_manager`` and rebound lazily when
        ``session_id`` changes (e.g. after /new or a compression-driven
        session split).
        """
        try:
            from reymen.reymen_cli.goals import GoalManager
            from reymen.reymen_cli.config import load_config
        except Exception as exc:
            logging.debug("goal manager unavailable: %s", exc)
            return None

        sid = getattr(self, "session_id", None) or ""
        if not sid:
            return None

        existing = getattr(self, "_goal_manager", None)
        if existing is not None and getattr(existing, "session_id", None) == sid:
            return existing

        try:
            cfg = load_config() or {}
            goals_cfg = cfg.get("goals") or {}
            max_turns = int(goals_cfg.get("max_turns", 20) or 20)
        except Exception:
            max_turns = 20

        mgr = GoalManager(session_id=sid, default_max_turns=max_turns)
        self._goal_manager = mgr
        return mgr

    # Moved to cli_mixin_goals.py (MixinGoals._handle_goal_command)
    # Moved to cli_mixin_goals.py (MixinGoals._handle_subgoal_command)
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

    # Moved to cli_mixin_ui.py (MixinUI._handle_skin_command)
    # Moved to cli_mixin_ui.py (MixinUI._handle_footer_command)
    def _toggle_verbose(self):
        """Cycle tool progress mode: off → new → all → verbose → off.

        Tool-progress display (full args / results / think blocks at the
        ``verbose`` step) is INDEPENDENT of global DEBUG logging.  Cycling
        through here does not change ``self.verbose`` or the agent's
        ``verbose_logging`` / ``quiet_mode`` — those remain under the
        explicit ``-v``/``--verbose`` flag and the ``/verbose-logging``
        toggle.  See PR #6a1aa420e for the history that decoupled them.
        """
        cycle = ["off", "new", "all", "verbose"]
        try:
            idx = cycle.index(self.tool_progress_mode)
        except ValueError:
            idx = 2  # default to "all"
        self.tool_progress_mode = cycle[(idx + 1) % len(cycle)]

        if self.agent:
            self.agent.reasoning_callback = self._current_reasoning_callback()

        # Use raw ANSI codes via _cprint so the output is routed through
        # prompt_toolkit's renderer.  self.console.print() with Rich markup
        # writes directly to stdout which patch_stdout's StdoutProxy mangles
        # into garbled sequences like '?[33mTool progress: NEW?[0m' (#2262).
        from reymen.reymen_cli.colors import Colors as _Colors
        labels = {
            "off": f"{_Colors.DIM}Tool progress: OFF{_Colors.RESET} — silent mode, just the final response.",
            "new": f"{_Colors.YELLOW}Tool progress: NEW{_Colors.RESET} — show each new tool (skip repeats).",
            "all": f"{_Colors.GREEN}Tool progress: ALL{_Colors.RESET} — show every tool call.",
            "verbose": f"{_Colors.BOLD}{_Colors.GREEN}Tool progress: VERBOSE{_Colors.RESET} — full args, results, and think blocks.",
        }
        _cprint(labels.get(self.tool_progress_mode, ""))

    def _transfer_session_yolo(self, old_session_id: str, new_session_id: str) -> None:
        """Move YOLO bypass state from an old session key to a new one.

        Called whenever ``self.session_id`` is reassigned mid-run — ``/branch``
        forks into a new session, and auto-compression rotates the agent's
        session id into a fresh continuation session. Without this transfer
        the user's ``/yolo ON`` toggle would silently revert on the very next
        turn (the same UX failure mode that motivated this entire fix), since
        ``_session_yolo`` is keyed by session id.

        Mirrors ``tui_gateway/server.py`` (~line 1297-1305) which performs the
        same transfer for the TUI's session-rename path. No-op when YOLO
        wasn't enabled or when the ids match.
        """
        if not old_session_id or not new_session_id or old_session_id == new_session_id:
            return
        try:
            from tools.approval import (
                disable_session_yolo,
                enable_session_yolo,
                is_session_yolo_enabled,
            )
        except Exception:
            return
        if is_session_yolo_enabled(old_session_id):
            enable_session_yolo(new_session_id)
            disable_session_yolo(old_session_id)

    def _is_session_yolo_active(self) -> bool:
        """Whether YOLO bypass is currently enabled for this CLI session.

        Reads from ``tools.approval._session_yolo`` (the same set that
        ``enable_session_yolo`` / ``disable_session_yolo`` write to) so the
        status bar reflects the actual bypass state instead of a stale env
        var. Also honors the process-start ``--yolo`` flag, which freezes
        ``ReYMeN_YOLO_MODE`` into ``_YOLO_MODE_FROZEN`` before tool imports
        happen.
        """
        try:
            from tools.approval import (
                _YOLO_MODE_FROZEN,
                is_session_yolo_enabled,
            )
        except Exception:
            return False
        if _YOLO_MODE_FROZEN:
            return True
        # Use ``getattr`` so test fixtures that build a CLI via ``__new__``
        # (skipping ``__init__``) don't trip an AttributeError here; the
        # status-bar builders swallow exceptions silently but lose every
        # field after the failure.
        session_key = getattr(self, "session_id", None) or "default"
        return is_session_yolo_enabled(session_key)

    def _toggle_yolo(self):
        """Toggle YOLO mode — skip all dangerous command approval prompts.

        Per-session toggle that mirrors the gateway and TUI ``/yolo`` handlers
        (see ``gateway/run.py:_handle_yolo_command`` and
        ``tui_gateway/server.py`` key=="yolo"). We deliberately do NOT mutate
        ``ReYMeN_YOLO_MODE`` here — that env var is read once at module import
        time into ``tools.approval._YOLO_MODE_FROZEN`` to keep prompt-injected
        skills from flipping the bypass mid-session, so setting it after CLI
        startup is a silent no-op. Routing through ``enable_session_yolo`` /
        ``disable_session_yolo`` gives the same auditable, per-session bypass
        the other surfaces have. ``run_conversation`` binds
        ``self.session_id`` as the active approval session key via
        ``set_current_session_key`` so the bypass takes effect on the very
        next dangerous command in this run.
        """
        from reymen.reymen_cli.colors import Colors as _Colors
        from tools.approval import (
            disable_session_yolo,
            enable_session_yolo,
            is_session_yolo_enabled,
        )

        session_key = self.session_id or "default"
        if is_session_yolo_enabled(session_key):
            disable_session_yolo(session_key)
            _cprint(
                f"  ⚠ YOLO mode {_Colors.BOLD}{_Colors.RED}OFF{_Colors.RESET}"
                " — dangerous commands will require approval."
            )
        else:
            enable_session_yolo(session_key)
            _cprint(
                f"  ⚡ YOLO mode {_Colors.BOLD}{_Colors.GREEN}ON{_Colors.RESET}"
                " — all commands auto-approved. Use with caution."
            )

    # Moved to cli_mixin_agentsettings.py (MixinAgentSettings._handle_reasoning_command)
    # Moved to cli_mixin_agentsettings.py (MixinAgentSettings._handle_busy_command)
    # Moved to cli_mixin_agentsettings.py (MixinAgentSettings._handle_fast_command)
    def _on_reasoning(self, reasoning_text: str):
        """Callback for intermediate reasoning display during tool-call loops."""
        if not reasoning_text:
            return
        self._reasoning_preview_buf = getattr(self, "_reasoning_preview_buf", "") + reasoning_text
        self._flush_reasoning_preview(force=False)

    def _manual_compress(self, cmd_original: str = ""):
        """Manually trigger context compression on the current conversation.

        Two modes:

        * ``/compress [<focus>]`` — compress the *whole* history. An
          optional focus topic guides the summariser to preserve
          information related to *focus* while being more aggressive
          about discarding everything else.  Inspired by Claude Code's
          ``/compact <focus>`` feature.
        * ``/compress here [N]`` — boundary-aware compression. Summarize
          everything *except* the most recent ``N`` exchanges (default
          2), which are preserved verbatim. Inspired by Claude Code's
          Rewind "Summarize up to here" action (v2.1.139, May 2026,
          https://code.claude.com/docs/en/whats-new/2026-w20). Lets the
          user pick the compression boundary instead of leaving it to
          the automatic token-budget heuristic.
        """
        if not self.conversation_history or len(self.conversation_history) < 4:
            print("(._.) Not enough conversation to compress (need at least 4 messages).")
            return

        if not self.agent:
            print("(._.) No active agent -- send a message first.")
            return

        if not self.agent.compression_enabled:
            print("(._.) Compression is disabled in config.")
            return

        from reymen.reymen_cli.partial_compress import (
            parse_partial_compress_args,
            rejoin_compressed_head_and_tail,
            split_history_for_partial_compress,
        )

        # Args after the command word (e.g. "/compress here 3" -> "here 3").
        raw_args = ""
        if cmd_original:
            _parts = cmd_original.strip().split(None, 1)
            if len(_parts) > 1:
                raw_args = _parts[1].strip()

        partial, keep_last, focus_topic = parse_partial_compress_args(raw_args)
        focus_topic = focus_topic or ""

        original_count = len(self.conversation_history)
        with self._busy_command("Compressing context..."):
            try:
                from agent.model_metadata import estimate_request_tokens_rough
                from agent.manual_compression_feedback import summarize_manual_compression
                original_history = list(self.conversation_history)

                # Boundary-aware split: only the head is summarized; the
                # most recent `keep_last` exchanges ride along verbatim.
                tail: list = []
                head = original_history
                if partial:
                    head, tail = split_history_for_partial_compress(
                        original_history, keep_last
                    )
                    if not tail:
                        # Split degenerated (everything would be kept, or
                        # no head left to compress). Fall back to full
                        # compression so the user still gets an action.
                        partial = False
                        head = original_history

                # Include system prompt + tool schemas in the estimate —
                # a transcript-only number understates real request pressure
                # and can even appear to grow after compression because a
                # dense handoff summary replaces many short turns (#6217).
                _sys_prompt = getattr(self.agent, "_cached_system_prompt", "") or ""
                _tools = getattr(self.agent, "tools", None) or None
                approx_tokens = estimate_request_tokens_rough(
                    original_history,
                    system_prompt=_sys_prompt,
                    tools=_tools,
                )
                if partial:
                    print(f"🗜️  Summarizing up to here: compressing {len(head)} of "
                          f"{original_count} messages (~{approx_tokens:,} tokens), "
                          f"keeping last {keep_last} exchange(s) verbatim...")
                elif focus_topic:
                    print(f"🗜️  Compressing {original_count} messages (~{approx_tokens:,} tokens), "
                          f"focus: \"{focus_topic}\"...")
                else:
                    print(f"🗜️  Compressing {original_count} messages (~{approx_tokens:,} tokens)...")

                # Pass None as system_message so _compress_context rebuilds
                # the system prompt from scratch via _build_system_prompt(None).
                # Passing _cached_system_prompt caused duplication because
                # _build_system_prompt appends system_message to prompt_parts
                # which already contain the agent identity — resulting in the
                # identity block appearing twice (issue #15281).
                compressed, _ = self.agent._compress_context(
                    head,
                    None,
                    approx_tokens=approx_tokens,
                    focus_topic=focus_topic or None,
                    force=True,
                )
                # Re-append the verbatim tail after the compressed head.
                # The split guarantees `tail` begins on a user turn, so the
                # compressed-head -> tail boundary is normally valid
                # (the head's compressed output ends on assistant/tool).
                # rejoin_compressed_head_and_tail() additionally guards the
                # seam against any illegal user->user / assistant->assistant
                # adjacency, defending provider role-alternation rules.
                if partial and tail:
                    compressed = rejoin_compressed_head_and_tail(compressed, tail)
                self.conversation_history = compressed
                # _compress_context ends the old session and creates a new child
                # session on the agent (run_agent.py::_compress_context). Sync the
                # CLI's session_id so /status, /resume, exit summary, and title
                # generation all point at the live continuation session, not the
                # ended parent. Without this, subsequent end_session() calls target
                # the already-closed parent and the child is orphaned.
                if (
                    getattr(self.agent, "session_id", None)
                    and self.agent.session_id != self.session_id
                ):
                    self.session_id = self.agent.session_id
                    self._pending_title = None
                    # Manual /compress replaces conversation_history with a new
                    # compressed handoff for the child session. Persist it from
                    # offset 0 so resume can recover the continuation after exit.
                    self.agent._flush_messages_to_session_db(self.conversation_history, None)
                new_tokens = estimate_request_tokens_rough(
                    self.conversation_history,
                    system_prompt=_sys_prompt,
                    tools=_tools,
                )
                summary = summarize_manual_compression(
                    original_history,
                    self.conversation_history,
                    approx_tokens,
                    new_tokens,
                )
                icon = "🗜️" if summary["noop"] else "✅"
                print(f"  {icon} {summary['headline']}")
                print(f"     {summary['token_line']}")
                if summary["note"]:
                    print(f"     {summary['note']}")

            except Exception as e:
                print(f"  ❌ Compression failed: {e}")

    # Moved to cli_mixin_fileops.py (MixinFileOps._handle_debug_command)
    # Moved to cli_mixin_fileops.py (MixinFileOps._handle_update_command)
    def _check_config_mcp_changes(self) -> None:
        """Detect mcp_servers changes in config.yaml and auto-reload MCP connections.

        Called from process_loop every CONFIG_WATCH_INTERVAL seconds.
        Compares config.yaml mtime + mcp_servers section against the last
        known state.  When a change is detected, triggers _reload_mcp() and
        informs the user so they know the tool list has been refreshed.
        """
        import yaml as _yaml

        CONFIG_WATCH_INTERVAL = 5.0  # seconds between config.yaml stat() calls

        now = time.monotonic()
        if now - self._last_config_check < CONFIG_WATCH_INTERVAL:
            return
        self._last_config_check = now

        from reymen.reymen_cli.config import get_config_path as _get_config_path
        cfg_path = _get_config_path()
        if not cfg_path.exists():
            return

        try:
            mtime = cfg_path.stat().st_mtime
        except OSError:
            return

        if mtime == self._config_mtime:
            return  # File unchanged — fast path

        # File changed — check whether mcp_servers section changed
        self._config_mtime = mtime
        try:
            with open(cfg_path, encoding="utf-8") as f:
                new_cfg = _yaml.safe_load(f) or {}
        except Exception:
            return

        new_mcp = new_cfg.get("mcp_servers") or {}
        if new_mcp == self._config_mcp_servers:
            return  # mcp_servers unchanged (some other section was edited)

        self._config_mcp_servers = new_mcp
        # Notify user and reload.  Run in a separate thread with a hard
        # timeout so a hung MCP server cannot block the process_loop
        # indefinitely (which would freeze the entire TUI).
        print()
        print("🔄 MCP server config changed — reloading connections...")
        _reload_thread = threading.Thread(
            target=self._reload_mcp, daemon=True
        )
        _reload_thread.start()
        _reload_thread.join(timeout=30)
        if _reload_thread.is_alive():
            print("  ⚠️  MCP reload timed out (30s). Some servers may not have reconnected.")

    # Inline-skip tokens that bypass the destructive-slash confirmation modal.
    # Matches the escape-hatch pattern users on broken modal platforms
    # (currently native Windows PowerShell — issue #30768) need to self-serve
    # without having to flip approvals.destructive_slash_confirm in config.
    _DESTRUCTIVE_SKIP_TOKENS = frozenset({"now", "--yes", "-y"})

    @classmethod
    def _split_destructive_skip(cls, cmd_text: Optional[str]) -> tuple[str, bool]:
        """Split inline-skip tokens out of a destructive slash command.

        Returns ``(remainder, skip)`` where ``remainder`` is the original
        text with the command word and any recognized skip tokens removed,
        and ``skip`` is True iff at least one skip token was found.

        Examples:
            "/reset now"            -> ("", True)
            "/reset --yes My title" -> ("My title", True)
            "/new My title"         -> ("My title", False)
            "/clear"                -> ("", False)
        """
        if not cmd_text:
            return "", False
        tokens = cmd_text.strip().split()
        if not tokens:
            return "", False
        # Drop leading "/cmd" word — callers pass the full command text.
        if tokens[0].startswith("/"):
            tokens = tokens[1:]
        skip = False
        kept: list[str] = []
        for tok in tokens:
            if tok.lower() in cls._DESTRUCTIVE_SKIP_TOKENS:
                skip = True
                continue
            kept.append(tok)
        return " ".join(kept), skip

    def _confirm_destructive_slash(
        self,
        command: str,
        detail: str,
        cmd_original: Optional[str] = None,
    ) -> Optional[str]:
        """Prompt the user to confirm a destructive session slash command.

        Used by ``/clear``, ``/new``/``/reset``, and ``/undo`` before they
        discard conversation state.  Three-option prompt:

          1. Approve Once — proceed this time only
          2. Always Approve — proceed and persist
             ``approvals.destructive_slash_confirm: false`` so future
             destructive commands run without confirmation
          3. Cancel — abort

        Gated by ``approvals.destructive_slash_confirm`` (default on).  If the
        gate is off the function returns ``"once"`` immediately without
        prompting.

        Inline-skip: if ``cmd_original`` contains ``now``, ``--yes``, or
        ``-y`` as an argument (e.g. ``/reset now``, ``/new --yes My title``),
        the modal is bypassed and ``"once"`` is returned immediately. This is
        an escape hatch for platforms where the prompt_toolkit modal hangs
        (issue #30768 — native Windows PowerShell). Callers are responsible
        for stripping the skip tokens from any remaining argument parsing
        (see :meth:`_split_destructive_skip`).

        Returns ``"once"``, ``"always"``, or ``None`` (cancelled).  Callers
        proceed with the destructive action when the result is non-None.
        """
        # Inline-skip escape hatch — works regardless of platform/modal state.
        # See class-level _DESTRUCTIVE_SKIP_TOKENS for the accepted tokens.
        if cmd_original:
            _, _skip = self._split_destructive_skip(cmd_original)
            if _skip:
                return "once"

        # Gate check — respects prior "Always Approve" clicks.
        try:
            cfg = load_cli_config()
            approvals = cfg.get("approvals") if isinstance(cfg, dict) else None
            confirm_required = True
            if isinstance(approvals, dict):
                confirm_required = bool(approvals.get("destructive_slash_confirm", True))
        except Exception:
            confirm_required = True

        if not confirm_required:
            return "once"

        # Render a prompt_toolkit-native confirmation panel.  This keeps option
        # labels visible above the composer and avoids raw input()/EOF races with
        # the running TUI.
        choices = [
            ("once", "Approve Once", "proceed this time only"),
            ("always", "Always Approve", "proceed and silence this prompt permanently"),
            ("cancel", "Cancel", "keep current conversation"),
        ]
        raw = self._prompt_text_input_modal(
            title=f"⚠️  /{command} — destroys conversation state",
            detail=detail,
            choices=choices,
        )
        if raw is None:
            print(f"🟡 /{command} cancelled (no input).")
            return None
        choice = self._normalize_slash_confirm_choice(raw, choices)
        if choice is None:
            print(f"🟡 Unrecognized choice '{raw}'. /{command} cancelled.")
            return None

        if choice == "cancel":
            print(f"🟡 /{command} cancelled. Conversation unchanged.")
            return None

        if choice == "always":
            if save_config_value("approvals.destructive_slash_confirm", False):
                print("🔒 Future /clear, /new, /reset, and /undo will run without confirmation.")
                print("   Re-enable via `approvals.destructive_slash_confirm: true` in config.yaml.")
            else:
                print("⚠️  Couldn't persist opt-out — proceeding once.")

        return choice

    def _confirm_and_reload_mcp(self, cmd_original: str = "") -> None:
        """Interactive /reload-mcp — confirm with the user, then reload.

        Reloading MCP tools invalidates the provider prompt cache for the
        active session (tool schemas are baked into the system prompt).
        The next message re-sends full input tokens — can be expensive on
        long-context or high-reasoning models.

        Three options: Approve Once, Always Approve (persists
        ``approvals.mcp_reload_confirm: false`` so future reloads run
        without this prompt), Cancel.  Gated by
        ``approvals.mcp_reload_confirm`` — default on.
        """
        # Gate check — respects prior "Always Approve" clicks.
        try:
            cfg = load_cli_config()
            approvals = cfg.get("approvals") if isinstance(cfg, dict) else None
            confirm_required = True
            if isinstance(approvals, dict):
                confirm_required = bool(approvals.get("mcp_reload_confirm", True))
        except Exception:
            confirm_required = True

        if not confirm_required:
            with self._busy_command(self._slow_command_status(cmd_original)):
                self._reload_mcp()
            return

        # Render warning + prompt.  Use the same prompt_toolkit-native composer
        # modal as destructive slash confirmations so choices stay visible.
        choices = [
            ("once", "Approve Once", "reload now"),
            ("always", "Always Approve", "reload now and silence this prompt permanently"),
            ("cancel", "Cancel", "leave MCP tools unchanged"),
        ]
        raw = self._prompt_text_input_modal(
            title="⚠️  /reload-mcp — Prompt cache invalidation warning",
            detail=(
                "Reloading MCP servers rebuilds the tool set for this session and\n"
                "invalidates the provider prompt cache. The next message will\n"
                "re-send full input tokens (can be expensive on long-context or\n"
                "high-reasoning models)."
            ),
            choices=choices,
        )
        if raw is None:
            print("🟡 /reload-mcp cancelled (no input).")
            return
        choice = self._normalize_slash_confirm_choice(raw, choices)
        if choice is None:
            print(f"🟡 Unrecognized choice '{raw}'. /reload-mcp cancelled.")
            return

        if choice == "cancel":
            print("🟡 /reload-mcp cancelled. MCP tools unchanged.")
            return

        if choice == "always":
            if save_config_value("approvals.mcp_reload_confirm", False):
                print("🔒 Future /reload-mcp calls will run without confirmation.")
                print("   Re-enable via `approvals.mcp_reload_confirm: true` in config.yaml.")
            else:
                print("⚠️  Couldn't persist opt-out — reloading once.")

        with self._busy_command(self._slow_command_status(cmd_original)):
            self._reload_mcp()

    def _reload_mcp(self):
        """Reload MCP servers: disconnect all, re-read config.yaml, reconnect.

        After reconnecting, refreshes the agent's tool list so the model
        sees the updated tools on the next turn.
        """
        try:
            from tools.mcp_tool import shutdown_mcp_servers, discover_mcp_tools, _servers, _lock

            # Capture old server names
            with _lock:
                old_servers = set(_servers.keys())

            if not self._command_running:
                print("🔄 Reloading MCP servers...")

            # Shutdown existing connections
            shutdown_mcp_servers()

            # Reconnect (reads config.yaml fresh)
            new_tools = discover_mcp_tools()

            # Compute what changed
            with _lock:
                connected_servers = set(_servers.keys())

            added = connected_servers - old_servers
            removed = old_servers - connected_servers
            reconnected = connected_servers & old_servers

            if reconnected:
                print(f"  ♻️  Reconnected: {', '.join(sorted(reconnected))}")
            if added:
                print(f"  ➕ Added: {', '.join(sorted(added))}")
            if removed:
                print(f"  ➖ Removed: {', '.join(sorted(removed))}")
            if not connected_servers:
                print("  No MCP servers connected.")
            else:
                print(f"  🔧 {len(new_tools)} tool(s) available from {len(connected_servers)} server(s)")

            # Refresh the agent's tool list so the model can call new tools
            if self.agent is not None:
                self.agent.tools = get_tool_definitions(
                    enabled_toolsets=self.agent.enabled_toolsets
                    if hasattr(self.agent, "enabled_toolsets") else None,
                    quiet_mode=True,
                )
                self.agent.valid_tool_names = {
                    tool["function"]["name"] for tool in self.agent.tools
                } if self.agent.tools else set()

            # Inject a message at the END of conversation history so the
            # model knows tools changed.  Appended after all existing
            # messages to preserve prompt-cache for the prefix.
            change_parts = []
            if added:
                change_parts.append(f"Added servers: {', '.join(sorted(added))}")
            if removed:
                change_parts.append(f"Removed servers: {', '.join(sorted(removed))}")
            if reconnected:
                change_parts.append(f"Reconnected servers: {', '.join(sorted(reconnected))}")
            tool_summary = f"{len(new_tools)} MCP tool(s) now available" if new_tools else "No MCP tools available"
            change_detail = ". ".join(change_parts) + ". " if change_parts else ""
            self.conversation_history.append({
                "role": "user",
                "content": f"[IMPORTANT: MCP servers have been reloaded. {change_detail}{tool_summary}. The tool list for this conversation has been updated accordingly.]",
            })

            # Persist session immediately so the session log reflects the
            # updated tools list (self.agent.tools was refreshed above).
            if self.agent is not None:
                try:
                    self.agent._persist_session(
                        self.conversation_history,
                        self.conversation_history,
                    )
                except Exception as _e:
                    __import__("logging").getLogger(__name__).warning(
                        "[SessizExcept] %%s: %%s", type(_e).__name__, _e
                    )  # Best-effort

            print(f"  ✅ Agent updated — {len(self.agent.tools if self.agent else [])} tool(s) available")

        except Exception as e:
            print(f"  ❌ MCP reload failed: {e}")

    def _reload_skills(self) -> None:
        """Reload skills: rescan ~/.ReYMeN/skills/ and queue a note for the
        next user turn.

        Skills don't need to live in the system prompt for the model to use
        them (they're invoked via ``/skill-name``, ``skills_list``, or
        ``skill_view`` at runtime), so this does NOT clear the prompt cache.
        It rescans the slash-command map, prints the diff for the user, and
        — if any skills were added or removed — queues a one-shot note that
        gets prepended to the next user message. This preserves message
        alternation (no phantom user turn injected out of band) and keeps
        prompt caching intact.
        """
        try:
            from agent.skill_commands import reload_skills, get_skill_commands

            if not self._command_running:
                print("🔄 Reloading skills...")

            result = reload_skills()

            # Sync cli.py's module-level _skill_commands so all consumers
            # (help display, command dispatch, Tab-completion lambda) see the
            # updated dict without needing to restart the session.
            global _skill_commands
            _skill_commands = get_skill_commands()
            added = result.get("added", [])      # [{"name", "description"}, ...]
            removed = result.get("removed", [])  # [{"name", "description"}, ...]
            total = result.get("total", 0)

            if not added and not removed:
                print("  No new skills detected.")
                print(f"  📚 {total} skill(s) available")
                return

            def _fmt_line(item: dict) -> str:
                nm = item.get("name", "")
                desc = item.get("description", "")
                return f"    - {nm}: {desc}" if desc else f"    - {nm}"

            if added:
                print("  ➕ Added Skills:")
                for item in added:
                    print(f"  {_fmt_line(item)}")
            if removed:
                print("  ➖ Removed Skills:")
                for item in removed:
                    print(f"  {_fmt_line(item)}")
            print(f"  📚 {total} skill(s) available")

            # Queue a one-shot note for the NEXT user turn. The CLI's agent
            # loop prepends ``_pending_skills_reload_note`` (if set) to the
            # API-call-local message at ~L8770, then clears it — same
            # pattern as ``_pending_model_switch_note``. Nothing is written
            # to conversation_history here, so message alternation stays
            # intact and no out-of-band user turn is persisted.
            #
            # Format matches how the system prompt renders pre-existing
            # skills (``    - name: description``) so the model reads the
            # diff in the same shape as its original skill catalog.
            sections = ["[USER INITIATED SKILLS RELOAD:"]
            if added:
                sections.append("")
                sections.append("Added Skills:")
                for item in added:
                    sections.append(_fmt_line(item))
            if removed:
                sections.append("")
                sections.append("Removed Skills:")
                for item in removed:
                    sections.append(_fmt_line(item))
            sections.append("")
            sections.append("Use skills_list to see the updated catalog.]")
            self._pending_skills_reload_note = "\n".join(sections)

        except Exception as e:
            print(f"  ❌ Skills reload failed: {e}")

    # ====================================================================
    # Tool-call generation indicator (shown during streaming)
    # ====================================================================

    def _on_tool_gen_start(self, tool_name: str) -> None:
        """Called when the model begins generating tool-call arguments.

        Closes any open streaming boxes (reasoning / response) exactly once,
        then prints a short status line so the user sees activity instead of
        a frozen screen while a large payload (e.g. 45 KB write_file) streams.
        """
        if getattr(self, "_stream_box_opened", False):
            self._flush_stream()
            self._stream_box_opened = False
        self._close_reasoning_box()

        from agent.display import get_tool_emoji
        emoji = get_tool_emoji(tool_name, default="⚡")
        _cprint(f"  ┊ {emoji} preparing {tool_name}…")

    # ====================================================================
    # Tool progress callback (audio cues for voice mode)
    # ====================================================================

    def _on_tool_progress(self, event_type: str, function_name: str = None, preview: str = None, function_args: dict = None, **kwargs):
        """Called on tool lifecycle events (tool.started, tool.completed, reasoning.available, etc.).

        Updates the TUI spinner widget so the user can see what the agent
        is doing during tool execution (fills the gap between thinking
        spinner and next response).

        On tool.started, records a monotonic timestamp so get_spinner_text()
        can show a live elapsed timer (the TUI poll loop already invalidates
        every ~0.15s, so the counter updates automatically).

        When tool_progress_mode is "all" or "new", also prints a persistent
        stacked line to scrollback on tool.completed so users can see the
        full history of tool calls (not just the current one in the spinner).
        """
        if event_type == "tool.completed":
            self._tool_start_time = 0.0
            # Print stacked scrollback line for "all" / "new" modes
            if function_name and self.tool_progress_mode in {"all", "new"}:
                duration = kwargs.get("duration", 0.0)
                is_error = kwargs.get("is_error", False)
                # Pop stored args from tool.started for this function
                stored = self._pending_tool_info.get(function_name)
                stored_args = stored.pop(0) if stored else {}
                if stored is not None and not stored:
                    del self._pending_tool_info[function_name]
                # "new" mode: skip consecutive repeats of the same tool
                if self.tool_progress_mode == "new" and function_name == self._last_scrollback_tool:
                    self._invalidate()
                    return
                self._last_scrollback_tool = function_name
                try:
                    from agent.display import get_cute_tool_message
                    line = get_cute_tool_message(function_name, stored_args, duration, result=kwargs.get("result"))
                    _cprint(f"  {line}")
                except Exception:
                    logger.warning("[fix_01_sessiz_except] Exception")
                # First-touch onboarding: on the first tool in this process
                # that takes longer than the threshold while we're in the
                # noisiest progress mode, print a one-time hint about
                # /verbose.  Latched on self so it fires at most once per
                # process; persisted to config.yaml so it never fires again
                # across processes either.
                try:
                    if (
                        not getattr(self, "_long_tool_hint_fired", False)
                        and self.tool_progress_mode == "all"
                        and duration >= 30.0
                    ):
                        from agent.onboarding import (
                            TOOL_PROGRESS_FLAG,
                            is_seen,
                            mark_seen,
                            tool_progress_hint_cli,
                        )
                        if not is_seen(CLI_CONFIG, TOOL_PROGRESS_FLAG):
                            self._long_tool_hint_fired = True
                            _cprint(f"  {_DIM}{tool_progress_hint_cli()}{_RST}")
                            mark_seen(_ReYMeN_home / "config.yaml", TOOL_PROGRESS_FLAG)
                            CLI_CONFIG.setdefault("onboarding", {}).setdefault("seen", {})[TOOL_PROGRESS_FLAG] = True
                except Exception:
                    logger.warning("[fix_01_sessiz_except] Exception")
            self._invalidate()
            return
        if event_type != "tool.started":
            return
        if function_name and not function_name.startswith("_"):
            from agent.display import get_tool_emoji
            emoji = get_tool_emoji(function_name)
            label = preview or function_name
            from agent.display import get_tool_preview_max_len
            _pl = get_tool_preview_max_len()
            if _pl > 0 and len(label) > _pl:
                label = label[:_pl - 3] + "..."
            self._spinner_text = f"{emoji} {label}"
            self._tool_start_time = time.monotonic()
            # Store args for stacked scrollback line on completion
            self._pending_tool_info.setdefault(function_name, []).append(
                function_args if function_args is not None else {}
            )
            self._invalidate()

    def _on_tool_start(self, tool_call_id: str, function_name: str, function_args: dict):
        """Capture local before-state for write-capable tools."""
        try:
            from agent.display import capture_local_edit_snapshot

            snapshot = capture_local_edit_snapshot(function_name, function_args)
            if snapshot is not None:
                self._pending_edit_snapshots[tool_call_id] = snapshot
        except Exception:
            logger.debug("Edit snapshot capture failed for %s", function_name, exc_info=True)

    def _on_tool_complete(self, tool_call_id: str, function_name: str, function_args: dict, function_result: str):
        """Render file edits with inline diff after write-capable tools complete."""
        snapshot = self._pending_edit_snapshots.pop(tool_call_id, None)
        try:
            from agent.display import render_edit_diff_with_delta

            render_edit_diff_with_delta(
                function_name,
                function_result,
                function_args=function_args,
                snapshot=snapshot,
                print_fn=_cprint,
            )
        except Exception:
            logger.debug("Edit diff preview failed for %s", function_name, exc_info=True)

    # ====================================================================
    # Voice mode methods
    # ====================================================================

    # Moved to cli_mixin_media.py (MixinMedia._handle_voice_command)
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

    def _clarify_callback(self, question, choices):
        """
        Platform callback for the clarify tool. Called from the agent thread.

        Sets up the interactive selection UI (or freetext prompt for open-ended
        questions), then blocks until the user responds via the prompt_toolkit
        key bindings.  If no response arrives within the configured timeout the
        question is dismissed and the agent is told to decide on its own.
        """
        import time as _time

        timeout = CLI_CONFIG.get("clarify", {}).get("timeout", 120)
        response_queue = queue.Queue()
        is_open_ended = not choices

        self._clarify_state = {
            "question": question,
            "choices": choices if not is_open_ended else [],
            "selected": 0,
            "response_queue": response_queue,
        }
        self._clarify_deadline = _time.monotonic() + timeout
        # Open-ended questions skip straight to freetext input
        self._clarify_freetext = is_open_ended

        # Trigger prompt_toolkit repaint from this (non-main) thread
        self._invalidate()

        # Poll for the user's response.  The countdown in the hint line
        # updates on each invalidate — but frequent repaints cause visible
        # flicker in some terminals (Kitty, ghostty).  We only refresh the
        # countdown every 5 s; selection changes (↑/↓) trigger instant
        # Poll for the user's response.  The countdown in the hint line
        # updates on each invalidate — but frequent repaints cause visible
        # flicker in some terminals (Kitty, ghostty).  We only refresh the
        # countdown every 5 s; selection changes (↑/↓) trigger instant
        # repaints via the key bindings.
        _last_countdown_refresh = _time.monotonic()
        while True:
            try:
                result = response_queue.get(timeout=1)
                self._clarify_deadline = 0
                return result
            except queue.Empty:
                remaining = self._clarify_deadline - _time.monotonic()
                if remaining <= 0:
                    break
                # Only repaint every 5 s for the countdown — avoids flicker
                now = _time.monotonic()
                if now - _last_countdown_refresh >= 5.0:
                    _last_countdown_refresh = now
                    self._invalidate()
                if now - _last_countdown_refresh >= 5.0:
                    _last_countdown_refresh = now
                    self._invalidate()

        # Timed out — tear down the UI and let the agent decide
        self._clarify_state = None
        self._clarify_freetext = False
        self._clarify_deadline = 0
        self._invalidate()
        _cprint(f"\n{_DIM}(clarify timed out after {timeout}s — agent will decide){_RST}")
        return (
            "The user did not provide a response within the time limit. "
            "Use your best judgement to make the choice and proceed."
        )

    def _approval_choices(self, command: str, *, allow_permanent: bool = True) -> list[str]:
        """Return approval choices for a dangerous command prompt."""
        choices = ["once", "session", "always", "deny"] if allow_permanent else ["once", "session", "deny"]
        if len(command) > 70:
            choices.append("view")
        return choices

    def _computer_use_approval_callback(self, action: str, args: dict, summary: str) -> str:
        """Adapt the generic approval UI for the computer_use tool.

        The computer_use handler expects verdicts of the form
        `approve_once` | `approve_session` | `always_approve` | `deny`.
        The CLI's built-in approval UI returns `once` | `session` | `always`
        | `deny`. Translate between the two.
        """
        # Build a command-ish string so the existing UI renders something
        # meaningful. `summary` is already a one-line human description.
        verdict = self._approval_callback(
            command=f"computer_use: {summary}",
            description=f"Allow computer_use to perform `{action}`?",
        )
        return {
            "once": "approve_once",
            "session": "approve_session",
            "always": "always_approve",
            "deny": "deny",
        }.get(verdict, "deny")

    def _handle_approval_selection(self) -> None:
        """Process the currently selected dangerous-command approval choice."""
        state = self._approval_state
        if not state:
            return

        selected = state.get("selected", 0)
        choices = state.get("choices")
        if not isinstance(choices, list):
            choices = []
        if not (0 <= selected < len(choices)):
            return

        chosen = choices[selected]
        if chosen == "view":
            state["show_full"] = True
            state["choices"] = [choice for choice in choices if choice != "view"]
            if state["selected"] >= len(state["choices"]):
                state["selected"] = max(0, len(state["choices"]) - 1)
            self._invalidate()
            return

        state["response_queue"].put(chosen)
        self._approval_state = None
        self._invalidate()

    def _clear_secret_input_buffer(self) -> None:
        if getattr(self, "_app", None):
            try:
                self._app.current_buffer.reset()
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")

def _run_kanban_goal_loop_q(cli: "ReYMeNCLI", first_response: str) -> None:
    """Drive a kanban goal_mode worker through the Ralph-style goal loop.

    Called from the quiet single-query path AFTER the worker's first turn,
    only when ``ReYMeN_KANBAN_GOAL_MODE`` is set (dispatcher-spawned
    goal_mode card). Wires the worker's ``run_conversation`` and the kanban
    DB into ``goals.run_kanban_goal_loop``. All errors are swallowed by the
    caller — a broken goal loop must never wedge a worker, the dispatcher's
    claim TTL / crash detection is the backstop.
    """
    import os as _os

    task_id = (_os.environ.get("ReYMeN_KANBAN_TASK") or "").strip()
    if not task_id:
        return

    from ReYMeN_cli import kanban_db as _kb
    from reymen.reymen_cli.goals import run_kanban_goal_loop as _run_loop, DEFAULT_MAX_TURNS as _DEF_TURNS

    # Resolve goal text from the card (title + body = the acceptance
    # criteria the judge evaluates against).
    conn = _kb.connect()
    try:
        task = _kb.get_task(conn, task_id)
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("[fix_01_sessiz_except] Exception")
    if task is None:
        return

    goal_parts = [task.title or ""]
    if task.body:
        goal_parts.append(task.body)
    goal_text = "\n\n".join(p for p in goal_parts if p).strip()
    if not goal_text:
        return

    max_turns = task.goal_max_turns or _DEF_TURNS

    def _run_turn(prompt: str) -> str:
        result = cli.agent.run_conversation(
            user_message=prompt,
            conversation_history=cli.conversation_history,
        )
        # Keep session_id in sync if mid-run compression rotated it.
        if (
            getattr(cli.agent, "session_id", None)
            and cli.agent.session_id != cli.session_id
        ):
            cli.session_id = cli.agent.session_id
        resp = result.get("final_response", "") if isinstance(result, dict) else str(result)
        if resp:
            print(resp)
        return resp or ""

    def _task_status() -> "str | None":
        c = _kb.connect()
        try:
            t = _kb.get_task(c, task_id)
            return t.status if t is not None else None
        finally:
            try:
                c.close()
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")

    def _block(reason: str) -> None:
        c = _kb.connect()
        try:
            _kb.block_task(c, task_id, reason=reason)
        finally:
            try:
                c.close()
            except Exception:
                logger.warning("[fix_01_sessiz_except] Exception")

    _run_loop(
        task_id=task_id,
        goal_text=goal_text,
        run_turn=_run_turn,
        task_status_fn=_task_status,
        block_fn=_block,
        max_turns=max_turns,
        first_response=first_response or "",
        log=lambda m: logger.info("%s", m),
    )


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
        from reymen.reymen_cli.stdio import configure_windows_stdio
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
            from reymen.reymen_cli.config import load_config as _load_reymen_config
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
        from reymen.reymen_cli.tools_config import _get_platform_tools
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
                        from reymen.reymen_cli.config import load_config

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
