"""Cool animated splash screen for Mastui on Espresso TUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseMsg
from espresso.core.tea import Cmd, Model, Msg, tick
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.gradient import linear_gradient
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width

MASTUI_ASCII_LOGO = r"""
 888b     d888                   888             d8b 
 8888b   d8888                   888             Y8P 
 88888b.d88888                   888                 
 888Y88888P888  8888b.  .d8888b  888888 888  888 888 
 888 Y888P 888     "88b 88K      888    888  888 8K8 
 888  Y8P  888 .d888888 "Y8888b. 888    888  888 8I8 
 888   "   888 888  888      X88 Y88b.  Y88b 888 8M8 
 888       888 "Y888888  88888P'  "Y888  "Y88888 888 
""".strip("\n")


@dataclass(frozen=True)
class SplashTickMsg(Msg):
    """Animation frame tick for the splash screen."""

    step: int


@dataclass(frozen=True)
class SplashDoneMsg(Msg):
    """Emitted when the splash screen completes or is dismissed."""


class SplashScreen(Model):
    """Animated startup splash screen."""

    def __init__(
        self,
        username: str = "kim@mastui.app",
        instance: str = "social.data.coop",
        version: str = "1.14.2",
        width: int = 100,
        height: int = 30,
        max_steps: int = 18,
    ) -> None:
        self.username = username
        self.instance = instance
        self.version = version
        self.width = width
        self.height = height
        self.step = 0
        self.max_steps = max_steps
        self.is_done = False

    def init(self) -> Cmd | None:
        """Dispatch initial animation tick."""
        return tick(0.08, SplashTickMsg(step=1))

    def update(self, msg: Msg) -> tuple[SplashScreen, Cmd | None]:
        # Any keypress or mouse click dismisses immediately
        if isinstance(msg, (KeyMsg, MouseMsg)):
            self.is_done = True
            def _done_now() -> Msg:
                return SplashDoneMsg()
            return self, _done_now

        if isinstance(msg, SplashTickMsg):
            self.step = msg.step
            if self.step >= self.max_steps:
                self.is_done = True
                def _done() -> Msg:
                    return SplashDoneMsg()
                return self, _done
            return self, tick(0.08, SplashTickMsg(step=self.step + 1))

        return self, None

    def view(self) -> str:
        box_w = min(74, max(50, self.width - 6))

        # 1. Gradient ASCII Logo
        logo_lines = [
            linear_gradient(line, "#00E5FF", "#7D56F4")
            for line in MASTUI_ASCII_LOGO.splitlines()
        ]
        gradient_logo = "\n".join(logo_lines)

        # 2. Subtitles & Badges
        version_str = Style().bold(True).foreground("#FFB300").render(f"v{self.version}")
        powered_str = Style().foreground("#7D56F4").render("⚡ Powered by Espresso TUI • High-Performance Elm Architecture")
        conn_str = Style().faint(True).foreground("#8888AA").render(f"Connected to {self.instance}  │  @{self.username}")

        # 3. Animated Progress Bar
        pct = min(100, int((self.step / max(1, self.max_steps)) * 100))
        bar_len = 28
        filled = int((pct / 100.0) * bar_len)
        bar_str = "█" * filled + "░" * (bar_len - filled)
        color_bar = Style().foreground("#00E5FF").render(bar_str)
        progress_text = Style().foreground("#00E676").bold(True).render(f"☕ Brewing feeds... [{color_bar}] {pct}%")

        # 4. Hint
        hint = Style().foreground("#555577").render("Press any key to jump straight to timeline →")

        body = (
            f"\n{gradient_logo}\n\n"
            f"Mastui {version_str}\n"
            f"{powered_str}\n"
            f"{conn_str}\n\n"
            f"{progress_text}\n\n"
            f"{hint}\n"
        )

        card = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#00E5FF")
            .width(box_w)
            .align(Align.CENTER)
            .render(body)
        )

        # Center vertically and horizontally on screen
        card_lines = card.splitlines()
        card_w = max((string_width(l) for l in card_lines), default=box_w)
        pad_left = max(0, (self.width - card_w) // 2)
        pad_left_str = " " * pad_left
        centered_lines = [f"{pad_left_str}{line}" for line in card_lines]

        pad_top = max(0, (self.height - len(card_lines)) // 2)
        top_spaces = "\n" * pad_top
        return f"{top_spaces}{chr(10).join(centered_lines)}"
