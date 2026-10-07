"""Universal clipboard utility supporting OSC 52 terminal escapes and system tools."""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import sys


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard via OSC 52 and local clipboard utilities."""
    if not text:
        return False

    success = False

    # 1. Terminal OSC 52 escape sequence (works across Ghostty, WezTerm, iTerm, Alacritty, Kitty, Windows Terminal, tmux)
    try:
        payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
        # Check if inside tmux - tmux requires DCS passthrough wrapper
        if "TMUX" in os.environ:
            osc_seq = f"\033Ptmux;\033\033]52;c;{payload}\007\033\\"
        else:
            osc_seq = f"\033]52;c;{payload}\a"

        # Emit to tty/stderr
        sys.stderr.write(osc_seq)
        sys.stderr.flush()
        success = True
    except Exception:
        pass

    # 2. Native CLI tools (wl-copy for Wayland, xclip/xsel for X11, pbcopy for macOS)
    commands = [
        ("wl-copy", []),
        ("xclip", ["-selection", "clipboard"]),
        ("xsel", ["--clipboard", "--input"]),
        ("pbcopy", []),
    ]
    for cmd, args in commands:
        if shutil.which(cmd):
            try:
                subprocess.run(
                    [cmd] + args,
                    input=text.encode("utf-8"),
                    check=True,
                    timeout=1.0,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                success = True
                break
            except Exception:
                pass

    return success
