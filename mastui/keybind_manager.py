import json
from pathlib import Path
import logging

log = logging.getLogger(__name__)

class KeybindManager:
    def __init__(self, profile_path: Path):
        self.keymap_path = profile_path / "keymap.json"
        self.keymap = {}
        self.default_keymap = {
            "quit": "q",
            "toggle_dark": "d",
            "refresh_timelines": "r",
            "compose_post": "c",
            "view_profile": "p",
            "reply_to_post": "a",
            "edit_post": "e",
            "delete_post": "delete",
            "show_urls": "x",
            "open_options": "o",
            "search": "/",
            "switch_profile": "u",
            "toggle_dms": "m",
            "like_post": "l",
            "boost_post": "b",
            "go_to_top": "g",
            "scroll_up": "up",
            "scroll_down": "down",
            "focus_previous_column": "left",
            "focus_next_column": "right",
            "show_help": "?",
            "view_log": "f12",
        }
        self.action_descriptions = {
            "quit": "Quit the application",
            "toggle_dark": "Toggle dark/light mode",
            "refresh_timelines": "Refresh all timelines",
            "compose_post": "Compose new post",
            "view_profile": "View author's profile",
            "reply_to_post": "Reply to post",
            "edit_post": "Edit your own post",
            "delete_post": "Delete your own post",
            "show_urls": "Show urls in post",
            "open_options": "Open options screen",
            "search": "Open search screen",
            "switch_profile": "Switch user profile",
            "toggle_dms": "Toggle Direct Messages timeline",
            "like_post": "Like / Unlike post",
            "boost_post": "Boost / Unboost post",
            "go_to_top": "Jump to top of timeline",
            "scroll_up": "Move selection up",
            "scroll_down": "Move selection down",
            "focus_previous_column": "Focus previous column",
            "focus_next_column": "Focus next column",
            "show_help": "Show this help screen",
            "view_log": "View Log File (Debug)",
        }

    def load_keymap(self):
        if self.keymap_path.exists():
            try:
                with open(self.keymap_path, "r") as f:
                    self.keymap = json.load(f)
                # Ensure all default actions are present
                for action, key in self.default_keymap.items():
                    if action not in self.keymap:
                        self.keymap[action] = key
            except (json.JSONDecodeError, IOError) as e:
                log.error(f"Failed to load keymap, using defaults: {e}")
                self.keymap = self.default_keymap.copy()
        else:
            self.keymap = self.default_keymap.copy()
        self.save_keymap() # Save to create file or add missing keys

    def save_keymap(self):
        try:
            with open(self.keymap_path, "w") as f:
                json.dump(self.keymap, f, indent=4)
        except IOError as e:
            log.error(f"Failed to save keymap: {e}")

    def get_key(self, action: str) -> str:
        return self.keymap.get(action, "")

    def reset_to_defaults(self):
        self.keymap = self.default_keymap.copy()
        self.save_keymap()
