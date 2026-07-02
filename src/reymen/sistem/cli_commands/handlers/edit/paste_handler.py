"""_handle_paste_command handler."""

from src.reymen.sistem.cli_display import _cprint, _DIM, _RST
from src.reymen.sistem.ReYMeN_constants import is_termux as _is_termux_environment


def _handle_paste_command(cli):
    """Handle /paste — explicitly check clipboard for an image.

    This is the reliable fallback for terminals where BracketedPaste
    doesn't fire for image-only clipboard content (e.g., VSCode terminal,
    Windows Terminal with WSL2).
    """
    if _is_termux_environment():
        _cprint(
            f"  {_DIM}Clipboard image paste is not available on Termux — "
            f"use /image <path> or paste a local image path like "
            f"{_termux_example_image_path()}{_RST}"
        )
        return

    from reymen.reymen_cli.clipboard import has_clipboard_image
    if has_clipboard_image():
        if cli._try_attach_clipboard_image():
            n = len(cli._attached_images)
            _cprint(f"  📎 Image #{n} attached from clipboard")
        else:
            _cprint(f"  {_DIM}(>_<) Clipboard has an image but extraction failed{_RST}")
    else:
        _cprint(f"  {_DIM}(._.) No image found in clipboard{_RST}")


from src.reymen.sistem.cli_stream import _termux_example_image_path  # noqa: E402
