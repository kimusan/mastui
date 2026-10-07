"""Account and profile switcher modal for multi-account support."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from espresso.beans.modal_stack import ModalCloseMsg
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi
from mastui.profile_manager import profile_manager


@dataclass
class SwitchProfileMsg(Msg):
    """Dispatched when user selects an existing profile to switch to."""
    profile_name: str


@dataclass
class OpenLoginModalMsg(Msg):
    """Dispatched when user requests adding a new account."""
    pass


class ProfileSelectionModal(Model):
    """Interactive modal dialog allowing users to switch accounts or add a new account."""

    def __init__(
        self,
        current_profile: str = "default",
        profiles: list[str] | None = None,
        width: int = 68,
        height: int = 18,
        theme: Any = None,
    ) -> None:
        self.width = max(52, width)
        self.height = max(12, height)
        self.theme = theme
        self.current_profile = current_profile

        # Get available profiles
        if profiles is not None:
            self.profiles = list(profiles)
        else:
            self.profiles = profile_manager.get_profiles()

        if not self.profiles:
            self.profiles = ["default"]

        # Ensure active profile appears first or is clearly indexed
        self.cursor = 0
        for i, p in enumerate(self.profiles):
            if p == current_profile:
                self.cursor = i
                break

        # Total items: available profiles + 1 ("➕ Add New Account")
        self.add_account_index = len(self.profiles)
        self.status_message = ""

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[ProfileSelectionModal, Cmd | None]:
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "esc" | "q":
                    def _close() -> Msg:
                        return ModalCloseMsg()
                    return self, _close

                case "up" | "k":
                    self.cursor = (self.cursor - 1) % (len(self.profiles) + 1)
                    return self, None

                case "down" | "j":
                    self.cursor = (self.cursor + 1) % (len(self.profiles) + 1)
                    return self, None

                case "a":
                    # Directly open login to add account
                    def _open_login() -> Msg:
                        return OpenLoginModalMsg()
                    return self, _open_login

                case "enter":
                    if self.cursor == self.add_account_index:
                        def _open_login() -> Msg:
                            return OpenLoginModalMsg()
                        return self, _open_login
                    else:
                        selected = self.profiles[self.cursor]
                        def _switch() -> Msg:
                            return SwitchProfileMsg(selected)
                        return self, _switch

                case "d":
                    # Delete inactive profile
                    if self.cursor < len(self.profiles):
                        target = self.profiles[self.cursor]
                        if target == self.current_profile:
                            self.status_message = "Cannot delete the currently active profile."
                        else:
                            profile_manager.delete_profile(target)
                            self.profiles.pop(self.cursor)
                            self.add_account_index = len(self.profiles)
                            self.cursor = min(self.cursor, len(self.profiles))
                            self.status_message = f"Deleted profile '{target}'."
                    return self, None

        if isinstance(msg, MouseMsg) and msg.button == MouseButton.LEFT and msg.action == MouseAction.PRESS:
            # Let clicks be handled gracefully
            pass

        return self, None

    def view(self) -> str:
        inner_w = max(46, self.width - 4)

        header = Style().bold(True).foreground("#00E5FF").render("👤 SWITCH ACCOUNT / PROFILE")
        sep = Style().foreground("#333355").render("─" * inner_w)

        lines: list[str] = [
            header,
            sep,
            Style().foreground("#AAAABB").render("Select an account to load timelines, posts, and notifications:"),
            "",
        ]

        # Profile list items
        for i, p in enumerate(self.profiles):
            is_active = (p == self.current_profile)
            is_sel = (i == self.cursor)

            prefix = "▶ " if is_sel else "  "
            badge = Style().bold(True).foreground("#00E676").render(" (Active)") if is_active else ""
            
            p_style = Style().bold(True).foreground("#00E5FF") if is_sel else Style().foreground("#FAFAFA" if is_active else "#CCCCDD")
            if is_sel:
                line_str = f"{prefix}{p_style.render(p)}{badge}"
                line_box = Style().background("#2A2A44").width(inner_w - 4).render(line_str)
                lines.append(f" {line_box}")
            else:
                lines.append(f" {prefix}{p_style.render(p)}{badge}")

        # Add New Account row
        is_add_sel = (self.cursor == self.add_account_index)
        add_prefix = "▶ " if is_add_sel else "  "
        add_text = "➕ Add New Account / Login"
        if is_add_sel:
            add_styled = Style().bold(True).foreground("#FFD54F").render(f"{add_prefix}{add_text}")
            lines.append("")
            lines.append(f" {Style().background('#2A2A44').width(inner_w - 4).render(add_styled)}")
        else:
            add_styled = Style().foreground("#FFD54F").render(f"{add_prefix}{add_text}")
            lines.append("")
            lines.append(f" {add_styled}")

        if self.status_message:
            lines.append("")
            lines.append(Style().italic(True).foreground("#FFB300").render(f"ℹ {self.status_message}"))

        lines.append("")
        hints = "[j/k] Navigate  [Enter] Switch  [a] Add Account  [d] Delete  [Esc] Close"
        lines.append(Style().foreground("#666688").render(hints))

        content = "\n".join(lines)
        return (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#00E5FF")
            .width(inner_w)
            .padding(1, 2)
            .render(content)
        )
