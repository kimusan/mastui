"""Interactive Settings and Preferences modal with tabbed sections for Mastui on Espresso."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from espresso.beans.modal_stack import ModalCloseMsg
from espresso.beans.select import Select, SelectChangeMsg
from espresso.beans.switch import Switch, SwitchToggledMsg
from espresso.beans.tabs import TabChangeMsg, TabStyle, Tabs
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.layout import join_horizontal
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi
from mastui.espresso_theme import get_theme, load_all_themes

SETTINGS_FILE = Path.home() / ".config" / "mastui" / "espresso_settings.json"


def parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse key-value pairs from .env."""
    vals: dict[str, str] = {}
    if not env_path.exists():
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


def load_settings(profile_dir: Path | None = None) -> dict[str, Any]:
    """Load settings from profile .env or JSON settings file."""
    defaults: dict[str, Any] = {
        # Timelines
        "home_timeline_enabled": True,
        "local_timeline_enabled": True,
        "notifications_timeline_enabled": True,
        "federated_timeline_enabled": False,
        "direct_timeline_enabled": True,
        "force_single_column": False,
        # Auto-Refresh
        "auto_refresh": True,
        "home_auto_refresh": True,
        "local_auto_refresh": False,
        "notifications_auto_refresh": True,
        "federated_auto_refresh": False,
        # Media & Cache
        "show_images": True,
        "image_renderer": "ansi",
        "auto_prune_cache": False,
        # Notifications
        "notifications_popups_mentions": True,
        "notifications_popups_follows": True,
        "notifications_popups_reblogs": False,
        "notifications_popups_favourites": False,
        # Appearance & Themes
        "theme": "espresso",
        "enable_animations": True,
        "show_splash": True,
        # Posting
        "default_visibility": "public",
    }

    # 1. Read profile .env if available
    if profile_dir:
        env_file = profile_dir / ".env"
        if env_file.exists():
            env_vals = parse_env_file(env_file)
            if "HOME_TIMELINE_ENABLED" in env_vals:
                defaults["home_timeline_enabled"] = (env_vals["HOME_TIMELINE_ENABLED"] == "on")
            if "LOCAL_TIMELINE_ENABLED" in env_vals:
                defaults["local_timeline_enabled"] = (env_vals["LOCAL_TIMELINE_ENABLED"] == "on")
            if "NOTIFICATIONS_TIMELINE_ENABLED" in env_vals:
                defaults["notifications_timeline_enabled"] = (env_vals["NOTIFICATIONS_TIMELINE_ENABLED"] == "on")
            if "FEDERATED_TIMELINE_ENABLED" in env_vals:
                defaults["federated_timeline_enabled"] = (env_vals["FEDERATED_TIMELINE_ENABLED"] == "on")
            if "DIRECT_TIMELINE_ENABLED" in env_vals:
                defaults["direct_timeline_enabled"] = (env_vals["DIRECT_TIMELINE_ENABLED"] == "on")
            if "FORCE_SINGLE_COLUMN" in env_vals:
                defaults["force_single_column"] = (env_vals["FORCE_SINGLE_COLUMN"] == "on")
            if "HOME_AUTO_REFRESH" in env_vals:
                defaults["home_auto_refresh"] = (env_vals["HOME_AUTO_REFRESH"] == "on")
            if "LOCAL_AUTO_REFRESH" in env_vals:
                defaults["local_auto_refresh"] = (env_vals["LOCAL_AUTO_REFRESH"] == "on")
            if "NOTIFICATIONS_AUTO_REFRESH" in env_vals:
                defaults["notifications_auto_refresh"] = (env_vals["NOTIFICATIONS_AUTO_REFRESH"] == "on")
            if "FEDERATED_AUTO_REFRESH" in env_vals:
                defaults["federated_auto_refresh"] = (env_vals["FEDERATED_AUTO_REFRESH"] == "on")
            if "IMAGE_SUPPORT" in env_vals:
                defaults["show_images"] = (env_vals["IMAGE_SUPPORT"] == "on")
            if "IMAGE_RENDERER" in env_vals:
                defaults["image_renderer"] = env_vals["IMAGE_RENDERER"]
            if "AUTO_PRUNE_CACHE" in env_vals:
                defaults["auto_prune_cache"] = (env_vals["AUTO_PRUNE_CACHE"] == "on")
            if "THEME" in env_vals:
                defaults["theme"] = env_vals["THEME"]

    # 2. Overlay espresso_settings.json if present
    candidates = []
    if profile_dir:
        candidates.append(profile_dir / "espresso_settings.json")
    candidates.append(SETTINGS_FILE)

    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                defaults.update(data)
                return defaults
            except Exception:
                pass

    return defaults


def save_settings(settings: dict[str, Any], profile_dir: Path | None = None) -> bool:
    """Save settings to target profile or global config."""
    target_path = (profile_dir / "espresso_settings.json") if profile_dir else SETTINGS_FILE
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

        # Also update .env if profile_dir provided
        if profile_dir:
            env_file = profile_dir / ".env"
            if env_file.exists():
                lines = env_file.read_text(encoding="utf-8").splitlines()
                key_map = {
                    "HOME_TIMELINE_ENABLED": "on" if settings.get("home_timeline_enabled") else "off",
                    "LOCAL_TIMELINE_ENABLED": "on" if settings.get("local_timeline_enabled") else "off",
                    "NOTIFICATIONS_TIMELINE_ENABLED": "on" if settings.get("notifications_timeline_enabled") else "off",
                    "FEDERATED_TIMELINE_ENABLED": "on" if settings.get("federated_timeline_enabled") else "off",
                    "DIRECT_TIMELINE_ENABLED": "on" if settings.get("direct_timeline_enabled") else "off",
                    "FORCE_SINGLE_COLUMN": "on" if settings.get("force_single_column") else "off",
                    "THEME": str(settings.get("theme", "espresso")),
                    "IMAGE_SUPPORT": "on" if settings.get("show_images") else "off",
                    "IMAGE_RENDERER": str(settings.get("image_renderer", "ansi")),
                    "AUTO_PRUNE_CACHE": "on" if settings.get("auto_prune_cache") else "off",
                }
                new_lines = []
                seen_keys = set()
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and "=" in stripped:
                        k, _ = stripped.split("=", 1)
                        k = k.strip()
                        if k in key_map:
                            new_lines.append(f"{k}={key_map[k]}")
                            seen_keys.add(k)
                            continue
                    new_lines.append(line)
                for k, v in key_map.items():
                    if k not in seen_keys:
                        new_lines.append(f"{k}={v}")
                env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

        return True
    except Exception:
        return False


@dataclass(frozen=True)
class SettingsSaveMsg(Msg):
    """Message emitted when settings are saved."""

    settings: dict[str, Any]


class SettingsModal(Model):
    """Tabbed modal dialog for configuring timelines and app preferences."""

    TAB_TITLES = ["1:Timelines", "2:Refresh", "3:Media", "4:Alerts", "5:Themes", "6:Posting"]

    def __init__(
        self,
        current_settings: dict[str, Any] | None = None,
        profile_dir: Path | None = None,
        width: int = 82,
        screen_width: int = 100,
        screen_height: int = 30,
    ) -> None:
        self.profile_dir = profile_dir
        self.width = max(60, min(width, screen_width - 4))
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.settings = dict(current_settings or load_settings(profile_dir))

        # Active tab: 0 (Timelines), 1 (Refresh), 2 (Media), 3 (Alerts), 4 (Themes), 5 (Posting)
        self.active_tab = 0
        if self.width < 78:
            self.tab_titles = ["1:Feeds", "2:Sync", "3:Media", "4:Alerts", "5:Themes", "6:Post"]
        else:
            self.tab_titles = list(self.TAB_TITLES)

        self.tabs = Tabs(
            titles=self.tab_titles,
            active_tab=0,
            tab_style=TabStyle.PILL,
            show_numbers=False,
        )

        # Tab 0: Timelines
        self.sw_home = Switch(
            value=bool(self.settings.get("home_timeline_enabled", True)),
            label="Home Timeline",
            id="sw_home",
            active_color="#00E5FF",
        )
        self.sw_local = Switch(
            value=bool(self.settings.get("local_timeline_enabled", True)),
            label="Local Timeline",
            id="sw_local",
            active_color="#00E5FF",
        )
        self.sw_notif = Switch(
            value=bool(self.settings.get("notifications_timeline_enabled", True)),
            label="Notifications Timeline",
            id="sw_notif",
            active_color="#00E5FF",
        )
        self.sw_fed = Switch(
            value=bool(self.settings.get("federated_timeline_enabled", False)),
            label="Federated Timeline",
            id="sw_fed",
            active_color="#00E5FF",
        )
        self.sw_dm = Switch(
            value=bool(self.settings.get("direct_timeline_enabled", True)),
            label="Direct Messages Timeline",
            id="sw_dm",
            active_color="#00E5FF",
        )
        self.sw_single_col = Switch(
            value=bool(self.settings.get("force_single_column", False)),
            label="Force Single-Column Mode (Tabs instead of multi-column)",
            id="sw_single_col",
            active_color="#FFB300",
        )

        # Tab 1: Auto-Refresh
        self.sw_refresh_home = Switch(
            value=bool(self.settings.get("home_auto_refresh", True)),
            label="Auto-refresh Home timeline",
            id="sw_refresh_home",
            active_color="#00E676",
        )
        self.sw_refresh_local = Switch(
            value=bool(self.settings.get("local_auto_refresh", False)),
            label="Auto-refresh Local timeline",
            id="sw_refresh_local",
            active_color="#00E676",
        )
        self.sw_refresh_notif = Switch(
            value=bool(self.settings.get("notifications_auto_refresh", True)),
            label="Auto-refresh Notifications timeline",
            id="sw_refresh_notif",
            active_color="#00E676",
        )
        self.sw_refresh_fed = Switch(
            value=bool(self.settings.get("federated_auto_refresh", False)),
            label="Auto-refresh Federated timeline",
            id="sw_refresh_fed",
            active_color="#00E676",
        )
        self.sw_refresh = Switch(
            value=bool(self.settings.get("auto_refresh", True)),
            label="Master Automatic Background Refresh",
            id="sw_refresh",
            active_color="#00E676",
        )

        # Tab 2: Media & Cache
        self.sw_images = Switch(
            value=bool(self.settings.get("show_images", True)),
            label="Show inline images and media attachments",
            id="sw_images",
            active_color="#00E5FF",
        )
        renderer_opts = [
            ("ansi", "TrueColor ANSI Halfblocks (Fast & Universal)"),
            ("auto", "Auto-detect terminal capabilities"),
            ("external", "Open in external image viewer (xdg-open)"),
        ]
        self.sel_img_renderer = Select(
            options=renderer_opts,
            value=str(self.settings.get("image_renderer", "ansi")),
            id="sel_img_renderer",
            prompt="Select image renderer...",
            width=self.width - 12,
            focused=False,
        )
        self.sw_prune_cache = Switch(
            value=bool(self.settings.get("auto_prune_cache", False)),
            label="Auto-prune cache (clean files older than 30 days)",
            id="sw_prune_cache",
            active_color="#FFB300",
        )

        # Tab 3: Notifications
        self.sw_pop_mentions = Switch(
            value=bool(self.settings.get("notifications_popups_mentions", True)),
            label="Toast pop-up on new mentions",
            id="sw_pop_mentions",
            active_color="#00E5FF",
        )
        self.sw_pop_follows = Switch(
            value=bool(self.settings.get("notifications_popups_follows", True)),
            label="Toast pop-up on new followers",
            id="sw_pop_follows",
            active_color="#00E5FF",
        )
        self.sw_pop_reblogs = Switch(
            value=bool(self.settings.get("notifications_popups_reblogs", False)),
            label="Toast pop-up on new reblogs / boosts",
            id="sw_pop_reblogs",
            active_color="#00E5FF",
        )
        self.sw_pop_favs = Switch(
            value=bool(self.settings.get("notifications_popups_favourites", False)),
            label="Toast pop-up on new favourites / likes",
            id="sw_pop_favs",
            active_color="#00E5FF",
        )

        # Tab 4: Appearance & Themes
        all_themes = load_all_themes()
        theme_opts = [(t.name, f"{t.label}") for t in all_themes.values()]
        cur_theme = str(self.settings.get("theme", "espresso"))
        if cur_theme not in all_themes:
            cur_theme = "espresso"
        self.sel_theme = Select(
            options=theme_opts,
            value=cur_theme,
            id="sel_theme",
            prompt="Select theme...",
            width=self.width - 12,
            focused=False,
        )
        self.sw_anim = Switch(
            value=bool(self.settings.get("enable_animations", True)),
            label="Celebratory Burst Animations (Confetti on boost/post)",
            id="sw_anim",
            active_color="#00E5FF",
        )
        self.sw_splash = Switch(
            value=bool(self.settings.get("show_splash", True)),
            label="Show animated splash screen on startup",
            id="sw_splash",
            active_color="#00E5FF",
        )

        # Tab 5: Posting Preferences
        vis_options = [
            ("public", "Public (To local & federated)"),
            ("unlisted", "Unlisted (Visible to all, no public feed)"),
            ("private", "Followers-only (Only your followers)"),
            ("direct", "Direct (Mentioned users only)"),
        ]
        self.vis_select = Select(
            options=vis_options,
            value=str(self.settings.get("default_visibility", "public")),
            id="vis_select",
            prompt="Select visibility...",
            width=self.width - 12,
            focused=False,
        )

        # Focus index within current tab:
        # 0..N-1: controls in active tab
        # -2: Save button, -1: Cancel button
        self.tab_focus_idx = 0
        self._sync_focus()

    @property
    def current_tab_controls(self) -> list[Any]:
        """Return list of interactive controls on the active tab."""
        if self.active_tab == 0:
            return [self.sw_home, self.sw_local, self.sw_notif, self.sw_fed, self.sw_dm, self.sw_single_col]
        elif self.active_tab == 1:
            return [self.sw_refresh_home, self.sw_refresh_local, self.sw_refresh_notif, self.sw_refresh_fed, self.sw_refresh]
        elif self.active_tab == 2:
            return [self.sw_images, self.sel_img_renderer, self.sw_prune_cache]
        elif self.active_tab == 3:
            return [self.sw_pop_mentions, self.sw_pop_follows, self.sw_pop_reblogs, self.sw_pop_favs]
        elif self.active_tab == 4:
            return [self.sel_theme, self.sw_anim, self.sw_splash]
        elif self.active_tab == 5:
            return [self.vis_select]
        return []

    # Backward compatibility properties
    @property
    def focus_idx(self) -> int:
        """Compatibility focus index for tests."""
        if self.tab_focus_idx < 0:
            return 9 if self.tab_focus_idx == -2 else 10
        # Return tab-based offset
        return self.tab_focus_idx

    @focus_idx.setter
    def focus_idx(self, val: int) -> None:
        if val == 9:
            self.tab_focus_idx = -2
        elif val == 10:
            self.tab_focus_idx = -1
        else:
            self.tab_focus_idx = max(0, val)
        self._sync_focus()

    def set_tab(self, tab_idx: int) -> None:
        """Switch active configuration tab."""
        self.active_tab = max(0, min(tab_idx, len(self.tab_titles) - 1))
        self.tabs.set_active(self.active_tab)
        self.tabs.active_tab = self.active_tab
        self.tab_focus_idx = 0
        self._sync_focus()

    def _sync_focus(self) -> None:
        controls = self.current_tab_controls
        for idx, ctrl in enumerate(controls):
            is_focused = (self.tab_focus_idx == idx)
            if hasattr(ctrl, "focused"):
                ctrl.focused = is_focused

    def init(self) -> Cmd | None:
        return None

    def _submit(self) -> tuple[SettingsModal, Cmd | None]:
        new_settings = {
            # Timelines
            "home_timeline_enabled": self.sw_home.value,
            "local_timeline_enabled": self.sw_local.value,
            "notifications_timeline_enabled": self.sw_notif.value,
            "federated_timeline_enabled": self.sw_fed.value,
            "direct_timeline_enabled": self.sw_dm.value,
            "force_single_column": self.sw_single_col.value,
            # Refresh
            "auto_refresh": self.sw_refresh.value,
            "home_auto_refresh": self.sw_refresh_home.value,
            "local_auto_refresh": self.sw_refresh_local.value,
            "notifications_auto_refresh": self.sw_refresh_notif.value,
            "federated_auto_refresh": self.sw_refresh_fed.value,
            # Media & Cache
            "show_images": self.sw_images.value,
            "image_renderer": self.sel_img_renderer.value,
            "auto_prune_cache": self.sw_prune_cache.value,
            # Notifications
            "notifications_popups_mentions": self.sw_pop_mentions.value,
            "notifications_popups_follows": self.sw_pop_follows.value,
            "notifications_popups_reblogs": self.sw_pop_reblogs.value,
            "notifications_popups_favourites": self.sw_pop_favs.value,
            # Appearance & Themes
            "theme": self.sel_theme.value,
            "enable_animations": self.sw_anim.value,
            "show_splash": self.sw_splash.value,
            # Posting
            "default_visibility": self.vis_select.value,
        }

        save_settings(new_settings, self.profile_dir)

        def _emit_saved() -> Msg:
            return SettingsSaveMsg(settings=new_settings)

        return self, _emit_saved

    def update(self, msg: Msg) -> tuple[SettingsModal, Cmd | None]:
        controls = self.current_tab_controls
        num_ctrls = len(controls)

        active_ctrl = controls[self.tab_focus_idx] if 0 <= self.tab_focus_idx < num_ctrls else None
        is_select_open = isinstance(active_ctrl, Select) and active_ctrl.is_open

        # If a dropdown Select is open, intercept navigation and selection
        if is_select_open and isinstance(active_ctrl, Select):
            if isinstance(msg, KeyMsg):
                match msg.key:
                    case "esc" | "q":
                        active_ctrl.close()
                        return self, None
                    case "up" | "k":
                        active_ctrl.cursor = max(0, active_ctrl.cursor - 1)
                        active_ctrl._adjust_scroll()
                        return self, None
                    case "down" | "j":
                        active_ctrl.cursor = min(len(active_ctrl.options) - 1, active_ctrl.cursor + 1)
                        active_ctrl._adjust_scroll()
                        return self, None
                    case "enter" | " ":
                        return self, active_ctrl.choose(active_ctrl.cursor)[1]

        # If a Select is focused (closed), allow quick + / - cycling of its values without opening
        if isinstance(active_ctrl, Select) and not is_select_open:
            if isinstance(msg, KeyMsg):
                if msg.key in ("+", "="):
                    cur_idx = active_ctrl._find_index_by_value(active_ctrl.value)
                    next_idx = (cur_idx + 1) % len(active_ctrl.options)
                    return self, active_ctrl.choose(next_idx)[1]
                elif msg.key in ("-", "_"):
                    cur_idx = active_ctrl._find_index_by_value(active_ctrl.value)
                    prev_idx = (cur_idx - 1) % len(active_ctrl.options)
                    return self, active_ctrl.choose(prev_idx)[1]
                elif msg.key in ("enter", " "):
                    active_ctrl.open()
                    return self, None

        if isinstance(msg, KeyMsg):
            match msg.key:
                # Direct Tab Jump: 1 to 6 (works on all international keyboard layouts without AltGr)
                case "1" | "2" | "3" | "4" | "5" | "6":
                    target_tab = int(str(msg.key)) - 1
                    if target_tab < len(self.tab_titles):
                        self.set_tab(target_tab)
                        return self, None

                # Tab cycling: Left / Right arrows, h / l, brackets [, ], comma / dot
                case "left" | "h" | "ctrl+left" | "[" | "<" | ",":
                    self.set_tab((self.active_tab - 1) % len(self.tab_titles))
                    return self, None
                case "right" | "l" | "ctrl+right" | "]" | ">" | ".":
                    self.set_tab((self.active_tab + 1) % len(self.tab_titles))
                    return self, None

                case "esc" | "q":
                    def _close() -> Msg:
                        return ModalCloseMsg()
                    return self, _close

                case "tab" | "down":
                    # Focus progression: 0..N-1 -> Save (-2) -> Cancel (-1) -> 0
                    if 0 <= self.tab_focus_idx < num_ctrls - 1:
                        self.tab_focus_idx += 1
                    elif self.tab_focus_idx == num_ctrls - 1:
                        self.tab_focus_idx = -2  # Save
                    elif self.tab_focus_idx == -2:
                        self.tab_focus_idx = -1  # Cancel
                    else:
                        self.tab_focus_idx = 0
                    self._sync_focus()
                    return self, None

                case "shift+tab" | "up":
                    if self.tab_focus_idx == -1:
                        self.tab_focus_idx = -2
                    elif self.tab_focus_idx == -2:
                        self.tab_focus_idx = num_ctrls - 1
                    elif self.tab_focus_idx > 0:
                        self.tab_focus_idx -= 1
                    else:
                        self.tab_focus_idx = -1
                    self._sync_focus()
                    return self, None

                case "enter" | " ":
                    if 0 <= self.tab_focus_idx < num_ctrls:
                        target = controls[self.tab_focus_idx]
                        if isinstance(target, Switch):
                            return self, target.toggle()[1]
                        elif isinstance(target, Select):
                            updated_sel, cmd = target.update(msg)
                            self._sync_focus()
                            return self, cmd
                    elif self.tab_focus_idx == -2:
                        return self._submit()
                    elif self.tab_focus_idx == -1:
                        def _cancel() -> Msg:
                            return ModalCloseMsg()
                        return self, _cancel

        # Mouse Hit Testing
        if isinstance(msg, MouseMsg):
            overlay_lines = self.view().splitlines()
            overlay_h = len(overlay_lines)
            overlay_w = max((string_width(l) for l in overlay_lines), default=self.width)

            pos_y = max(0, (self.screen_height - overlay_h) // 2)
            pos_x = max(0, (self.screen_width - overlay_w) // 2)

            rel_y = msg.y - pos_y
            rel_x = msg.x - pos_x

            # Mouse wheel cycles tabs
            if msg.button == MouseButton.WHEEL_UP:
                self.set_tab((self.active_tab - 1) % len(self.tab_titles))
                return self, None
            elif msg.button == MouseButton.WHEEL_DOWN:
                self.set_tab((self.active_tab + 1) % len(self.tab_titles))
                return self, None

            if msg.button == MouseButton.LEFT and msg.action == MouseAction.PRESS:
                if 0 <= rel_x <= overlay_w:
                    # Row 2: Tabs bar
                    if rel_y == 2:
                        cur_x = 2
                        for idx, title in enumerate(self.tab_titles):
                            pill_w = string_width(title) + 2
                            sep_w = 2
                            tab_end_x = cur_x + pill_w + (sep_w if idx < len(self.tab_titles) - 1 else 0)
                            if rel_x < tab_end_x:
                                self.set_tab(idx)
                                return self, None
                            cur_x += pill_w + sep_w
                        self.set_tab(len(self.tab_titles) - 1)
                        return self, None

                    # Active tab controls
                    cur_line = 4
                    for idx, ctrl in enumerate(controls):
                        ctrl_h = len(ctrl.view().splitlines()) if isinstance(ctrl, Select) else 1
                        if cur_line <= rel_y < cur_line + ctrl_h:
                            self.tab_focus_idx = idx
                            self._sync_focus()
                            if isinstance(ctrl, Switch):
                                return self, ctrl.toggle()[1]
                            elif isinstance(ctrl, Select):
                                local_y = rel_y - cur_line
                                if not ctrl.is_open:
                                    ctrl.open()
                                    return self, None
                                else:
                                    if 0 <= local_y <= 2:
                                        ctrl.close()
                                        return self, None
                                    opt_idx = local_y - 4
                                    if 0 <= opt_idx < len(ctrl.options):
                                        return self, ctrl.choose(opt_idx)[1]
                                    ctrl.close()
                                    return self, None
                        else:
                            if isinstance(ctrl, Select) and ctrl.is_open:
                                ctrl.close()
                        cur_line += ctrl_h + 1

                    # Save / Cancel buttons (span lines 16 .. 19)
                    if 16 <= rel_y <= 19:
                        if rel_x < 30:
                            self.tab_focus_idx = -2
                            return self._submit()
                        else:
                            self.tab_focus_idx = -1
                            def _cancel_click() -> Msg:
                                return ModalCloseMsg()
                            return self, _cancel_click

        return self, None

    def view(self) -> str:
        inner_w = max(48, self.width - 2)

        # Title banner
        title = Style().bold(True).foreground("#00E5FF").render("⚙️  MASTUI PREFERENCES & OPTIONS")

        # Tabs bar
        tabs_view = self.tabs.view()

        # Render controls for active tab
        controls = self.current_tab_controls
        control_lines: list[str] = []

        for idx, ctrl in enumerate(controls):
            if isinstance(ctrl, Switch):
                prefix = " ▶ " if self.tab_focus_idx == idx else "   "
                color = "#FFFFFF" if self.tab_focus_idx == idx else "#CCCCCC"
                lbl_style = Style().bold(self.tab_focus_idx == idx).foreground(color)
                control_lines.append(f"{prefix}{ctrl.view()}")
            elif isinstance(ctrl, Select):
                prefix = " ▶ " if self.tab_focus_idx == idx else "   "
                sel_subview = ctrl.view()
                sub_lines = sel_subview.splitlines()
                indented_lines = []
                for l_idx, l in enumerate(sub_lines):
                    # Show arrow only on first line, pad subsequent lines with spaces
                    p = prefix if l_idx == 0 else "   "
                    indented_lines.append(f"{p}{l}")
                control_lines.append("\n".join(indented_lines))
            control_lines.append("")  # breathing space

        body_str = "\n".join(control_lines)
        actual_lines = body_str.splitlines()
        while len(actual_lines) < 12:
            actual_lines.append("")
        body_content = "\n".join(actual_lines)

        # Bottom buttons
        save_focus = (self.tab_focus_idx == -2)
        cancel_focus = (self.tab_focus_idx == -1)

        save_style = (
            Style().bold(True).foreground("#00E5FF").border(ROUNDED_BORDER).border_foreground("#00E5FF")
            if save_focus
            else Style().foreground("#AAAAAA").border(ROUNDED_BORDER).border_foreground("#555566")
        )
        cancel_style = (
            Style().bold(True).foreground("#FF5555").border(ROUNDED_BORDER).border_foreground("#FF5555")
            if cancel_focus
            else Style().foreground("#777788").border(ROUNDED_BORDER).border_foreground("#444455")
        )

        save_btn = save_style.render("  💾 Save Preferences  ")
        cancel_btn = cancel_style.render("  ❌ Cancel  ")
        buttons_row = join_horizontal(Align.TOP, "  ", save_btn, "    ", cancel_btn)

        if inner_w >= 80:
            hints_str = "[1-6] Jump Tab  [←/→] Switch Tab  [Tab] Focus  [Space] Toggle  [Esc] Cancel"
        else:
            hints_str = "[1-6] Tab  [←/→] Switch  [Tab] Focus  [Space] Toggle  [Esc] Cancel"
        hints = Style().foreground("#666688").render(f" {hints_str}")

        modal_body = (
            f" {title}\n"
            f" {tabs_view}\n\n"
            f"{body_content}\n"
            f"{buttons_row}\n\n"
            f" {hints}"
        )

        return (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#00E5FF")
            .width(inner_w)
            .render(modal_body)
        )
