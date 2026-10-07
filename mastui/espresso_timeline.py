"""Interactive Timeline model using VirtualList, Crema post cards, and animated Spinners."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from espresso.beans.spinner import DOTS, Spinner, SpinnerTickMsg
from espresso.beans.virtual_list import VirtualList, VirtualListChangeMsg
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg, batch
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi
from mastui.espresso_post import render_post_card


@dataclass(frozen=True)
class NeedOlderPostsMsg(Msg):
    """Message emitted when user scrolls near the end of timeline."""

    timeline_id: str
    max_id: str


@dataclass(frozen=True)
class NeedRefreshMsg(Msg):
    """Message emitted when a timeline starts refreshing."""

    timeline_id: str
    since_id: str | None = None


class TimelineModel(Model):
    """A single timeline column displaying posts via VirtualList with pagination and spinner."""

    def __init__(
        self,
        timeline_id: str = "home",
        title: str = "Home Timeline",
        posts: list[dict] | None = None,
        width: int = 70,
        height: int = 24,
        is_active: bool = True,
        enabled: bool = True,
        profile_dir: Any = None,
        show_images: bool = True,
        theme: Any = None,
    ) -> None:
        self.timeline_id = timeline_id
        self.title = title
        self.posts: list[dict] = list(posts) if posts else []
        self.width = max(24, width)
        self.height = max(10, height)
        self.is_active = is_active
        self.enabled = enabled
        self.profile_dir = profile_dir
        self.show_images = show_images
        self.theme = theme
        self.revealed_spoilers: set[str] = set()

        # Loading & Refresh states
        self.is_refreshing: bool = False
        self.is_loading_more: bool = False
        self.has_more: bool = True
        self.spinner = Spinner(DOTS, fps=12.0, tag=f"sp_{timeline_id}")

        # Build VirtualList with custom post card renderer
        card_w = max(20, self.width - 2)

        def _render_post(post: dict, is_selected: bool, w: int) -> str:
            post_id = str(post.get("id", ""))
            show_revealed = (post_id in self.revealed_spoilers)
            return render_post_card(
                post,
                is_selected=is_selected and self.is_active,
                width=w,
                show_spoiler_revealed=show_revealed,
                profile_dir=self.profile_dir,
                show_images=self.show_images,
                theme=self.theme,
            )

        self.list = VirtualList(
            items=self.posts,
            render_item=_render_post,
            width=card_w,
            height=max(5, self.height - 3),
            show_scrollbar=True,
            focused=self.is_active,
        )
        self._apply_scrollbar_theme()

    def _apply_scrollbar_theme(self) -> None:
        if not self.theme:
            return
        thumb_col = getattr(self.theme, "scrollbar_thumb", None) or getattr(self.theme, "secondary", "#7D56F4")
        track_col = getattr(self.theme, "scrollbar_track", None) or getattr(self.theme, "surface", "#252438")
        self.list.scrollbar_thumb_style = Style().foreground(thumb_col).bold(True)
        self.list.scrollbar_track_style = Style().foreground(track_col)

    def set_theme(self, theme: Any) -> None:
        self.theme = theme
        self._apply_scrollbar_theme()
        self.list.invalidate_cache()

    def set_show_images(self, show: bool) -> None:
        self.show_images = show
        self.list.invalidate_cache()

    @property
    def selected_post(self) -> dict | None:
        return self.list.selected_item

    @property
    def oldest_post_id(self) -> str | None:
        if not self.posts:
            return None
        last = self.posts[-1].get("reblog") or self.posts[-1]
        return str(last.get("id"))

    @property
    def latest_post_id(self) -> str | None:
        if not self.posts:
            return None
        for p in self.posts:
            pid = str(p.get("id", ""))
            if pid and pid != "welcome_empty" and not pid.startswith("welcome"):
                return pid
        return None

    def set_posts(self, posts: list[dict]) -> None:
        self.posts = list(posts)
        self.list.set_items(self.posts, keep_anchor=True, anchor_id_fn=lambda p: str(p.get("id")))

    def append_older_posts(self, older: list[dict]) -> None:
        self.is_loading_more = False
        if not older:
            self.has_more = False
            return
        # Filter duplicates based on post ID
        existing_ids = {str(p.get("id")) for p in self.posts}
        new_items = [p for p in older if str(p.get("id")) not in existing_ids]
        if not new_items:
            self.has_more = False
        else:
            self.posts.extend(new_items)
            self.list.set_items(self.posts, keep_anchor=True, anchor_id_fn=lambda p: str(p.get("id")))

    def prepend_newer_posts(self, newer: list[dict]) -> None:
        self.is_refreshing = False
        if not newer:
            return

        # Clear placeholder if real posts have arrived
        self.posts = [p for p in self.posts if str(p.get("id")) != "welcome_empty"]

        existing_ids = {str(p.get("id")) for p in self.posts}
        new_items = [p for p in newer if str(p.get("id")) not in existing_ids]
        if not new_items:
            return

        was_at_top = (self.list.cursor == 0 and self.list.scroll_offset == 0)

        # Prepend new items (newest at index 0)
        self.posts = new_items + self.posts

        if was_at_top:
            # If user was viewing the top, show the brand new posts immediately at the top!
            self.list.set_items(self.posts, keep_anchor=False)
            self.list.cursor = 0
            self.list.scroll_offset = 0
        else:
            # If user was scrolled down reading older posts, maintain reading position
            self.list.set_items(self.posts, keep_anchor=True, anchor_id_fn=lambda p: str(p.get("id")))

        self.list.invalidate_cache()

    def toggle_current_favourite(self) -> dict | None:
        post = self.selected_post
        if not post:
            return None
        target = post.get("reblog") or post
        target["favourited"] = not target.get("favourited", False)
        target["favourites_count"] = max(0, target.get("favourites_count", 0) + (1 if target["favourited"] else -1))
        return target

    def toggle_current_reblog(self) -> dict | None:
        post = self.selected_post
        if not post:
            return None
        target = post.get("reblog") or post
        target["reblogged"] = not target.get("reblogged", False)
        target["reblogs_count"] = max(0, target.get("reblogs_count", 0) + (1 if target["reblogged"] else -1))
        return target

    def toggle_spoiler_reveal(self) -> None:
        post = self.selected_post
        if not post:
            return
        post_id = str(post.get("id", ""))
        if post_id in self.revealed_spoilers:
            self.revealed_spoilers.remove(post_id)
        else:
            self.revealed_spoilers.add(post_id)
        self.list.invalidate_cache()

    def set_size(self, width: int, height: int) -> None:
        self.width = max(24, width)
        self.height = max(10, height)
        inner_w = max(20, self.width - 2)
        inner_h = max(5, self.height - 4)
        self.list.set_size(inner_w, inner_h)

    def jump_to_top(self) -> tuple[TimelineModel, Cmd | None]:
        """Jump to the first post in the timeline."""
        self.list.select(0)
        return self, None

    def trigger_refresh(self) -> tuple[TimelineModel, Cmd | None]:
        """Initiate refreshing animation and emit refresh message."""
        if self.is_refreshing:
            return self, None
        self.is_refreshing = True
        s_cmd = self.spinner.init()
        tl_id = self.timeline_id
        since_id = self.latest_post_id

        def _emit_refresh() -> Msg:
            return NeedRefreshMsg(timeline_id=tl_id, since_id=since_id)

        return self, batch(s_cmd, _emit_refresh)

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[TimelineModel, Cmd | None]:
        cmds: list[Cmd] = []

        # Handle spinner ticks
        if isinstance(msg, SpinnerTickMsg) and msg.tag == self.spinner.tag:
            self.spinner, s_cmd = self.spinner.update(msg)
            if self.is_refreshing or self.is_loading_more:
                return self, s_cmd
            return self, None

        if not self.is_active:
            return self, None

        if isinstance(msg, KeyMsg):
            match msg.key:
                case "s":  # Content Warning spoiler toggle
                    self.toggle_spoiler_reveal()
                    return self, None
                case "g" | "home":
                    return self.jump_to_top()
                case "k" | "up":
                    if self.list.cursor == 0 and not self.is_refreshing:
                        return self.trigger_refresh()

        if isinstance(msg, MouseMsg):
            if msg.button == MouseButton.WHEEL_UP:
                if self.list.cursor == 0 and not self.is_refreshing:
                    return self.trigger_refresh()
                self.list, cmd = self.list.update(msg)
                self._check_pagination(cmds)
                return self, cmd
            if msg.button == MouseButton.WHEEL_DOWN:
                self.list, cmd = self.list.update(msg)
                self._check_pagination(cmds)
                return self, cmd
            if msg.button == MouseButton.LEFT and msg.action == MouseAction.PRESS:
                if msg.y <= 1:
                    # Click on title bar jumps to top
                    return self, self.list.select(0)[1]
                list_y = msg.y - 3
                list_x = max(0, msg.x - 1)
                if 0 <= list_y < self.list.height:
                    translated = MouseMsg(
                        x=list_x,
                        y=list_y,
                        button=msg.button,
                        action=msg.action,
                        ctrl=msg.ctrl,
                        alt=msg.alt,
                        shift=msg.shift,
                    )
                    self.list, cmd = self.list.update(translated)
                    self._check_pagination(cmds)
                    return self, cmd

        self.list, cmd = self.list.update(msg)
        if cmd:
            cmds.append(cmd)

        self._check_pagination(cmds)

        if len(cmds) == 1:
            return self, cmds[0]
        elif len(cmds) > 1:
            from espresso import batch
            return self, batch(*cmds)
        return self, None

    def _check_pagination(self, cmds: list[Cmd]) -> None:
        """Check if user scrolled near bottom to trigger loading older posts."""
        if (
            len(self.posts) >= 3
            and self.list.cursor >= len(self.posts) - 2
            and not self.is_loading_more
            and self.has_more
        ):
            self.is_loading_more = True
            cmds.append(self.spinner.init())
            tl_id = self.timeline_id
            oldest_id = self.oldest_post_id or ""

            def _emit_load_more() -> Msg:
                return NeedOlderPostsMsg(timeline_id=tl_id, max_id=oldest_id)

            cmds.append(_emit_load_more)

    def view(self) -> str:
        """Render the timeline column with title banner, spinner, and virtual list."""
        inner_w = max(20, self.width - 2)
        inner_h = max(5, self.height - 4)

        # Theme colors
        primary = self.theme.primary if self.theme else "#00E5FF"
        border_dim = self.theme.border_dim if self.theme else "#33334A"

        # Title bar
        title_style = Style().bold(True).foreground(primary if self.is_active else "#8888AA")

        # Spinner & status indicators
        if self.is_refreshing:
            status_str = f" {self.spinner.view()} {Style().bold(True).foreground(primary).render('Refreshing...')}"
        elif self.is_loading_more:
            status_str = f" {self.spinner.view()} {Style().faint(True).foreground('#AAAAAA').render('Loading older...')}"
        else:
            post_count_str = f"({len(self.posts)} posts)"
            status_str = f" {Style().faint(True).render(post_count_str)}"

        title_line = f" {title_style.render(self.title)}{status_str}"

        # Content view from VirtualList
        self.list.set_size(inner_w, inner_h)
        self.list.focused = self.is_active
        list_view = self.list.view()

        content = f"{title_line}\n\n{list_view}"
        border_color = primary if self.is_active else border_dim

        return (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground(border_color)
            .width(inner_w)
            .render(content)
        )
