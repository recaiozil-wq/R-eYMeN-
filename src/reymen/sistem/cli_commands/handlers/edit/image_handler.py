"""_handle_image_command handler."""

from pathlib import Path

from src.reymen.sistem.cli_display import _cprint, _DIM, _RST, _IMAGE_EXTENSIONS
from src.reymen.sistem.cli_stream import (
    _split_path_input,
    _resolve_attachment_path,
    _termux_example_image_path,
)
from src.reymen.sistem.ReYMeN_constants import is_termux as _is_termux_environment


def _handle_image_command(cli, cmd_original: str):
    """Handle /image <path> — attach a local image file for the next prompt."""
    raw_args = (cmd_original.split(None, 1)[1].strip() if " " in cmd_original else "")
    if not raw_args:
        hint = _termux_example_image_path() if _is_termux_environment() else "/path/to/image.png"
        _cprint(f"  {_DIM}Usage: /image <path>  e.g. /image {hint}{_RST}")
        return

    path_token, _remainder = _split_path_input(raw_args)
    image_path = _resolve_attachment_path(path_token)
    if image_path is None:
        _cprint(f"  {_DIM}(>_<) File not found: {path_token}{_RST}")
        return
    if image_path.suffix.lower() not in _IMAGE_EXTENSIONS:
        _cprint(f"  {_DIM}(._.) Not a supported image file: {image_path.name}{_RST}")
        return

    cli._attached_images.append(image_path)
    _cprint(f"  📎 Attached image: {image_path.name}")
    if _remainder:
        _cprint(f"  {_DIM}Now type your prompt (or use --image in single-query mode): {_remainder}{_RST}")
    elif _is_termux_environment():
        _cprint(f"  {_DIM}Tip: type your next message, or run ReYMeN chat -q --image {_termux_example_image_path(image_path.name)} \"What do you see?\"{_RST}")
