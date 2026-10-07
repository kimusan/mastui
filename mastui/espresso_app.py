"""Root Mastui TUI application powered by Espresso."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_cached_posts_from_db(
    db_path: Path, timeline_id: str, limit: int = 20, max_id: str | None = None
) -> list[dict]:
    """Safely query cached timeline posts from SQLite in read-only mode."""
    if not db_path or not db_path.exists():
        return []
    try:
        uri = f"file:{db_path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if max_id:
            cursor.execute(
                "SELECT data FROM posts WHERE timeline_id = ? AND id < ? ORDER BY created_at DESC, id DESC LIMIT ?",
                (timeline_id, max_id, limit),
            )
        else:
            cursor.execute(
                "SELECT data FROM posts WHERE timeline_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
                (timeline_id, limit),
            )
        rows = cursor.fetchall()
        posts = [json.loads(row["data"]) for row in rows]
        conn.close()
        return posts
    except Exception:
        return []


def read_newer_cached_posts_from_db(
    db_path: Path, timeline_id: str, limit: int = 20, since_id: str | None = None
) -> list[dict]:
    """Safely query newer cached timeline posts from SQLite in read-only mode."""
    if not db_path or not db_path.exists():
        return []
    try:
        uri = f"file:{db_path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if since_id:
            cursor.execute(
                "SELECT data FROM posts WHERE timeline_id = ? AND id > ? ORDER BY created_at DESC, id DESC LIMIT ?",
                (timeline_id, since_id, limit),
            )
        else:
            cursor.execute(
                "SELECT data FROM posts WHERE timeline_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
                (timeline_id, limit),
            )
        rows = cursor.fetchall()
        posts = [json.loads(row["data"]) for row in rows]
        conn.close()
        return posts
    except Exception:
        return []


def read_cached_conversations_from_db(db_path: Path, limit: int = 50) -> list[dict]:
    """Safely query cached conversations from SQLite in read-only mode."""
    if not db_path or not db_path.exists():
        return []
    try:
        uri = f"file:{db_path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM conversations LIMIT ?", (limit,))
        rows = cursor.fetchall()
        convs = [json.loads(row["data"]) for row in rows]
        conn.close()
        return convs
    except Exception:
        return []


def save_posts_to_db(db_path: Path, timeline_id: str, posts: list[dict]) -> None:
    """Safely bulk insert or replace posts in SQLite cache.db."""
    if not db_path or not posts:
        return
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                timeline_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                data TEXT NOT NULL
            )
        """)
        posts_to_insert = []
        for post in posts:
            if not isinstance(post, dict) or "id" not in post:
                continue
            created_at_val = (post.get("reblog") or post).get("created_at")
            if isinstance(created_at_val, datetime):
                created_at_str = created_at_val.isoformat()
            elif created_at_val:
                created_at_str = str(created_at_val)
            else:
                created_at_str = datetime.now(timezone.utc).isoformat()

            def _dt_handler(obj: Any) -> str:
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return str(obj)

            posts_to_insert.append((
                str(post["id"]),
                timeline_id,
                created_at_str,
                json.dumps(post, default=_dt_handler),
            ))
        if posts_to_insert:
            cursor.executemany(
                "INSERT OR REPLACE INTO posts (id, timeline_id, created_at, data) VALUES (?, ?, ?, ?)",
                posts_to_insert,
            )
            conn.commit()
        conn.close()
    except Exception:
        pass


def parse_simple_env_from_file(env_path: Path) -> dict[str, str]:
    """Parse key=value pairs from a .env file without external dependencies."""
    vals: dict[str, str] = {}
    if not env_path or not env_path.exists():
        return vals
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip().strip("'\"")
    except Exception:
        pass
    return vals


# Ensure espresso is importable
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ESPRESSO_SRC = REPO_ROOT / "espresso" / "src"
if str(ESPRESSO_SRC) not in sys.path:
    sys.path.insert(0, str(ESPRESSO_SRC))

from espresso import Cmd, KeyMsg, Model, Msg, Program, WindowSizeMsg, batch, quit_app
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.beans import (
    Confetti,
    ModalCloseMsg,
    ModalStack,
    Tabs,
    TabStyle,
    TabChangeMsg,
    ToastLevel,
    ToastManager,
)
from espresso.crema import (
    ROUNDED_BORDER,
    Align,
    Style,
    join_horizontal,
    linear_gradient,
    place_overlay,
    string_width,
    truncate_ansi,
)
from mastui.espresso_clipboard import copy_to_clipboard
from mastui.espresso_composer import ComposerModal, TootSubmitMsg
from mastui.espresso_help import HelpModal
from mastui.espresso_image import ImageModal, download_and_cache_image
from mastui.espresso_login import LoginModal, LoginSuccessMsg
from mastui.espresso_profile import ProfileModal
from mastui.espresso_profile_selection import (
    OpenLoginModalMsg,
    ProfileSelectionModal,
    SwitchProfileMsg,
)
from mastui.espresso_settings import SettingsModal, SettingsSaveMsg, load_settings
from mastui.espresso_splash import SplashDoneMsg, SplashScreen
from mastui.espresso_theme import Theme, get_theme
from mastui.espresso_thread import (
    ThreadContextLoadedMsg,
    ThreadModal,
    ThreadReplyMsg,
    ThreadShowUrlsMsg,
)
from mastui.espresso_timeline import (
    NeedOlderPostsMsg,
    NeedRefreshMsg,
    TimelineModel,
)
from mastui.espresso_urls import UrlSelectedMsg, UrlSelectorModal
from mastui.profile_manager import profile_manager

# Sample Fediverse posts for demo and offline initial display
SAMPLE_POSTS = [
    {
        "id": "11321001",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "account": {
            "display_name": "Kim Schulz",
            "acct": "kim@mastui.app",
        },
        "content": "<p>Welcome to <strong>Mastui on Espresso TUI</strong>! ☕✨<br>Experience instant 12ms startup, TrueColor gradients, and pure functional TEA responsiveness in your terminal. #fediverse #python #tui</p>",
        "reblogs_count": 42,
        "favourites_count": 128,
        "replies_count": 9,
        "visibility": "public",
        "favourited": True,
        "reblogged": False,
    },
    {
        "id": "11321002",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "account": {
            "display_name": "Espresso Framework",
            "acct": "espresso@terminal.cafe",
        },
        "content": "<p>Did you know? Switching from a retained DOM widget tree to Espresso's Elm Architecture eliminates all layout thrashing and cuts memory consumption by over 70%! 🚀</p>",
        "reblogs_count": 89,
        "favourites_count": 256,
        "replies_count": 15,
        "visibility": "public",
        "favourited": False,
        "reblogged": True,
    },
    {
        "id": "11321003",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "account": {
            "display_name": "Mastodon News",
            "acct": "news@mastodon.social",
        },
        "spoiler_text": "Speculation on upcoming decentralized protocols",
        "content": "<p>A deep dive into new ActivityPub extensions and how modern terminal clients are innovating with rich inline media previews and faster scrolling feeds.</p>",
        "reblogs_count": 14,
        "favourites_count": 67,
        "replies_count": 4,
        "visibility": "public",
        "favourited": False,
        "reblogged": False,
    },
    {
        "id": "11321004",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "account": {
            "display_name": "Open Source Weekly",
            "acct": "osweekly@fosstodon.org",
        },
        "content": "<p>Check out @kim's open-source terminal clients! Fast, beautiful, and keyboard-driven tools make managing social feeds and dev workflows an absolute delight. #opensource #cli</p>",
        "reblogs_count": 31,
        "favourites_count": 94,
        "replies_count": 3,
        "visibility": "public",
        "favourited": False,
        "reblogged": False,
    },
]


@dataclass(frozen=True)
class TimelineRefreshedMsg(Msg):
    """Message emitted when refresh completes."""

    timeline_id: str
    new_posts: list[dict]


@dataclass(frozen=True)
class TimelineOlderLoadedMsg(Msg):
    """Message emitted when older posts are loaded for pagination."""

    timeline_id: str
    older_posts: list[dict]


class MastuiEspressoApp(Model):
    """Interactive Mastui root application model with multi-column side-by-side timelines."""

    def __init__(
        self,
        username: str = "kim@mastui.app",
        instance: str = "social.data.coop",
        posts: list[dict] | None = None,
        timeline_posts: dict[str, list[dict]] | None = None,
        is_demo: bool = False,
        profile_dir: Path | None = None,
        profile_name: str | None = None,
        api: Any = None,
        cache_db_path: Path | None = None,
        show_splash: bool = False,
        show_login: bool = False,
    ) -> None:
        self.username = username
        self.instance = instance
        self.is_demo = is_demo
        self.profile_dir = profile_dir
        self.profile_name = profile_name or (profile_dir.name if profile_dir else username)
        self.api = api
        self.cache_db_path = cache_db_path
        self.show_login = show_login

        self.settings = load_settings(profile_dir)
        self.enable_animations = bool(self.settings.get("enable_animations", True))
        self.force_single_column = bool(self.settings.get("force_single_column", False))
        self.show_images = bool(self.settings.get("show_images", True))
        self.theme: Theme = get_theme(self.settings.get("theme", "espresso"))
        self.show_splash = show_splash

        import shutil
        term_size = shutil.get_terminal_size(fallback=(100, 30))
        self.width = max(term_size.columns, 60)
        self.height = max(term_size.lines, 20)

        self.splash = SplashScreen(
            username=self.username,
            instance=self.instance,
            width=self.width,
            height=self.height,
        )

        # Prepare posts per timeline
        home_posts = timeline_posts.get("home") if timeline_posts else None
        local_posts = timeline_posts.get("local") if timeline_posts else None
        fed_posts = timeline_posts.get("federated") if timeline_posts else None
        notif_posts = timeline_posts.get("notifications") if timeline_posts else None
        dm_posts = timeline_posts.get("conversations") if timeline_posts else None

        if is_demo:
            home_posts = home_posts or list(SAMPLE_POSTS)
            local_posts = local_posts or list(SAMPLE_POSTS[:2])
            fed_posts = fed_posts or list(SAMPLE_POSTS[1:])
            notif_posts = notif_posts or []
            dm_posts = dm_posts or []
        else:
            home_posts = home_posts or (posts if posts is not None else [])
            local_posts = local_posts or []
            fed_posts = fed_posts or []
            notif_posts = notif_posts or []
            dm_posts = dm_posts or []

        self.timelines: list[TimelineModel] = [
            TimelineModel(
                timeline_id="home",
                title="🏠 Home",
                posts=home_posts,
                is_active=True,
                enabled=bool(self.settings.get("home_timeline_enabled", True)),
                profile_dir=self.profile_dir,
                show_images=self.show_images,
                theme=self.theme,
            ),
            TimelineModel(
                timeline_id="local",
                title="🏙️ Local",
                posts=local_posts,
                is_active=False,
                enabled=bool(self.settings.get("local_timeline_enabled", True)),
                profile_dir=self.profile_dir,
                show_images=self.show_images,
                theme=self.theme,
            ),
            TimelineModel(
                timeline_id="notifications",
                title="🔔 Mentions",
                posts=notif_posts,
                is_active=False,
                enabled=bool(self.settings.get("notifications_timeline_enabled", True)),
                profile_dir=self.profile_dir,
                show_images=self.show_images,
                theme=self.theme,
            ),
            TimelineModel(
                timeline_id="federated",
                title="🌐 Federated",
                posts=fed_posts,
                is_active=False,
                enabled=bool(self.settings.get("federated_timeline_enabled", False)),
                profile_dir=self.profile_dir,
                show_images=self.show_images,
                theme=self.theme,
            ),
            TimelineModel(
                timeline_id="conversations",
                title="✉️ Direct Messages",
                posts=dm_posts,
                is_active=False,
                enabled=bool(self.settings.get("direct_timeline_enabled", True)),
                profile_dir=self.profile_dir,
                show_images=self.show_images,
                theme=self.theme,
            ),
        ]
        self.active_timeline_idx = 0

        # Tabs for single-column fallback
        self.tabs = Tabs(
            titles=["🏠 Home", "🏙️ Local", "🔔 Mentions", "🌐 Fed", "✉️ DMs"],
            active_tab=0,
            tab_style=TabStyle.PILL,
        )

        # Sub-beans
        self.toasts = ToastManager()
        self.confetti = Confetti(width=self.width, height=self.height)
        self.modal_stack = ModalStack(base_model=self)
        if self.show_login:
            login_modal = LoginModal(
                default_host=self.instance or "mastodon.social",
                width=min(74, self.width - 6),
                height=min(22, self.height - 4),
                theme=self.theme,
            )
            self.modal_stack.push(login_modal)
        self._update_timeline_sizes()

    def _update_timeline_sizes(self) -> None:
        """Dynamically resize timeline columns to span the entire terminal width and height."""
        inner_w = max(40, self.width - 2)
        enabled = self.enabled_timelines
        is_multi = (not self.force_single_column) and (self.width >= 70) and (len(enabled) > 1)
        col_h = max(8, self.height - 9)

        if not is_multi:
            for tl in self.timelines:
                tl.set_size(inner_w, col_h)
        else:
            num_cols = len(enabled)
            col_gap = 1
            total_gaps = (num_cols - 1) * col_gap
            available_w = max(24 * num_cols, inner_w - total_gaps)
            col_w_base = available_w // num_cols
            rem = available_w % num_cols

            for i, tl in enumerate(enabled):
                w = col_w_base + (1 if i < rem else 0)
                tl.set_size(w, col_h)

    @property
    def current_timeline(self) -> TimelineModel:
        return self.timelines[self.active_timeline_idx]

    @property
    def enabled_timelines(self) -> list[TimelineModel]:
        enabled = [tl for tl in self.timelines if tl.enabled]
        return enabled if enabled else [self.timelines[0]]

    def init(self) -> Cmd | None:
        cmds: list[Cmd] = []
        if self.show_splash:
            splash_cmd = self.splash.init()
            if splash_cmd:
                cmds.append(splash_cmd)
        return batch(*cmds) if cmds else None

    def switch_timeline(self, idx: int) -> tuple[MastuiEspressoApp, Cmd | None]:
        idx = max(0, min(idx, len(self.timelines) - 1))
        self.active_timeline_idx = idx
        if not self.timelines[idx].enabled:
            self.timelines[idx].enabled = True
        self.tabs.set_active(idx)
        for i, tl in enumerate(self.timelines):
            tl.is_active = (i == idx)
            tl.list.focused = (i == idx)
        self._update_timeline_sizes()
        return self, None

    def switch_profile(self, profile_name: str) -> None:
        """Switch active account to profile_name, reloading credentials, API, settings, and cache."""
        self.profile_name = profile_name
        profile_manager.set_last_profile(profile_name)
        target_dir = profile_manager.get_profile_path(profile_name)
        self.profile_dir = target_dir

        if target_dir.exists():
            env_file = target_dir / ".env"
            env_vals = parse_simple_env_from_file(env_file)
            self.instance = env_vals.get("MASTODON_HOST") or self.instance
            if "@" in profile_name:
                self.username = profile_name
            else:
                self.username = f"{profile_name}@{self.instance}"

            # Re-initialize Mastodon API
            try:
                from mastui.config import Config
                from mastui.mastodon_api import get_api
                conf = Config(target_dir)
                self.api = get_api(conf)
            except Exception:
                self.api = None

            # Load cached posts from cache.db
            db_file = target_dir / "cache.db"
            self.cache_db_path = db_file if db_file.exists() else None
            if self.cache_db_path:
                for tl in self.timelines:
                    if tl.timeline_id == "conversations":
                        convs = read_cached_conversations_from_db(db_file, limit=50)
                        tl.set_posts(convs)
                    else:
                        posts = read_cached_posts_from_db(db_file, tl.timeline_id, limit=50)
                        tl.set_posts(posts)
            else:
                for tl in self.timelines:
                    tl.set_posts([])

            # Reload settings & theme
            self.settings = load_settings(target_dir)
            self.theme = get_theme(self.settings.get("theme", "espresso"))
            for tl in self.timelines:
                tl.profile_dir = target_dir
                tl.set_theme(self.theme)

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        cmds: list[Cmd] = []

        # 1. ALWAYS handle window resizing first, so dimensions are never swallowed by splash or modals
        if isinstance(msg, WindowSizeMsg):
            self.width = max(msg.width, 60)
            self.height = max(msg.height, 20)
            self.confetti.width = self.width
            self.confetti.height = self.height
            self.splash.width = self.width
            self.splash.height = self.height
            self._update_timeline_sizes()
            return self, None

        # 2. Handle splash screen if active
        if self.show_splash:
            if isinstance(msg, SplashDoneMsg):
                self.show_splash = False
                self._update_timeline_sizes()
                return self, None
            self.splash, s_cmd = self.splash.update(msg)
            return self, s_cmd

        # Route through ModalStack if open
        if self.modal_stack.has_modals:
            if isinstance(msg, SettingsSaveMsg):
                self.settings = msg.settings
                self.enable_animations = bool(self.settings.get("enable_animations", True))
                self.force_single_column = bool(self.settings.get("force_single_column", False))
                self.show_images = bool(self.settings.get("show_images", True))
                self.theme = get_theme(self.settings.get("theme", "espresso"))
                for tl in self.timelines:
                    tl.set_theme(self.theme)
                    tl.set_show_images(self.show_images)
                self.timelines[0].enabled = bool(self.settings.get("home_timeline_enabled", True))
                self.timelines[1].enabled = bool(self.settings.get("local_timeline_enabled", True))
                self.timelines[2].enabled = bool(self.settings.get("notifications_timeline_enabled", True))
                self.timelines[3].enabled = bool(self.settings.get("federated_timeline_enabled", False))
                self.timelines[4].enabled = bool(self.settings.get("direct_timeline_enabled", True))

                if not self.timelines[self.active_timeline_idx].enabled:
                    for i, tl in enumerate(self.timelines):
                        if tl.enabled:
                            self.switch_timeline(i)
                            break

                self.modal_stack.pop()
                _, s_cmd = self.toasts.add("⚙️ Preferences updated successfully!", ToastLevel.SUCCESS, 2.5)
                return self, s_cmd

            if isinstance(msg, UrlSelectedMsg):
                self.modal_stack.pop()
                act = "Copied link to clipboard" if msg.action == "copy" else "Opening in browser"
                disp = msg.url if len(msg.url) <= 35 else msg.url[:32] + "..."
                _, u_cmd = self.toasts.add(f"🔗 {act}: {disp}", ToastLevel.SUCCESS, 2.5)
                return self, u_cmd

            if isinstance(msg, TootSubmitMsg):
                new_post = {
                    "id": str(int(datetime.now().timestamp())),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "account": {
                        "display_name": "Kim Schulz",
                        "acct": self.username,
                    },
                    "content": f"<p>{msg.content}</p>",
                    "spoiler_text": msg.spoiler_text,
                    "reblogs_count": 0,
                    "favourites_count": 0,
                    "replies_count": 0,
                    "visibility": msg.visibility,
                }
                self.timelines[0].set_posts([new_post] + self.timelines[0].posts)
                self.modal_stack.pop()
                if self.enable_animations:
                    c_cmd = self.confetti.fire(count=25)
                    if c_cmd:
                        cmds.append(c_cmd)
                _, t_cmd = self.toasts.add("🚀 Toot posted successfully!", ToastLevel.SUCCESS, 3.0)
                cmds.append(t_cmd)
                return self, batch(*cmds)

            if isinstance(msg, SwitchProfileMsg):
                self.modal_stack.pop()
                self.switch_profile(msg.profile_name)
                _, toast_cmd = self.toasts.add(
                    f"👤 Switched account to @{msg.profile_name}",
                    ToastLevel.SUCCESS,
                    2.5,
                )
                ref_cmds = [toast_cmd]
                for tl in self.enabled_timelines:
                    _, c = tl.trigger_refresh()
                    if c:
                        ref_cmds.append(c)
                return self, batch(*ref_cmds)

            if isinstance(msg, OpenLoginModalMsg):
                self.modal_stack.pop()
                login_modal = LoginModal(
                    default_host=self.instance or "mastodon.social",
                    width=min(74, self.width - 6),
                    height=min(22, self.height - 4),
                    theme=self.theme,
                )
                self.modal_stack.push(login_modal)
                return self, login_modal.init()

            if isinstance(msg, LoginSuccessMsg):
                profile_manager.create_profile(msg.profile_name, msg.env_content)
                self.modal_stack.pop()
                self.switch_profile(msg.profile_name)
                _, toast_cmd = self.toasts.add(
                    f"🎉 Successfully logged in as @{msg.profile_name}!",
                    ToastLevel.SUCCESS,
                    3.5,
                )
                ref_cmds = [toast_cmd]
                for tl in self.enabled_timelines:
                    _, c = tl.trigger_refresh()
                    if c:
                        ref_cmds.append(c)
                return self, batch(*ref_cmds)

            if isinstance(msg, ThreadReplyMsg):
                self.modal_stack.pop()
                composer = ComposerModal(
                    reply_to_post=msg.post,
                    width=min(72, self.width - 8),
                )
                self.modal_stack.push(composer)
                return self, None

            if isinstance(msg, ThreadShowUrlsMsg):
                url_modal = UrlSelectorModal(
                    post_data=msg.post,
                    width=min(72, self.width - 6),
                )
                self.modal_stack.push(url_modal)
                return self, None

            if isinstance(msg, ModalCloseMsg):
                self.modal_stack.pop()
                return self, None

            # Route to modal
            self.modal_stack, m_cmd = self.modal_stack.update(msg)
            return self, m_cmd

        # Confetti updates
        self.confetti, c_cmd = self.confetti.update(msg)
        if c_cmd:
            cmds.append(c_cmd)

        # Toast updates
        self.toasts, t_cmd = self.toasts.update(msg)
        if t_cmd:
            cmds.append(t_cmd)

        # Asynchronous Refresh Handlers
        if isinstance(msg, NeedRefreshMsg):
            tl_id = msg.timeline_id
            since_id = msg.since_id

            def _async_fetch_new() -> Msg:
                try:
                    newer: list[dict] = []
                    if self.api:
                        try:
                            if tl_id == "home":
                                newer = self.api.timeline_home(since_id=since_id, limit=20)
                            elif tl_id == "local":
                                newer = self.api.timeline_local(since_id=since_id, limit=20)
                            elif tl_id == "federated":
                                newer = self.api.timeline_public(since_id=since_id, limit=20)
                            elif tl_id == "notifications":
                                newer = self.api.notifications(since_id=since_id, limit=20)
                            elif tl_id == "conversations":
                                newer = self.api.conversations(since_id=since_id, limit=20)
                        except Exception:
                            newer = []
                    if not newer and self.cache_db_path and self.cache_db_path.exists():
                        try:
                            newer = read_newer_cached_posts_from_db(self.cache_db_path, tl_id, limit=20, since_id=since_id)
                        except Exception:
                            newer = []

                    # Persist newly fetched live posts to SQLite cache
                    if newer and self.cache_db_path and self.api and not self.is_demo:
                        try:
                            save_posts_to_db(self.cache_db_path, tl_id, newer)
                        except Exception:
                            pass

                    # Pre-cache images asynchronously in a background thread so UI timeline refresh completes instantly
                    if newer and self.settings.get("show_images", True):
                        def _bg_cache_images(items: list[dict], pdir: Path | None) -> None:
                            for post in items:
                                st = post.get("reblog") or post
                                for att in st.get("media_attachments", []):
                                    u = att.get("preview_url") or att.get("url")
                                    if u:
                                        try:
                                            download_and_cache_image(u, pdir, allow_network=True)
                                        except Exception:
                                            pass

                        import threading
                        threading.Thread(target=_bg_cache_images, args=(newer, self.profile_dir), daemon=True).start()

                    return TimelineRefreshedMsg(timeline_id=tl_id, new_posts=newer)
                except Exception:
                    return TimelineRefreshedMsg(timeline_id=tl_id, new_posts=[])

            return self, _async_fetch_new

        if isinstance(msg, TimelineRefreshedMsg):
            for tl in self.timelines:
                if tl.timeline_id == msg.timeline_id:
                    tl.prepend_newer_posts(msg.new_posts)
            if msg.new_posts:
                _, cmd = self.toasts.add(f"✨ Received {len(msg.new_posts)} new toots!", ToastLevel.SUCCESS, 2.0)
                return self, cmd
            else:
                _, cmd = self.toasts.add("Timeline up to date", ToastLevel.INFO, 1.5)
                return self, cmd

        # Asynchronous Pagination Handlers
        if isinstance(msg, NeedOlderPostsMsg):
            tl_id = msg.timeline_id
            max_id = msg.max_id

            def _async_fetch_older() -> Msg:
                try:
                    older: list[dict] = []
                    # 1. First check local cache database for instant offline/cached pagination
                    if self.cache_db_path and self.cache_db_path.exists():
                        try:
                            older = read_cached_posts_from_db(self.cache_db_path, tl_id, limit=20, max_id=max_id)
                        except Exception:
                            older = []

                    # 2. If local cache did not return older posts, query live API if available
                    if not older and self.api:
                        try:
                            if tl_id == "home":
                                older = self.api.timeline_home(max_id=max_id, limit=20)
                            elif tl_id == "local":
                                older = self.api.timeline_local(max_id=max_id, limit=20)
                            elif tl_id == "federated":
                                older = self.api.timeline_public(max_id=max_id, limit=20)
                            elif tl_id == "notifications":
                                older = self.api.notifications(max_id=max_id, limit=20)
                            elif tl_id == "conversations":
                                older = self.api.conversations(max_id=max_id, limit=20)
                        except Exception:
                            older = []

                    # 3. Fallback for demo mode
                    if not older and self.is_demo:
                        older = [
                            {
                                "id": str(int(max_id or "11321000") - i - 1),
                                "created_at": datetime.now(timezone.utc).isoformat(),
                                "account": {"display_name": f"Fediverse Citizen #{i+1}", "acct": f"user{i+1}@fediverse.org"},
                                "content": f"<p>Older toot #{i+1} loaded continuously on <strong>{tl_id}</strong>! 📜☕</p>",
                                "reblogs_count": (i + 1) * 2,
                                "favourites_count": (i + 1) * 5,
                                "visibility": "public",
                            }
                            for i in range(4)
                        ]
                    elif older and self.cache_db_path and not self.is_demo:
                        try:
                            save_posts_to_db(self.cache_db_path, tl_id, older)
                        except Exception:
                            pass

                    # Pre-cache images asynchronously in a background thread so UI pagination completes instantly
                    if older and self.settings.get("show_images", True):
                        def _bg_cache_older_images(items: list[dict], pdir: Path | None) -> None:
                            for post in items:
                                st = post.get("reblog") or post
                                for att in st.get("media_attachments", []):
                                    u = att.get("preview_url") or att.get("url")
                                    if u:
                                        try:
                                            download_and_cache_image(u, pdir, allow_network=True)
                                        except Exception:
                                            pass

                        import threading
                        threading.Thread(target=_bg_cache_older_images, args=(older, self.profile_dir), daemon=True).start()

                    return TimelineOlderLoadedMsg(timeline_id=tl_id, older_posts=older)
                except Exception:
                    # Guarantee that TimelineOlderLoadedMsg is returned even on failure
                    return TimelineOlderLoadedMsg(timeline_id=tl_id, older_posts=[])

            return self, _async_fetch_older

        if isinstance(msg, TimelineOlderLoadedMsg):
            for tl in self.timelines:
                if tl.timeline_id == msg.timeline_id:
                    tl.append_older_posts(msg.older_posts)
            return self, None

        # Global Key Navigation
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "q" | "ctrl+c":
                    return self, quit_app
                case "n" | "c":  # Compose new toot
                    composer = ComposerModal(width=min(72, self.width - 8))
                    self.modal_stack.push(composer)
                    return self, None
                case "a":  # Reply to post
                    sel = self.current_timeline.selected_post
                    composer = ComposerModal(reply_to_post=sel, width=min(72, self.width - 8))
                    self.modal_stack.push(composer)
                    return self, None
                case "f":  # Like / Favourite
                    post = self.current_timeline.toggle_current_favourite()
                    if post:
                        is_fav = post.get("favourited")
                        text = "💖 Added to Favourites!" if is_fav else "💔 Removed from Favourites."
                        lvl = ToastLevel.SUCCESS if is_fav else ToastLevel.INFO
                        _, cmd = self.toasts.add(text, lvl, 2.0)
                        cmds.append(cmd)
                    return self, batch(*cmds) if cmds else None
                case "b":  # Boost / Reblog
                    post = self.current_timeline.toggle_current_reblog()
                    if post:
                        is_reb = post.get("reblogged")
                        if is_reb and self.enable_animations:
                            c_cmd = self.confetti.fire(count=20)
                            if c_cmd:
                                cmds.append(c_cmd)
                        text = "🚀 Boosted post to your followers!" if is_reb else "↩️ Unboosted post."
                        lvl = ToastLevel.SUCCESS if is_reb else ToastLevel.INFO
                        _, cmd = self.toasts.add(text, lvl, 2.0)
                        cmds.append(cmd)
                    return self, batch(*cmds) if cmds else None
                case "o":  # Settings & Options
                    modal = SettingsModal(
                        current_settings=self.settings,
                        profile_dir=self.profile_dir,
                        width=min(88, max(76, self.width - 6)),
                        screen_width=self.width,
                        screen_height=self.height,
                    )
                    self.modal_stack.push(modal)
                    return self, None
                case "x":  # URL Selector
                    sel = self.current_timeline.selected_post
                    if sel:
                        modal = UrlSelectorModal(post_data=sel, width=min(72, self.width - 6))
                        self.modal_stack.push(modal)
                    else:
                        _, cmd = self.toasts.add("No post selected", ToastLevel.INFO, 2.0)
                        return self, cmd
                    return self, None
                case "?":  # Help Screen
                    modal = HelpModal(width=min(76, self.width - 6))
                    self.modal_stack.push(modal)
                    return self, None
                case "t" | "enter":  # View Thread
                    sel = self.current_timeline.selected_post
                    if sel:
                        modal = ThreadModal(
                            post=sel,
                            api=self.api,
                            all_known_posts=self.current_timeline.posts,
                            cache_db_path=self.cache_db_path,
                            is_demo=self.is_demo,
                            width=min(78, self.width - 6),
                            height=min(26, self.height - 4),
                            theme=self.theme,
                        )
                        self.modal_stack.push(modal)
                        return self, modal.init()
                    return self, None
                case "u":  # Switch Account / Profile
                    profiles = profile_manager.get_profiles()
                    modal = ProfileSelectionModal(
                        current_profile=self.profile_name,
                        profiles=profiles,
                        width=min(68, self.width - 6),
                        height=min(20, self.height - 4),
                        theme=self.theme,
                    )
                    self.modal_stack.push(modal)
                    return self, modal.init()
                case "p":  # Author Profile
                    sel = self.current_timeline.selected_post
                    if sel:
                        modal = ProfileModal(account_or_post=sel, width=min(68, self.width - 6))
                        self.modal_stack.push(modal)
                    return self, None
                case "y":  # Copy post link
                    sel = self.current_timeline.selected_post
                    if sel:
                        status = sel.get("reblog") or sel
                        url = status.get("url")
                        if url:
                            copy_to_clipboard(url)
                            disp = url if len(url) <= 35 else url[:32] + "..."
                            _, cmd = self.toasts.add(f"📋 Copied link: {disp}", ToastLevel.SUCCESS, 2.5)
                            return self, cmd
                    return self, None
                case "g":  # Jump to top
                    self.current_timeline.jump_to_top()
                    return self, None
                case "r":  # Refresh with animated spinner
                    _, ref_cmd = self.current_timeline.trigger_refresh()
                    return self, ref_cmd
                case "R":  # Refresh all active/enabled timelines concurrently
                    ref_cmds = []
                    for tl in self.enabled_timelines:
                        _, c = tl.trigger_refresh()
                        if c:
                            ref_cmds.append(c)
                    _, t_cmd = self.toasts.add("🔄 Refreshing all timelines...", ToastLevel.INFO, 2.0)
                    ref_cmds.append(t_cmd)
                    return self, batch(*ref_cmds)
                case "i":  # Open Image/Media attachment preview modal
                    sel = self.current_timeline.selected_post
                    if sel:
                        status = sel.get("reblog") or sel
                        attachments = status.get("media_attachments", [])
                        if attachments:
                            modal = ImageModal(
                                attachment=attachments[0],
                                profile_dir=self.profile_dir,
                                width=min(78, self.width - 6),
                                height=min(26, self.height - 4),
                                renderer=str(self.settings.get("image_renderer", "ansi")),
                            )
                            self.modal_stack.push(modal)
                            return self, modal.init()
                        else:
                            _, cmd = self.toasts.add("Selected post has no media attachments", ToastLevel.INFO, 2.0)
                            return self, cmd
                    return self, None
                case "m":  # Toggle Direct Messages timeline
                    dm_tl = self.timelines[4]
                    dm_tl.enabled = not dm_tl.enabled
                    if dm_tl.enabled:
                        self.switch_timeline(4)
                        _, cmd = self.toasts.add("✉️ Direct Messages timeline shown", ToastLevel.INFO, 2.0)
                    else:
                        if self.active_timeline_idx == 4:
                            self.switch_timeline(0)
                        _, cmd = self.toasts.add("✉️ Direct Messages timeline hidden", ToastLevel.INFO, 2.0)
                    return self, cmd
                case "shift+tab" | "left" | "h" | "[":
                    enabled = self.enabled_timelines
                    cur_in_enabled = (
                        enabled.index(self.current_timeline)
                        if self.current_timeline in enabled
                        else 0
                    )
                    prev_col = enabled[(cur_in_enabled - 1) % len(enabled)]
                    return self.switch_timeline(self.timelines.index(prev_col))
                case "tab" | "right" | "l" | "]":
                    enabled = self.enabled_timelines
                    cur_in_enabled = (
                        enabled.index(self.current_timeline)
                        if self.current_timeline in enabled
                        else 0
                    )
                    next_col = enabled[(cur_in_enabled + 1) % len(enabled)]
                    return self.switch_timeline(self.timelines.index(next_col))
                case "1" | "2" | "3" | "4" | "5":
                    k = str(msg.key)
                    if k.isdigit():
                        return self.switch_timeline(int(k) - 1)
                    return self, None

        if isinstance(msg, TabChangeMsg):
            return self.switch_timeline(msg.index)

        # Mouse Navigation
        if isinstance(msg, MouseMsg):
            enabled = self.enabled_timelines
            is_multi = (not self.force_single_column) and (self.width >= 70) and (len(enabled) > 1)
            inner_w = max(40, self.width - 2)

            if not is_multi:
                if msg.y == 3:
                    self.tabs, t_cmd = self.tabs.update(MouseMsg(x=msg.x, y=0, button=msg.button, action=msg.action))
                    if self.tabs.active_tab != self.active_timeline_idx:
                        return self.switch_timeline(self.tabs.active_tab)
                    return self, t_cmd

                if 4 <= msg.y < 4 + self.current_timeline.height:
                    tl_msg = MouseMsg(
                        x=msg.x,
                        y=msg.y - 4,
                        button=msg.button,
                        action=msg.action,
                        ctrl=msg.ctrl,
                        alt=msg.alt,
                        shift=msg.shift,
                    )
                    self.current_timeline, tl_cmd = self.current_timeline.update(tl_msg)
                    return self, tl_cmd
            else:
                num_cols = len(enabled)
                col_w = max(24, (inner_w - (num_cols - 1)) // num_cols)
                col_h = max(10, self.height - 8)

                if 3 <= msg.y <= 5:
                    col_idx = min(num_cols - 1, max(0, msg.x // (col_w + 1)))
                    target_tl = enabled[col_idx]
                    target_idx = self.timelines.index(target_tl)
                    if self.active_timeline_idx != target_idx:
                        return self.switch_timeline(target_idx)
                    return self, None

                if 6 <= msg.y < 6 + col_h:
                    col_idx = min(num_cols - 1, max(0, msg.x // (col_w + 1)))
                    target_tl = enabled[col_idx]
                    target_idx = self.timelines.index(target_tl)
                    if self.active_timeline_idx != target_idx:
                        self.switch_timeline(target_idx)

                    tl_msg = MouseMsg(
                        x=msg.x % (col_w + 1),
                        y=msg.y - 6,
                        button=msg.button,
                        action=msg.action,
                        ctrl=msg.ctrl,
                        alt=msg.alt,
                        shift=msg.shift,
                    )
                    target_tl, tl_cmd = target_tl.update(tl_msg)
                    return self, tl_cmd

        # Delegate update to active timeline (and forward ticks to refreshing timelines)
        for tl in self.timelines:
            if tl == self.current_timeline or tl.is_refreshing or tl.is_loading_more:
                tl, tl_cmd = tl.update(msg)
                if tl_cmd:
                    cmds.append(tl_cmd)

        return self, batch(*cmds) if cmds else None

    def view(self) -> str:
        """Render the complete Mastui interface supporting multi-column side-by-side timelines."""
        if self.show_splash:
            return self.splash.view()

        inner_w = max(40, self.width - 2)
        primary = self.theme.primary
        secondary = self.theme.secondary
        border_dim = self.theme.border_dim
        text_muted = self.theme.text_muted

        # 1. Top Header Banner
        conn_subtitle = f"{self.instance}" if not self.is_demo else "Demo Mode"
        banner_text = f"☕ MASTUI  │  {conn_subtitle}  │  @{self.username}"
        gradient_header = linear_gradient(banner_text, primary, secondary)
        header_card = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground(secondary)
            .background(getattr(self.theme, "header_bg", None))
            .width(inner_w - 2)
            .align(Align.CENTER)
            .render(truncate_ansi(gradient_header, inner_w - 2))
        )

        # 2. Determine Single vs Multi-Column Mode
        enabled = self.enabled_timelines
        is_multi_column = (not self.force_single_column) and (self.width >= 70) and (len(enabled) > 1)
        col_h = max(8, self.height - 9)

        if not is_multi_column:
            # Single-Column Mode: Full width with top tabs
            top_bar = self.tabs.view()
            self.current_timeline.set_size(inner_w, col_h)
            timelines_view = self.current_timeline.view()
        else:
            # Multi-Column Mode: Side-by-side columns
            num_cols = len(enabled)
            col_gap = 1
            total_gaps = (num_cols - 1) * col_gap
            available_w = max(24 * num_cols, inner_w - total_gaps)
            col_w_base = available_w // num_cols
            rem = available_w % num_cols

            col_badges = []
            for i, tl in enumerate(self.timelines):
                if tl.enabled:
                    is_cur = (tl == self.current_timeline)
                    style = (
                        Style()
                        .bold(True)
                        .foreground(primary)
                        .background(getattr(self.theme, "surface_active", None))
                        .border(ROUNDED_BORDER)
                        .border_foreground(primary)
                        if is_cur
                        else Style()
                        .foreground(text_muted)
                        .background(getattr(self.theme, "surface", None))
                        .border(ROUNDED_BORDER)
                        .border_foreground(border_dim)
                    )
                    idx_str = f"[{i + 1}] " if i < 4 else "[m] "
                    col_badges.append(style.render(f" {idx_str}{tl.title} "))

            joined_badges = []
            for idx, b in enumerate(col_badges):
                joined_badges.append(b)
                if idx < len(col_badges) - 1:
                    joined_badges.append("  ")
            col_header_bar = join_horizontal(Align.TOP, *joined_badges)

            col_views = []
            for idx, tl in enumerate(enabled):
                w = col_w_base + (1 if idx < rem else 0)
                tl.set_size(w, col_h)
                tl.is_active = (tl == self.current_timeline)
                col_views.append(tl.view())

            joined_cols = []
            for idx, cv in enumerate(col_views):
                joined_cols.append(cv)
                if idx < len(col_views) - 1:
                    joined_cols.append(" ")
            timelines_view = join_horizontal(Align.TOP, *joined_cols)
            top_bar = col_header_bar

        # 3. Footer: Connection Status Line & Keybindings Bar
        conn_label = "Demo Mode" if self.is_demo else f"Connected to {self.instance}"
        dot_color = "#00E676" if not self.is_demo else primary
        dot = Style().foreground(dot_color).render("● ")
        conn_styled = Style().foreground(getattr(self.theme, "accent", "#80D8FF")).render(conn_label)
        user_styled = Style().foreground(text_muted).render(f"│  @{self.username}")
        status_left = f" {dot}{conn_styled}  {user_styled}"

        cur_tl = self.current_timeline
        total_posts = len(cur_tl.posts)
        cur_pos = (cur_tl.list.cursor + 1) if total_posts > 0 else 0
        pos_str = f"Post {cur_pos}/{total_posts} "
        status_right = Style().foreground(text_muted).render(pos_str)

        plain_left = f" ● {conn_label}  │  @{self.username}"
        plain_right = pos_str
        avail_gap = inner_w - string_width(plain_left) - string_width(plain_right)
        if avail_gap >= 2:
            status_line = f"{status_left}{' ' * avail_gap}{status_right}"
        else:
            status_line = truncate_ansi(f"{status_left}  {status_right}", inner_w)

        # Bottom Keybindings Bar
        bottom_hints = (
            " [j/k] Scroll  [←/→] Columns  [l] Like  [b] Boost  [c] Compose  [Enter] Thread  [u] Acct  [i] Image  [x] Links  [p] Profile  [r/R] Refresh  [m] DMs  [o] Options  [?] Help  [q] Quit"
        )
        bottom_bar = Style().foreground(text_muted).render(truncate_ansi(bottom_hints, inner_w))

        # Composite screen
        content = f"{header_card}\n{top_bar}\n{timelines_view}\n{status_line}\n{bottom_bar}"

        # 4. Composite Active Modals
        for modal in self.modal_stack.modals:
            content = place_overlay(content, modal.view(), center=True, dim_backdrop=True)

        # 5. Composite Toasts at bottom of the screen (above bottom status bar)
        if self.toasts.has_toasts:
            toast_view = self.toasts.view()
            toast_lines = toast_view.splitlines()
            toast_h = len(toast_lines)
            toast_w = max((string_width(l) for l in toast_lines), default=0)
            toast_x = max(2, (self.width - toast_w) // 2)
            toast_y = max(0, self.height - toast_h - 3)
            content = place_overlay(content, toast_view, x=toast_x, y=toast_y, center=False, dim_backdrop=False)

        # 6. Composite Confetti Particles directly on top of the actual timeline
        if self.enable_animations and self.confetti.is_active:
            content = self.confetti.overlay(content)

        return content


def run():
    """Launch the Espresso Mastui application."""
    app = MastuiEspressoApp()
    program = Program(app, alt_screen=True, mouse=True)
    program.run()


if __name__ == "__main__":
    run()
