"""Handle dangerous-command approval selection for the CLI session."""


def _handle_approval_selection(cli) -> None:
    """Process the currently selected dangerous-command approval choice.

    Delegated from :meth:`session_commands.MixinCommands._handle_approval_selection`.
    """
    state = cli._approval_state
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
        cli._invalidate()
        return

    state["response_queue"].put(chosen)
    cli._approval_state = None
    cli._invalidate()
