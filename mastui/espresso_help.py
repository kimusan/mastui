"""Help screen modal displaying keybinding cheatsheet and app documentation."""

from __future__ import annotations

from espresso.beans.modal_stack import ModalCloseMsg
from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi


class HelpModal(Model):
    """Modal displaying keyboard shortcuts and help."""

    def __init__(self, width: int = 74) -> None:
        self.width = max(56, width)

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[HelpModal, Cmd | None]:
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "esc" | "q" | "?" | "enter":
                    def _close() -> Msg:
                        return ModalCloseMsg()
                    return self, _close
        return self, None

    def view(self) -> str:
        """Render two-column keybinding guide."""
        inner_w = max(50, self.width - 4)
        col_w = (inner_w - 4) // 2

        key_style = Style().bold(True).foreground("#00E5FF")
        desc_style = Style().foreground("#DDDDDD")
        section_style = Style().bold(True).foreground("#7D56F4")

        def _fmt_row(k: str, d: str, w: int) -> str:
            ks = key_style.render(f"{k:<11}")
            ds = desc_style.render(d)
            line = f"{ks} {ds}"
            return truncate_ansi(line, w)

        left_lines = [
            section_style.render("◆ NAVIGATION"),
            _fmt_row("j / ↓", "Scroll down timeline", col_w),
            _fmt_row("k / ↑", "Scroll up timeline", col_w),
            _fmt_row("g / Home", "Jump to top of feed", col_w),
            _fmt_row("1 - 5", "Direct jump to timeline tab", col_w),
            _fmt_row("Tab / ]", "Next timeline column", col_w),
            _fmt_row("S-Tab / [", "Previous timeline column", col_w),
            "",
            section_style.render("◆ POST ACTIONS"),
            _fmt_row("l / f", "Like / Favourite post", col_w),
            _fmt_row("b", "Boost post (confetti burst)", col_w),
            _fmt_row("a", "Reply to selected post", col_w),
            _fmt_row("c / n", "Compose new toot", col_w),
            _fmt_row("s", "Toggle spoiler / CW text", col_w),
        ]

        right_lines = [
            section_style.render("◆ INSPECTION & TOOLS"),
            _fmt_row("Enter / t", "View conversation thread", col_w),
            _fmt_row("x", "Extract & copy links", col_w),
            _fmt_row("p", "View author profile", col_w),
            _fmt_row("y", "Copy post link to clipboard", col_w),
            "",
            section_style.render("◆ SETTINGS & SYSTEM"),
            _fmt_row("o", "Settings & burst animations", col_w),
            _fmt_row("r", "Refresh active timeline", col_w),
            _fmt_row("?", "Show / hide this help guide", col_w),
            _fmt_row("Esc", "Close any open dialog", col_w),
            _fmt_row("q / ^C", "Quit Mastui", col_w),
            "",
            Style().faint(True).foreground("#777799").render("🖱️ Full mouse click & wheel support"),
        ]

        max_rows = max(len(left_lines), len(right_lines))
        while len(left_lines) < max_rows:
            left_lines.append("")
        while len(right_lines) < max_rows:
            right_lines.append("")

        body_lines: list[str] = []
        # Title header
        title = Style().bold(True).foreground("#00E5FF").render("📖 MASTUI KEYBOARD SHORTCUTS & HELP")
        body_lines.append(title)
        body_lines.append(Style().foreground("#555577").render("Fully keyboard-driven Fediverse client powered by Espresso TUI"))
        body_lines.append("")

        for l_line, r_line in zip(left_lines, right_lines):
            l_pad = l_line + " " * max(0, col_w - string_width(l_line))
            body_lines.append(f"{l_pad}  │  {r_line}")

        body_lines.append("")
        body_lines.append(Style().foreground("#555577").render("Press [Esc], [?], or [Enter] to return to timeline"))

        content = "\n".join(body_lines)
        return (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#7D56F4")
            .width(inner_w)
            .render(content)
        )
