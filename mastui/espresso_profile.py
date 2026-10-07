"""Author Profile modal to view account details, bio, stats, and metadata."""

from __future__ import annotations

import re
from html import unescape
from typing import Any

from espresso.beans.modal_stack import ModalCloseMsg
from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi


def _clean_bio_html(html: str) -> str:
    """Convert HTML bio to clean terminal readable text."""
    if not html:
        return "No bio provided."
    # Replace <br> and </p> with newlines
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text).strip()
    return text or "No bio provided."


class ProfileModal(Model):
    """Modal displaying user profile details and relationship status."""

    def __init__(self, account_or_post: dict, width: int = 68) -> None:
        if "account" in account_or_post:
            self.account = account_or_post["account"]
        elif "reblog" in account_or_post and "account" in account_or_post["reblog"]:
            self.account = account_or_post["reblog"]["account"]
        else:
            self.account = account_or_post

        self.width = max(52, width)
        self.is_following = bool(self.account.get("following", False))
        self.is_muted = bool(self.account.get("muting", False))

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[ProfileModal, Cmd | None]:
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "esc" | "q" | "p":
                    def _close() -> Msg:
                        return ModalCloseMsg()
                    return self, _close
                case "f":
                    self.is_following = not self.is_following
                    return self, None
                case "m":
                    self.is_muted = not self.is_muted
                    return self, None
        return self, None

    def view(self) -> str:
        """Render user profile card."""
        inner_w = max(44, self.width - 4)
        lines: list[str] = []

        disp_name = self.account.get("display_name") or self.account.get("username") or "User"
        acct = self.account.get("acct") or self.account.get("username") or "unknown"

        # Avatar initial badge
        initials = (disp_name[:2] if len(disp_name) >= 2 else disp_name + " ").upper()
        avatar_badge = Style().bold(True).foreground("#FFFFFF").background("#7D56F4").render(f" {initials} ")

        # Header title
        title_name = Style().bold(True).foreground("#00E5FF").render(disp_name)
        handle_style = Style().foreground("#AAAAAA").render(f"@{acct}")
        status_badges = []
        if self.is_following:
            status_badges.append(Style().bold(True).foreground("#00E676").render("[Following]"))
        if self.is_muted:
            status_badges.append(Style().bold(True).foreground("#FFB300").render("[Muted]"))
        if self.account.get("bot"):
            status_badges.append(Style().foreground("#00E5FF").render("[BOT]"))

        badges_str = f" {' '.join(status_badges)}" if status_badges else ""
        lines.append(f"{avatar_badge}  {title_name} {handle_style}{badges_str}")
        lines.append("")

        # Metrics bar
        followers = self.account.get("followers_count", 0)
        following = self.account.get("following_count", 0)
        posts_count = self.account.get("statuses_count", 0)

        stat_bar = (
            f"  {Style().bold(True).foreground('#00E5FF').render(str(posts_count))} Posts   │   "
            f"{Style().bold(True).foreground('#00E5FF').render(str(following))} Following   │   "
            f"{Style().bold(True).foreground('#00E5FF').render(str(followers))} Followers"
        )
        lines.append(stat_bar)
        lines.append(Style().foreground("#444466").render("─" * (inner_w - 2)))

        # Bio note
        bio_text = _clean_bio_html(self.account.get("note", ""))
        for b_line in bio_text.splitlines():
            if b_line.strip():
                lines.append(truncate_ansi(f"  {b_line}", inner_w - 4))
        lines.append("")

        # Custom profile fields (e.g. Pronouns, Website)
        fields = self.account.get("fields", [])
        if fields:
            lines.append(Style().bold(True).foreground("#7D56F4").render("◆ Metadata:"))
            for f in fields[:4]:
                name = f.get("name", "")
                val = _clean_bio_html(f.get("value", ""))
                lines.append(truncate_ansi(f"  • {Style().bold(True).render(name)}: {val}", inner_w - 4))
            lines.append("")

        # Bottom hotkey actions
        f_label = "Unfollow" if self.is_following else "Follow"
        m_label = "Unmute" if self.is_muted else "Mute"
        hints = f"  [f] {f_label}   [m] {m_label}   [Esc/q] Close Profile"
        lines.append(Style().foreground("#777799").render(hints))

        content = "\n".join(lines)
        return (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#00E5FF")
            .width(inner_w)
            .render(content)
        )
