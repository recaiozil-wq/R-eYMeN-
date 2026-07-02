"""_handle_gquota_command handler."""


def _handle_gquota_command(cli, cmd_original: str) -> None:
    """Show Google Gemini Code Assist quota usage for the current OAuth account."""
    try:
        from agent.google_oauth import get_valid_access_token, GoogleOAuthError, load_credentials
        from agent.google_code_assist import retrieve_user_quota, CodeAssistError
    except ImportError as exc:
        cli._console_print(f"  [red]Gemini modules unavailable: {exc}[/]")
        return

    try:
        access_token = get_valid_access_token()
    except GoogleOAuthError as exc:
        cli._console_print(f"  [yellow]{exc}[/]")
        cli._console_print("  Run [bold]/model[/] and pick 'Google Gemini (OAuth)' to sign in.")
        return

    creds = load_credentials()
    project_id = (creds.project_id if creds else "") or ""

    try:
        buckets = retrieve_user_quota(access_token, project_id=project_id)
    except CodeAssistError as exc:
        cli._console_print(f"  [red]Quota lookup failed:[/] {exc}")
        return

    if not buckets:
        cli._console_print("  [dim]No quota buckets reported (account may be on legacy/unmetered tier).[/]")
        return

    # Sort for stable display, group by model
    buckets.sort(key=lambda b: (b.model_id, b.token_type))
    cli._console_print()
    cli._console_print(f"  [bold]Gemini Code Assist quota[/]  (project: {project_id or '(auto / free-tier)'})")
    cli._console_print()
    for b in buckets:
        pct = max(0.0, min(1.0, b.remaining_fraction))
        width = 20
        filled = int(round(pct * width))
        bar = "▓" * filled + "░" * (width - filled)
        pct_str = f"{int(pct * 100):3d}%"
        header = b.model_id
        if b.token_type:
            header += f" [{b.token_type}]"
        cli._console_print(f"    {header:40s}  {bar}  {pct_str}")
    cli._console_print()
