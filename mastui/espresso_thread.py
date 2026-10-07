"""Thread conversation tree modal for viewing ancestors and replies to a post."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from espresso.beans.modal_stack import ModalCloseMsg
from espresso.beans.spinner import DOTS, Spinner
from espresso.beans.virtual_list import VirtualList
from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg, batch
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi
from mastui.espresso_post import render_post_card


@dataclass
class ThreadContextLoadedMsg(Msg):
    """Dispatched when background thread fetching completes."""
    post_id: str
    ancestors: list[dict]
    descendants: list[dict]


@dataclass
class ThreadReplyMsg(Msg):
    """Dispatched when user presses 'a' in thread modal to reply."""
    post: dict


@dataclass
class ThreadShowUrlsMsg(Msg):
    """Dispatched when user presses 'x' in thread modal to view URLs."""
    post: dict


def resolve_actual_status(post: dict) -> dict:
    """Extract the innermost actual status from notifications, conversations, or reblogs."""
    raw = post.get("status") or post.get("last_status") or post
    return raw.get("reblog") or raw


def fetch_ancestors_from_db(db_path: Path, status: dict, max_depth: int = 15) -> list[dict]:
    """Recursively fetch parent statuses up the reply chain from SQLite cache."""
    if not db_path or not db_path.exists():
        return []
    ancestors: list[dict] = []
    curr = status
    visited: set[str] = {str(status.get("id", ""))}
    try:
        conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        for _ in range(max_depth):
            parent_id = curr.get("in_reply_to_id")
            if not parent_id or str(parent_id) in visited:
                break
            visited.add(str(parent_id))
            cur.execute("SELECT data FROM posts WHERE id = ? LIMIT 1", (str(parent_id),))
            row = cur.fetchone()
            if not row:
                break
            parent_post = json.loads(row["data"])
            actual_parent = resolve_actual_status(parent_post)
            actual_parent["_thread_role"] = "ancestor"
            ancestors.insert(0, actual_parent)  # Chronological order
            curr = actual_parent
        conn.close()
    except Exception:
        pass
    return ancestors


def fetch_descendants_from_db(db_path: Path, post_id: str, max_depth: int = 30) -> list[dict]:
    """Fetch child replies and sub-replies recursively from SQLite cache."""
    if not db_path or not db_path.exists():
        return []
    descendants: list[dict] = []
    to_search = [str(post_id)]
    visited: set[str] = set(to_search)
    try:
        conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        while to_search and len(descendants) < max_depth:
            curr_id = to_search.pop(0)
            try:
                cur.execute(
                    "SELECT data FROM posts WHERE json_extract(data, '$.in_reply_to_id') = ? ORDER BY created_at ASC",
                    (curr_id,),
                )
                rows = cur.fetchall()
            except Exception:
                # Fallback if json_extract is unavailable in older SQLite
                rows = []
            for r in rows:
                child = json.loads(r["data"])
                actual_child = resolve_actual_status(child)
                cid = str(actual_child.get("id", ""))
                if cid and cid not in visited:
                    visited.add(cid)
                    actual_child["_thread_role"] = "reply"
                    descendants.append(actual_child)
                    to_search.append(cid)
        conn.close()
    except Exception:
        pass
    return descendants


def fetch_thread_context(
    post: dict,
    api: Any = None,
    all_known_posts: list[dict] | None = None,
    cache_db_path: Path | None = None,
    is_demo: bool = False,
) -> tuple[list[dict], list[dict]]:
    """Retrieve actual thread context: returns (ancestors, descendants)."""
    status = resolve_actual_status(post)
    post_id = str(status.get("id", "0"))

    ancestors: list[dict] = []
    descendants: list[dict] = []

    # 1. If API is available, fetch real status context from Mastodon instance
    if api:
        try:
            context = api.status_context(post_id)
            if context:
                for a in context.get("ancestors", []):
                    anc = dict(resolve_actual_status(a))
                    anc["_thread_role"] = "ancestor"
                    ancestors.append(anc)
                for d in context.get("descendants", []):
                    desc = dict(resolve_actual_status(d))
                    desc["_thread_role"] = "reply"
                    descendants.append(desc)
        except Exception:
            pass

    # 2. If no API results or offline, query SQLite cache.db
    if not ancestors and not descendants and cache_db_path:
        db_ancestors = fetch_ancestors_from_db(cache_db_path, status)
        db_descendants = fetch_descendants_from_db(cache_db_path, post_id)
        if db_ancestors:
            ancestors = db_ancestors
        if db_descendants:
            descendants = db_descendants

    # 3. If still empty, search local timeline posts
    if not ancestors and not descendants and all_known_posts:
        parent_id = str(status.get("in_reply_to_id") or "")
        for p in all_known_posts:
            p_actual = resolve_actual_status(p)
            curr_id = str(p_actual.get("id", ""))
            curr_parent_id = str(p_actual.get("in_reply_to_id") or "")

            if parent_id and curr_id == parent_id:
                anc = dict(p_actual)
                anc["_thread_role"] = "ancestor"
                ancestors.append(anc)
            elif curr_parent_id == post_id:
                desc = dict(p_actual)
                desc["_thread_role"] = "reply"
                descendants.append(desc)

    # 4. If in demo mode, supply rich multi-turn discussion context
    if not ancestors and not descendants and is_demo:
        if status.get("in_reply_to_id"):
            demo_ancestor = {
                "id": str(status.get("in_reply_to_id")),
                "created_at": "2026-10-02T16:00:00Z",
                "account": {
                    "display_name": "Dev Community",
                    "acct": "devs@coder.cafe",
                },
                "content": "<p>Has anyone explored building high-performance TUIs using Elm Architecture (TEA) in Python?</p>",
                "reblogs_count": 5,
                "favourites_count": 28,
                "visibility": "public",
                "_thread_role": "ancestor",
            }
            ancestors.append(demo_ancestor)

        demo_reply1 = {
            "id": f"{post_id}_demo_r1",
            "created_at": "2026-10-02T17:15:00Z",
            "account": {
                "display_name": "Fediverse Explorer",
                "acct": "explorer@social.cafe",
            },
            "content": "<p>Running full Elm Architecture in the terminal is super slick! No DOM overhead and instant sub-millisecond response.</p>",
            "reblogs_count": 4,
            "favourites_count": 19,
            "visibility": "public",
            "_thread_role": "reply",
        }
        demo_reply2 = {
            "id": f"{post_id}_demo_r2",
            "created_at": "2026-10-02T17:30:00Z",
            "account": {
                "display_name": "Terminal Hacker",
                "acct": "cli_guru@matrix.org",
            },
            "content": "<p>The multi-column layout and ANSI halfblock media rendering look fantastic! Keyboard navigation feels completely seamless.</p>",
            "reblogs_count": 2,
            "favourites_count": 11,
            "visibility": "public",
            "_thread_role": "reply",
        }
        descendants.extend([demo_reply1, demo_reply2])

    return ancestors, descendants



def fetch_thread_posts(
    post: dict,
    api: Any = None,
    all_known_posts: list[dict] | None = None,
    cache_db_path: Path | None = None,
    is_demo: bool = False,
) -> list[dict]:
    """Retrieve full thread list in order: ancestors + [focused] + descendants."""
    status = dict(resolve_actual_status(post))
    status["_thread_role"] = "main"
    ancestors, descendants = fetch_thread_context(
        status, api=api, all_known_posts=all_known_posts, cache_db_path=cache_db_path, is_demo=is_demo
    )
    return ancestors + [status] + descendants


class ThreadModal(Model):
    """Modal displaying full conversation thread tree with parents and replies."""

    def __init__(
        self,
        post: dict,
        thread_posts: list[dict] | None = None,
        api: Any = None,
        all_known_posts: list[dict] | None = None,
        cache_db_path: Path | None = None,
        is_demo: bool = False,
        width: int = 78,
        height: int = 24,
        theme: Any = None,
    ) -> None:
        self.raw_target_post = post
        self.focused_post = dict(resolve_actual_status(post))
        self.focused_post["_thread_role"] = "main"

        self.width = max(56, width)
        self.height = max(12, height)
        self.api = api
        self.all_known_posts = all_known_posts
        self.cache_db_path = cache_db_path
        self.is_demo = is_demo
        self.theme = theme

        self.spinner = Spinner(DOTS, fps=12.0)
        self.is_loading = False

        if thread_posts is not None:
            self.posts = thread_posts
        else:
            # Synchronously fetch quick local/demo context so modal is immediately responsive
            ancestors, descendants = fetch_thread_context(
                self.focused_post,
                api=None,  # don't block UI thread on network here
                all_known_posts=all_known_posts,
                cache_db_path=cache_db_path,
                is_demo=is_demo,
            )
            self.posts = ancestors + [self.focused_post] + descendants
            if self.api and not is_demo:
                self.is_loading = True

        # Find index of target post
        init_cursor = 0
        for i, p in enumerate(self.posts):
            if p.get("_thread_role") == "main" or str(p.get("id")) == str(self.focused_post.get("id")):
                init_cursor = i
                break

        card_w = max(40, self.width - 6)

        def _render_thread_item(p: dict, is_sel: bool, w: int) -> str:
            role = p.get("_thread_role", "reply")
            if role == "ancestor":
                tree_prefix = Style().bold(True).foreground("#7D56F4").render(" ▲ Parent Post in Thread:")
            elif role == "main":
                tree_prefix = Style().bold(True).foreground("#00E5FF").render(" ★ Selected Post:")
            else:
                tree_prefix = Style().foreground("#555577").render(" └── Reply:")

            card = render_post_card(p, is_selected=is_sel, width=w - 2, theme=self.theme)
            return f"{tree_prefix}\n{card}"

        thumb_col = getattr(theme, "scrollbar_thumb", "#7D56F4") if theme else "#7D56F4"
        track_col = getattr(theme, "scrollbar_track", "#2A2A40") if theme else "#333344"

        self.list = VirtualList(
            items=self.posts,
            render_item=_render_thread_item,
            width=card_w,
            height=max(6, self.height - 6),
            show_scrollbar=True,
            focused=True,
            scrollbar_thumb_style=Style().foreground(thumb_col).bold(True),
            scrollbar_track_style=Style().foreground(track_col),
        )
        self.list.cursor = init_cursor

    @property
    def selected_post(self) -> dict | None:
        return self.list.selected_item

    def init(self) -> Cmd | None:
        cmds: list[Cmd] = []
        if self.is_loading:
            s_cmd = self.spinner.init()
            if s_cmd:
                cmds.append(s_cmd)
            cmds.append(self._start_async_thread_fetch())
        elif self.api and not self.is_demo:
            self.is_loading = True
            s_cmd = self.spinner.init()
            if s_cmd:
                cmds.append(s_cmd)
            cmds.append(self._start_async_thread_fetch())
        return batch(*cmds) if cmds else None

    def _start_async_thread_fetch(self) -> Cmd:
        target = self.focused_post
        api = self.api
        all_posts = self.all_known_posts
        cache_path = self.cache_db_path
        is_demo = self.is_demo

        def _fetch_task() -> Msg:
            try:
                anc, desc = fetch_thread_context(
                    target,
                    api=api,
                    all_known_posts=all_posts,
                    cache_db_path=cache_path,
                    is_demo=is_demo,
                )
                return ThreadContextLoadedMsg(
                    post_id=str(target.get("id", "0")),
                    ancestors=anc,
                    descendants=desc,
                )
            except Exception:
                return ThreadContextLoadedMsg(
                    post_id=str(target.get("id", "0")),
                    ancestors=[],
                    descendants=[],
                )

        return _fetch_task

    def update(self, msg: Msg) -> tuple[ThreadModal, Cmd | None]:
        cmds: list[Cmd] = []

        if isinstance(msg, ThreadContextLoadedMsg):
            if msg.post_id == str(self.focused_post.get("id", "0")):
                self.is_loading = False
                if msg.ancestors or msg.descendants:
                    self.posts = msg.ancestors + [self.focused_post] + msg.descendants
                    self.list.set_items(self.posts)
                    self.list.select(len(msg.ancestors))
                    self.list.invalidate_cache()
            return self, None

        if self.is_loading:
            self.spinner, s_cmd = self.spinner.update(msg)
            if s_cmd:
                cmds.append(s_cmd)

        if isinstance(msg, KeyMsg):
            match msg.key:
                case "esc" | "q":
                    def _close() -> Msg:
                        return ModalCloseMsg()
                    return self, _close
                case "r":  # Refresh thread
                    self.is_loading = True
                    s_cmd = self.spinner.init()
                    if s_cmd:
                        cmds.append(s_cmd)
                    cmds.append(self._start_async_thread_fetch())
                    return self, batch(*cmds)
                case "a":  # Reply to selected post
                    if self.selected_post:
                        sel = self.selected_post
                        def _reply() -> Msg:
                            return ThreadReplyMsg(sel)
                        return self, _reply
                case "x":  # Show URLs
                    if self.selected_post:
                        sel = self.selected_post
                        def _urls() -> Msg:
                            return ThreadShowUrlsMsg(sel)
                        return self, _urls
                case "l" | "f":
                    if self.selected_post:
                        p = self.selected_post
                        p["favourited"] = not p.get("favourited", False)
                        p["favourites_count"] = max(0, p.get("favourites_count", 0) + (1 if p["favourited"] else -1))
                        self.list.invalidate_cache()
                    return self, None
                case "b":
                    if self.selected_post:
                        p = self.selected_post
                        p["reblogged"] = not p.get("reblogged", False)
                        p["reblogs_count"] = max(0, p.get("reblogs_count", 0) + (1 if p["reblogged"] else -1))
                        self.list.invalidate_cache()
                    return self, None

        self.list, cmd = self.list.update(msg)
        if cmd:
            cmds.append(cmd)
        return self, batch(*cmds) if cmds else None

    def view(self) -> str:
        """Render thread dialog."""
        inner_w = max(46, self.width - 4)

        header = Style().bold(True).foreground("#00E5FF").render("🧵 CONVERSATION THREAD")
        
        anc_count = sum(1 for p in self.posts if p.get("_thread_role") == "ancestor")
        desc_count = sum(1 for p in self.posts if p.get("_thread_role") == "reply")

        if self.is_loading:
            status_line = f"{self.spinner.view()} " + Style().foreground("#00E5FF").render("Fetching thread replies and parents...")
        elif anc_count == 0 and desc_count == 0:
            status_line = Style().foreground("#777799").render("Showing standalone toot (no parent or replies found)")
        else:
            parts = []
            if anc_count:
                parts.append(f"{anc_count} parent {'post' if anc_count == 1 else 'posts'}")
            parts.append("1 selected")
            if desc_count:
                parts.append(f"{desc_count} {'reply' if desc_count == 1 else 'replies'}")
            status_line = Style().foreground("#00E676").render(f"✓ Thread tree: {' · '.join(parts)}")

        self.list.set_size(inner_w - 2, max(6, self.height - 7))
        list_view = self.list.view()

        hints = "[j/k] Move  [a] Reply  [l] Like  [b] Boost  [x] Links  [r] Refresh  [Esc] Close"
        hint_line = Style().foreground("#666688").render(hints)

        content = f"{header}\n{status_line}\n\n{list_view}\n\n{hint_line}"
        return (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#00E5FF")
            .width(inner_w)
            .render(content)
        )
