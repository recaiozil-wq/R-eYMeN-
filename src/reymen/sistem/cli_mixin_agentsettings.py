"""ReYMeNCLI mixin module — Agent settings (personality, reasoning, fast, busy, gquota, profile)."""

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

class MixinAgentSettings:
    """ReYMeNCLI Agent settings — personality, reasoning, fast, busy, gquota, profile."""


    def _handle_profile_command(self):
        """Display active profile name and home directory."""
        from reymen.sistem.ReYMeN_constants import display_reymen_home
        from reymen.reymen_cli.profiles import get_active_profile_name

        display = display_reymen_home()
        profile_name = get_active_profile_name()

        print()
        print(f"  Profile: {profile_name}")
        print(f"  Home:    {display}")
        print()


    def _handle_gquota_command(self, cmd_original: str) -> None:
        """Show Google Gemini Code Assist quota usage for the current OAuth account."""
        try:
            from agent.google_oauth import get_valid_access_token, GoogleOAuthError, load_credentials
            from agent.google_code_assist import retrieve_user_quota, CodeAssistError
        except ImportError as exc:
            self._console_print(f"  [red]Gemini modules unavailable: {exc}[/]")
            return

        try:
            access_token = get_valid_access_token()
        except GoogleOAuthError as exc:
            self._console_print(f"  [yellow]{exc}[/]")
            self._console_print("  Run [bold]/model[/] and pick 'Google Gemini (OAuth)' to sign in.")
            return

        creds = load_credentials()
        project_id = (creds.project_id if creds else "") or ""

        try:
            buckets = retrieve_user_quota(access_token, project_id=project_id)
        except CodeAssistError as exc:
            self._console_print(f"  [red]Quota lookup failed:[/] {exc}")
            return

        if not buckets:
            self._console_print("  [dim]No quota buckets reported (account may be on legacy/unmetered tier).[/]")
            return

        # Sort for stable display, group by model
        buckets.sort(key=lambda b: (b.model_id, b.token_type))
        self._console_print()
        self._console_print(f"  [bold]Gemini Code Assist quota[/]  (project: {project_id or '(auto / free-tier)'})")
        self._console_print()
        for b in buckets:
            pct = max(0.0, min(1.0, b.remaining_fraction))
            width = 20
            filled = int(round(pct * width))
            bar = "▓" * filled + "░" * (width - filled)
            pct_str = f"{int(pct * 100):3d}%"
            header = b.model_id
            if b.token_type:
                header += f" [{b.token_type}]"
            self._console_print(f"    {header:40s}  {bar}  {pct_str}")
        self._console_print()


    def _handle_personality_command(self, cmd: str):
        """Handle the /personality command to set predefined personalities."""
        parts = cmd.split(maxsplit=1)
        
        if len(parts) > 1:
            # Set personality
            personality_name = parts[1].strip().lower()
            
            if personality_name in {"none", "default", "neutral"}:
                self.system_prompt = ""
                self.agent = None  # Force re-init
                if save_config_value("agent.system_prompt", ""):
                    print("(^_^)b Personality cleared (saved to config)")
                else:
                    print("(^_^) Personality cleared (session only)")
                print("  No personality overlay — using base agent behavior.")
            elif personality_name in self.personalities:
                self.system_prompt = self._resolve_personality_prompt(self.personalities[personality_name])
                self.agent = None  # Force re-init
                if save_config_value("agent.system_prompt", self.system_prompt):
                    print(f"(^_^)b Personality set to '{personality_name}' (saved to config)")
                else:
                    print(f"(^_^) Personality set to '{personality_name}' (session only)")
                print(f"  \"{self.system_prompt[:60]}{'...' if len(self.system_prompt) > 60 else ''}\"")
            else:
                print(f"(._.) Unknown personality: {personality_name}")
                print(f"  Available: none, {', '.join(self.personalities.keys())}")
        else:
            # Show available personalities
            print()
            print("+" + "-" * 50 + "+")
            print("|" + " " * 12 + "(^o^)/ Personalities" + " " * 15 + "|")
            print("+" + "-" * 50 + "+")
            print()
            print(f"  {'none':<12} - (no personality overlay)")
            for name, prompt in self.personalities.items():
                if isinstance(prompt, dict):
                    preview = prompt.get("description") or prompt.get("system_prompt", "")[:50]
                else:
                    preview = str(prompt)[:50]
                print(f"  {name:<12} - {preview}")
            print()
            print("  Usage: /personality <name>")
            print()


    def _handle_reasoning_command(self, cmd: str):
        """Handle /reasoning — manage effort level and display toggle.

        Usage:
            /reasoning              Show current effort level and display state
            /reasoning <level>      Set reasoning effort (none, minimal, low, medium, high, xhigh)
            /reasoning show|on      Show model thinking/reasoning in output
            /reasoning hide|off     Hide model thinking/reasoning from output
        """
        parts = cmd.strip().split(maxsplit=1)

        if len(parts) < 2:
            # Show current state
            rc = self.reasoning_config
            if rc is None:
                level = "medium (default)"
            elif rc.get("enabled") is False:
                level = "none (disabled)"
            else:
                level = rc.get("effort", "medium")
            display_state = "on ✓" if self.show_reasoning else "off"
            _cprint(f"  {_ACCENT}Reasoning effort:  {level}{_RST}")
            _cprint(f"  {_ACCENT}Reasoning display: {display_state}{_RST}")
            _cprint(f"  {_DIM}Usage: /reasoning <none|minimal|low|medium|high|xhigh|show|hide>{_RST}")
            return

        arg = parts[1].strip().lower()

        # Display toggle
        if arg in {"show", "on"}:
            self.show_reasoning = True
            if self.agent:
                self.agent.reasoning_callback = self._current_reasoning_callback()
            save_config_value("display.show_reasoning", True)
            _cprint(f"  {_ACCENT}✓ Reasoning display: ON (saved){_RST}")
            _cprint(f"  {_DIM}  Model thinking will be shown during and after each response.{_RST}")
            return
        if arg in {"hide", "off"}:
            self.show_reasoning = False
            if self.agent:
                self.agent.reasoning_callback = self._current_reasoning_callback()
            save_config_value("display.show_reasoning", False)
            _cprint(f"  {_ACCENT}✓ Reasoning display: OFF (saved){_RST}")
            return

        # Effort level change
        parsed = _parse_reasoning_config(arg)
        if parsed is None:
            _cprint(f"  {_DIM}(._.) Unknown argument: {arg}{_RST}")
            _cprint(f"  {_DIM}Valid levels: none, minimal, low, medium, high, xhigh{_RST}")
            _cprint(f"  {_DIM}Display:      show, hide{_RST}")
            return

        self.reasoning_config = parsed
        self.agent = None  # Force agent re-init with new reasoning config

        if save_config_value("agent.reasoning_effort", arg):
            _cprint(f"  {_ACCENT}✓ Reasoning effort set to '{arg}' (saved to config){_RST}")
        else:
            _cprint(f"  {_ACCENT}✓ Reasoning effort set to '{arg}' (session only){_RST}")


    def _handle_busy_command(self, cmd: str):
        """Handle /busy — control what Enter does while ReYMeN is working.

        Usage:
            /busy               Show current busy input mode
            /busy status        Show current busy input mode
            /busy queue         Queue input for the next turn instead of interrupting
            /busy steer         Inject Enter mid-run via /steer (after next tool call)
            /busy interrupt     Interrupt the current run on Enter (default)
        """
        parts = cmd.strip().split(maxsplit=1)
        if len(parts) < 2 or parts[1].strip().lower() == "status":
            _cprint(f"  {_ACCENT}Busy input mode: {self.busy_input_mode}{_RST}")
            if self.busy_input_mode == "queue":
                _behavior = "queues for next turn"
            elif self.busy_input_mode == "steer":
                _behavior = "steers into current run (after next tool call)"
            else:
                _behavior = "interrupts current run"
            _cprint(f"  {_DIM}Enter while busy: {_behavior}{_RST}")
            _cprint(f"  {_DIM}Usage: /busy [queue|steer|interrupt|status]{_RST}")
            return

        arg = parts[1].strip().lower()
        if arg not in {"queue", "interrupt", "steer"}:
            _cprint(f"  {_DIM}(._.) Unknown argument: {arg}{_RST}")
            _cprint(f"  {_DIM}Usage: /busy [queue|steer|interrupt|status]{_RST}")
            return

        self.busy_input_mode = arg
        if save_config_value("display.busy_input_mode", arg):
            if arg == "queue":
                behavior = "Enter will queue follow-up input while ReYMeN is busy."
            elif arg == "steer":
                behavior = "Enter will steer your message into the current run (after the next tool call)."
            else:
                behavior = "Enter will interrupt the current run while ReYMeN is busy."
            _cprint(f"  {_ACCENT}✓ Busy input mode set to '{arg}' (saved to config){_RST}")
            _cprint(f"  {_DIM}{behavior}{_RST}")
        else:
            _cprint(f"  {_ACCENT}✓ Busy input mode set to '{arg}' (session only){_RST}")


    def _handle_fast_command(self, cmd: str):
        """Handle /fast — toggle fast mode (OpenAI Priority Processing / Anthropic Fast Mode)."""
        if not self._fast_command_available():
            _cprint("  (._.) /fast is only available for models that support fast mode (OpenAI Priority Processing or Anthropic Fast Mode).")
            return

        # Determine the branding for the current model
        try:
            from reymen.reymen_cli.models import _is_anthropic_fast_model
            agent = getattr(self, "agent", None)
            model = getattr(agent, "model", None) or getattr(self, "model", None)
            feature_name = "Anthropic Fast Mode" if _is_anthropic_fast_model(model) else "Priority Processing"
        except Exception:
            feature_name = "Fast mode"

        parts = cmd.strip().split(maxsplit=1)
        if len(parts) < 2 or parts[1].strip().lower() == "status":
            status = "fast" if self.service_tier == "priority" else "normal"
            _cprint(f"  {_ACCENT}{feature_name}: {status}{_RST}")
            _cprint(f"  {_DIM}Usage: /fast [normal|fast|status]{_RST}")
            return

        arg = parts[1].strip().lower()

        if arg in {"fast", "on"}:
            self.service_tier = "priority"
            saved_value = "fast"
            label = "FAST"
        elif arg in {"normal", "off"}:
            self.service_tier = None
            saved_value = "normal"
            label = "NORMAL"
        else:
            _cprint(f"  {_DIM}(._.) Unknown argument: {arg}{_RST}")
            _cprint(f"  {_DIM}Usage: /fast [normal|fast|status]{_RST}")
            return

        self.agent = None  # Force agent re-init with new service-tier config
        if save_config_value("agent.service_tier", saved_value):
            _cprint(f"  {_ACCENT}✓ {feature_name} set to {label} (saved to config){_RST}")
        else:
            _cprint(f"  {_ACCENT}✓ {feature_name} set to {label} (session only){_RST}")


__all__ = ['MixinAgentSettings']
