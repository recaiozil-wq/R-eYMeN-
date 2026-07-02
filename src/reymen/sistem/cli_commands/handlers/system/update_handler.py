"""_handle_update_command handler."""


def _handle_update_command(cli) -> bool:
    """Handle /update — update ReYMeN Agent to the latest version.

    In the classic CLI this exits the session and relaunches as
    ``ReYMeN update`` so the user sees update output directly and gets
    the new version on next launch.

    Returns ``True`` when the update was confirmed (caller should trigger
    app exit so the relaunch is deferred to the main thread after
    prompt_toolkit cleans up terminal modes).  Returns ``False`` / falsy
    when cancelled.
    """
    from reymen.reymen_cli.config import is_managed, format_managed_message

    if is_managed():
        print(f"  ✗ {format_managed_message('update ReYMeN Agent')}")
        return False

    # Use the prompt_toolkit-native modal so the confirmation panel
    # renders properly above the composer and avoids raw input() races
    # with the prompt_toolkit event loop (same pattern as
    # _confirm_destructive_slash).
    choices = [
        ("once", "Update Now", "exit the current session and update ReYMeN Agent"),
        ("cancel", "Cancel", "keep the current session"),
    ]
    raw = cli._prompt_text_input_modal(
        title="⚕  Update ReYMeN Agent",
        detail="This will exit the current session and run `ReYMeN update`.",
        choices=choices,
    )
    if raw is None:
        print("  🟡 /update cancelled.")
        return False
    choice = cli._normalize_slash_confirm_choice(raw, choices)
    if choice != "once":
        print("  🟡 /update cancelled.")
        return False

    print()
    print("  ⚕ Launching update...")
    print()

    # Store the relaunch args so run() can exec them from the main thread
    # after prompt_toolkit exits and restores terminal modes.  Calling
    # relaunch() directly here (from the process_loop daemon thread) would
    # skip terminal cleanup on POSIX (execvp replaces the process mid-TUI)
    # and only exit the worker thread on Windows (subprocess.run +
    # sys.exit inside a non-main thread does not exit the process).
    cli._pending_relaunch = ["update"]
    return True
