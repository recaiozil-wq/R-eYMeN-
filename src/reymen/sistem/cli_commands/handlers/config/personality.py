"""_handle_personality_command handler."""

from src.reymen.sistem.cli_stream import save_config_value


def _handle_personality_command(cli, cmd: str):
    """Handle the /personality command to set predefined personalities."""
    parts = cmd.split(maxsplit=1)

    if len(parts) > 1:
        # Set personality
        personality_name = parts[1].strip().lower()

        if personality_name in {"none", "default", "neutral"}:
            cli.system_prompt = ""
            cli.agent = None  # Force re-init
            if save_config_value("agent.system_prompt", ""):
                print("(^_^)b Personality cleared (saved to config)")
            else:
                print("(^_^) Personality cleared (session only)")
            print("  No personality overlay — using base agent behavior.")
        elif personality_name in cli.personalities:
            cli.system_prompt = cli._resolve_personality_prompt(cli.personalities[personality_name])
            cli.agent = None  # Force re-init
            if save_config_value("agent.system_prompt", cli.system_prompt):
                print(f"(^_^)b Personality set to '{personality_name}' (saved to config)")
            else:
                print(f"(^_^) Personality set to '{personality_name}' (session only)")
            print(f"  \"{cli.system_prompt[:60]}{'...' if len(cli.system_prompt) > 60 else ''}\"")
        else:
            print(f"(._.) Unknown personality: {personality_name}")
            print(f"  Available: none, {', '.join(cli.personalities.keys())}")
    else:
        # Show available personalities
        print()
        print("+" + "-" * 50 + "+")
        print("|" + " " * 12 + "(^o^)/ Personalities" + " " * 15 + "|")
        print("+" + "-" * 50 + "+")
        print()
        print(f"  {'none':<12} - (no personality overlay)")
        for name, prompt in cli.personalities.items():
            if isinstance(prompt, dict):
                preview = prompt.get("description") or prompt.get("system_prompt", "")[:50]
            else:
                preview = str(prompt)[:50]
            print(f"  {name:<12} - {preview}")
        print()
        print("  Usage: /personality <name>")
        print()
