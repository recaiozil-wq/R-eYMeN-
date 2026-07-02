"""_handle_bundles_command handler."""


def _handle_bundles_command(cli, cmd: str) -> None:
    """In-session ``/bundles`` — show installed skill bundles.

    Mirrors ``ReYMeN bundles list`` but renders inside the running
    CLI so users can discover what's available without dropping out
    of their session. Bundles are loaded via ``/<bundle-name>``.
    """
    from reymen.sistem.cli_display import _cprint, _RST, _DIM, _BOLD, _accent_hex
    from reymen.sistem.cli_stream import ChatConsole
    from rich.markup import escape as _escape

    try:
        from agent.skill_bundles import list_bundles, _bundles_dir
    except Exception as exc:
        _cprint(f"\033[1;31mBundle subsystem unavailable: {exc}\033[0m")
        return

    bundles = list_bundles()
    if not bundles:
        _cprint("  No skill bundles installed.")
        _cprint(
            f"  {_DIM}Create one with: ReYMeN bundles create "
            f"<name> --skill <s1> --skill <s2>{_RST}"
        )
        _cprint(f"  {_DIM}Directory: {_bundles_dir()}{_RST}")
        return

    _cprint(f"\n  ▣ {_BOLD}Skill Bundles{_RST} ({len(bundles)} installed):")
    for info in bundles:
        skill_count = len(info.get("skills", []))
        desc = info.get("description") or f"Load {skill_count} skills"
        ChatConsole().print(
            f"    [bold {_accent_hex()}]/{info['slug']:<20}[/] "
            f"[dim]-[/] {_escape(desc)} [dim]({skill_count} skills)[/]"
        )
        for s in info.get("skills", []):
            ChatConsole().print(f"        [dim]· {_escape(s)}[/]")
    _cprint(
        f"\n  {_DIM}Invoke a bundle with /<slug>. "
        f"Manage with `ReYMeN bundles`.{_RST}"
    )
