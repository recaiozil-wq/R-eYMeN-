"""_handle_codex_runtime handler."""


def _handle_codex_runtime(cli, cmd_original: str) -> None:
    """Handle /codex-runtime — toggle the codex app-server runtime opt-in.

    Usage:
        /codex-runtime                       — show current state
        /codex-runtime auto                  — ReYMeN default (chat_completions)
        /codex-runtime codex_app_server      — hand turns to codex subprocess
        /codex-runtime on / off              — synonyms for the above
    """
    from ReYMeN_cli import codex_runtime_switch as crs
    from reymen.sistem.cli_display import _cprint

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
