"""_handle_kanban_command handler."""


def _handle_kanban_command(cli, cmd: str):
    """Handle the /kanban command — delegate to the shared kanban CLI.

    The string form passed here is the user's full ``/kanban ...``
    including the leading slash; we strip it and hand the remainder
    to ``kanban.run_slash`` which returns a single formatted string.
    """
    from reymen.reymen_cli.kanban import run_slash

    rest = cmd.strip()
    if rest.startswith("/"):
        rest = rest.lstrip("/")
    if rest.startswith("kanban"):
        rest = rest[len("kanban"):].lstrip()
    try:
        output = run_slash(rest)
    except Exception as exc:  # pragma: no cover - defensive
        output = f"(._.) kanban error: {exc}"
    if output:
        print(output)
