"""_handle_profile_command handler."""

from src.reymen.sistem.ReYMeN_constants import display_reymen_home


def _handle_profile_command(cli) -> None:
    """Display active profile name and home directory."""
    display = display_reymen_home()
    try:
        from reymen.reymen_cli.profiles import get_active_profile_name
        profile_name = get_active_profile_name()
    except ImportError:
        profile_name = "default"

    print()
    print(f"  Profile: {profile_name}")
    print(f"  Home:    {display}")
    print()
