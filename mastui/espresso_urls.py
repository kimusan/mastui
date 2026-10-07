"""URL Selector modal to browse and copy/open links extracted from a post."""

from __future__ import annotations

import re
import webbrowser
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import urlparse

from espresso.beans.modal_stack import ModalCloseMsg
from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi
from mastui.espresso_clipboard import copy_to_clipboard


@dataclass(frozen=True)
class UrlSelectedMsg(Msg):
    """Message emitted when user selects and copies a URL."""

    url: str
    action: str  # "copy" or "open"


def extract_post_urls(post_data: dict) -> list[str]:
    """Extract and deduplicate all URLs from a post."""
    status = post_data.get("reblog") or post_data
    urls: list[str] = []

    # 1. Content HTML hrefs
    content = status.get("content", "")
    if content:
        href_pattern = r'href=["\']([^"\']+)["\']'
        for href in re.findall(href_pattern, content):
            urls.append(href)

        # Plain URLs in text
        url_pattern = r'https?://[^\s<>"\'{}|\\^`\[\]]+'
        for u in re.findall(url_pattern, unescape(content)):
            if not (u.endswith("...") or "…" in u):
                urls.append(u)

    # 2. Media attachments
    for att in status.get("media_attachments", []):
        if att.get("url"):
            urls.append(att["url"])
        elif att.get("remote_url"):
            urls.append(att["remote_url"])

    # 3. Card URL
    card = status.get("card")
    if card and card.get("url"):
        urls.append(card["url"])

    # Deduplicate while preserving order and filtering invalid
    seen: set[str] = set()
    cleaned: list[str] = []
    for u in urls:
        u = u.strip()
        parsed = urlparse(u)
        if not parsed.scheme or not parsed.netloc or parsed.netloc == "www." or u.endswith("...") or "…" in u:
            continue
        if u not in seen:
            seen.add(u)
            cleaned.append(u)

    return cleaned


class UrlSelectorModal(Model):
    """Modal for selecting and copying URLs found in a toot."""

    def __init__(self, post_data: dict, width: int = 70) -> None:
        self.post_data = post_data
        self.width = max(50, width)
        self.urls = extract_post_urls(post_data)
        self.selected_idx = 0

    def init(self) -> Cmd | None:
        return None

    def _choose_url(self, idx: int, action: str = "copy") -> tuple[UrlSelectorModal, Cmd | None]:
        if not (0 <= idx < len(self.urls)):
            return self, None
        target_url = self.urls[idx]

        if action == "copy":
            copy_to_clipboard(target_url)
        elif action == "open":
            try:
                webbrowser.open(target_url)
            except Exception:
                pass

        def _emit() -> Msg:
            return UrlSelectedMsg(url=target_url, action=action)

        return self, _emit

    def update(self, msg: Msg) -> tuple[UrlSelectorModal, Cmd | None]:
        if not self.urls:
            if isinstance(msg, KeyMsg) and msg.key in ("esc", "q", "enter"):
                def _close() -> Msg:
                    return ModalCloseMsg()
                return self, _close
            return self, None

        if isinstance(msg, KeyMsg):
            # Direct number key selection (1-9)
            k = str(msg.key)
            if k.isdigit() and 1 <= int(k) <= min(9, len(self.urls)):
                return self._choose_url(int(k) - 1, action="copy")

            match msg.key:
                case "esc" | "q":
                    def _close() -> Msg:
                        return ModalCloseMsg()
                    return self, _close
                case "j" | "down":
                    self.selected_idx = (self.selected_idx + 1) % len(self.urls)
                    return self, None
                case "k" | "up":
                    self.selected_idx = (self.selected_idx - 1) % len(self.urls)
                    return self, None
                case "enter" | "c" | "y":
                    return self._choose_url(self.selected_idx, action="copy")
                case "o":
                    return self._choose_url(self.selected_idx, action="open")

        return self, None

    def view(self) -> str:
        """Render the URL selection card."""
        inner_w = max(42, self.width - 4)
        lines: list[str] = []

        # Header
        header = Style().bold(True).foreground("#00E5FF").render("🔗 EXTRACTED LINKS")
        lines.append(header)
        lines.append(Style().foreground("#555577").render("Select a URL to copy to clipboard or open in browser"))
        lines.append("")

        if not self.urls:
            lines.append(Style().faint(True).foreground("#888899").render("  No URLs or media links found in this post."))
            lines.append("")
            lines.append(Style().foreground("#555577").render("  [Esc] Close"))
        else:
            for i, u in enumerate(self.urls):
                is_sel = (i == self.selected_idx)
                num_tag = f"[{i + 1}]" if i < 9 else f"[{i + 1}]"
                prefix = "▶ " if is_sel else "  "

                # Truncate if URL exceeds width
                max_url_w = inner_w - 10
                disp_url = u if len(u) <= max_url_w else u[:max_url_w - 3] + "..."

                if is_sel:
                    item_str = f"{prefix}{Style().bold(True).foreground('#00E5FF').render(num_tag)} {Style().bold(True).foreground('#FFFFFF').render(disp_url)}"
                else:
                    item_str = f"{prefix}{Style().foreground('#8888AA').render(num_tag)} {Style().foreground('#DDDDDD').render(disp_url)}"
                lines.append(item_str)

            lines.append("")
            hints = "[1-9] Quick Copy  [Enter/y] Copy  [o] Open Browser  [j/k] Navigate  [Esc] Close"
            lines.append(Style().foreground("#555577").render(hints))

        content = "\n".join(lines)
        return (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#00E5FF")
            .width(inner_w)
            .render(content)
        )
