"""Interactive Toot/Reply Composer modal for Mastui on Espresso."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from espresso.beans.modal_stack import ModalCloseMsg
from espresso.beans.select import Select
from espresso.beans.switch import Switch
from espresso.beans.textarea import TextArea
from espresso.beans.textinput import TextInput
from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi


@dataclass(frozen=True)
class TootSubmitMsg(Msg):
    """Message emitted when user confirms posting a new status/toot."""

    content: str
    spoiler_text: str
    visibility: str
    reply_to_id: str | None = None


class ComposerModal(Model):
    """Modal dialog for composing new Mastodon posts or replies."""

    def __init__(
        self,
        reply_to_post: dict | None = None,
        max_characters: int = 500,
        initial_text: str = "",
        visibility: str = "public",
        width: int = 68,
    ) -> None:
        self.reply_to_post = reply_to_post
        self.max_characters = max_characters
        self.width = max(50, width)

        reply_status = reply_to_post.get("reblog") or reply_to_post if reply_to_post else None
        self.reply_to_id = reply_status.get("id") if reply_status else None

        # Build initial text with mentions if replying
        if reply_status and not initial_text:
            mentions = {f"@{reply_status.get('account', {}).get('acct', '')}"}
            for m in reply_status.get("mentions", []):
                mentions.add(f"@{m.get('acct', '')}")
            initial_text = f"{' '.join(sorted(mentions))} "

        # Sub-beans
        self.text_area = TextArea(
            placeholder="What's happening on the Fediverse?",
            width=self.width - 6,
            height=6,
            show_line_numbers=False,
        )
        if initial_text:
            self.text_area.lines = initial_text.split("\n")
            self.text_area.cursor_row = len(self.text_area.lines) - 1
            self.text_area.cursor_col = len(self.text_area.lines[-1])

        self.cw_switch = Switch(value=False, label="Content Warning (CW)")
        self.cw_input = TextInput(placeholder="Spoiler warning text...", prompt="  ⚠ ")
        self.cw_input.blur()

        vis_options = [
            ("public", "🌐 Public"),
            ("unlisted", "🔑 Unlisted"),
            ("private", "👥 Followers-only"),
            ("direct", "🔒 Direct message"),
        ]
        self.vis_select = Select(options=vis_options, value=visibility, width=26)
        self.vis_select.blur()

        # Focus indices:
        # 0: TextArea, 1: CW Switch, 2: CW Input (if enabled), 3: Visibility, 4: Post Button, 5: Cancel Button
        self.focus_idx = 0

    def init(self) -> Cmd | None:
        return None

    def _sync_focus(self) -> None:
        """Update focus states across sub-components."""
        self.text_area.focused = (self.focus_idx == 0)
        self.cw_switch.focused = (self.focus_idx == 1)
        self.cw_input.focused = (self.focus_idx == 2 and self.cw_switch.value)
        self.vis_select.focused = (self.focus_idx == 3)

    def _max_focus_idx(self) -> int:
        return 5 if self.cw_switch.value else 5

    def _submit(self) -> tuple[ComposerModal, Cmd | None]:
        content = "\n".join(self.text_area.lines).strip()
        spoiler = self.cw_input.value.strip() if self.cw_switch.value else ""
        vis = self.vis_select.selected_value
        rep_id = self.reply_to_id

        if not content:
            return self, None

        def _cmd() -> Msg:
            return TootSubmitMsg(
                content=content,
                spoiler_text=spoiler,
                visibility=vis,
                reply_to_id=rep_id,
            )
        return self, _cmd

    def update(self, msg: Msg) -> tuple[ComposerModal, Cmd | None]:
        # Handle Tab navigation
        if isinstance(msg, KeyMsg):
            # If Select is open, let Select consume keys
            if self.vis_select.is_open:
                self.vis_select, cmd = self.vis_select.update(msg)
                return self, cmd

            match msg.key:
                case "tab":
                    self.focus_idx = (self.focus_idx + 1) % 6
                    # Skip CW input if switch is off
                    if self.focus_idx == 2 and not self.cw_switch.value:
                        self.focus_idx = 3
                    self._sync_focus()
                    return self, None
                case "shift+tab":
                    self.focus_idx = (self.focus_idx - 1) % 6
                    if self.focus_idx == 2 and not self.cw_switch.value:
                        self.focus_idx = 1
                    self._sync_focus()
                    return self, None
                case "esc":
                    def _close() -> Msg:
                        return ModalCloseMsg()
                    return self, _close

        # Route to focused component
        if self.focus_idx == 0:
            self.text_area, cmd = self.text_area.update(msg)
            return self, cmd
        elif self.focus_idx == 1:
            self.cw_switch, cmd = self.cw_switch.update(msg)
            return self, cmd
        elif self.focus_idx == 2:
            self.cw_input, cmd = self.cw_input.update(msg)
            return self, cmd
        elif self.focus_idx == 3:
            self.vis_select, cmd = self.vis_select.update(msg)
            return self, cmd
        elif self.focus_idx == 4:  # Post Button
            if isinstance(msg, KeyMsg) and msg.key in ("enter", " "):
                return self._submit()
        elif self.focus_idx == 5:  # Cancel Button
            if isinstance(msg, KeyMsg) and msg.key in ("enter", " "):
                def _cancel() -> Msg:
                    return ModalCloseMsg()
                return self, _cancel

        return self, None

    def view(self) -> str:
        """Render the modal composer card."""
        inner_w = max(40, self.width - 4)

        lines: list[str] = []

        # 1. Header
        title = "💬 Reply to Post" if self.reply_to_post else "✨ New Mastodon Post"
        header = Style().bold(True).foreground("#00E5FF").render(f"☕ {title}")
        lines.append(header)
        lines.append("")

        # 2. TextArea Body
        lines.append(self.text_area.view())
        lines.append("")

        # 3. CW Toggle & Input
        cw_switch_str = self.cw_switch.view()
        if self.cw_switch.value:
            cw_input_box = self.cw_input.view()
            lines.append(f"{cw_switch_str}\n  {cw_input_box}")
        else:
            lines.append(cw_switch_str)
        lines.append("")

        # 4. Visibility Selector
        vis_label = Style().bold(True).foreground("#AAAAAA").render("Visibility:")
        lines.append(f"{vis_label} {self.vis_select.view()}")
        lines.append("")

        # 5. Char Count & Action Buttons
        total_len = sum(len(l) for l in self.text_area.lines)
        chars_left = self.max_characters - total_len
        char_style = Style().bold(True).foreground("#00E676" if chars_left >= 0 else "#FF5252")
        char_str = char_style.render(f"{chars_left} chars remaining")

        btn_post_style = Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1) if self.focus_idx == 4 \
            else Style().foreground("#DDDDDD").background("#333355").padding(0, 1)
        btn_cancel_style = Style().bold(True).foreground("#FFFFFF").background("#FF5252").padding(0, 1) if self.focus_idx == 5 \
            else Style().foreground("#AAAAAA").background("#222233").padding(0, 1)

        post_btn = btn_post_style.render(" Post Toot [Enter] ")
        cancel_btn = btn_cancel_style.render(" Cancel [Esc] ")

        footer_right = f"{post_btn}  {cancel_btn}"
        pad = max(1, inner_w - string_width(char_str) - string_width(footer_right))
        lines.append(f"{char_str}{' ' * pad}{footer_right}")

        # Modal Box Border
        content = "\n".join(lines)
        return (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#7D56F4")
            .padding(1, 2)
            .width(inner_w)
            .render(content)
        )
