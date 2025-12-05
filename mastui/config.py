from pathlib import Path
from dotenv import dotenv_values
import logging

from mastui.languages import (
    dedupe_language_codes,
    get_default_language_codes,
)

log = logging.getLogger(__name__)

class Config:
    def __init__(self, profile_path: Path = None):
        if profile_path:
            self.profile_path = profile_path
        else:
            # Fallback for old single-profile structure
            self.profile_path = Path.home() / ".config" / "mastui"
        
        self.profile_name = self.profile_path.name

        self.image_cache_dir = self.profile_path / "image_cache"
        self.image_cache_dir.mkdir(exist_ok=True)
        self.env_file = self.profile_path / ".env"
        
        config_values = {}
        if self.env_file.exists():
            config_values = dotenv_values(self.env_file)
            log.debug(f"Loaded config from {self.env_file}: {config_values}")
        else:
            log.warning(f"Config file not found: {self.env_file}")


        self.mastodon_host = config_values.get("MASTODON_HOST")
        self.mastodon_client_id = config_values.get("MASTODON_CLIENT_ID")
        self.mastodon_client_secret = config_values.get("MASTODON_CLIENT_SECRET")
        self.mastodon_access_token = config_values.get("MASTODON_ACCESS_TOKEN")
        self.ssl_verify = True
        
        self.theme = config_values.get("THEME", "textual-dark")
        self.preferred_dark_theme = config_values.get("PREFERRED_DARK_THEME", "textual-dark")
        self.preferred_light_theme = config_values.get("PREFERRED_LIGHT_THEME", "textual-light")

        # Auto-refresh settings
        self.home_auto_refresh = config_values.get("HOME_AUTO_REFRESH", "on") == "on"
        self.home_auto_refresh_interval = float(config_values.get("HOME_AUTO_REFRESH_INTERVAL", "2"))
        self.local_auto_refresh = config_values.get("LOCAL_AUTO_REFRESH", "on") == "on"
        self.local_auto_refresh_interval = float(config_values.get("LOCAL_AUTO_REFRESH_INTERVAL", "2"))
        self.notifications_auto_refresh = config_values.get("NOTIFICATIONS_AUTO_REFRESH", "on") == "on"
        self.notifications_auto_refresh_interval = float(config_values.get("NOTIFICATIONS_AUTO_REFRESH_INTERVAL", "10"))
        self.federated_auto_refresh = config_values.get("FEDERATED_AUTO_REFRESH", "on") == "on"
        self.federated_auto_refresh_interval = float(config_values.get("FEDERATED_AUTO_REFRESH_INTERVAL", "2"))

        # Image settings
        self.image_support = config_values.get("IMAGE_SUPPORT", "off") == "on"
        self.image_renderer = config_values.get("IMAGE_RENDERER", "ansi")
        self.auto_prune_cache = config_values.get("AUTO_PRUNE_CACHE", "on") == "on"

        # Timeline settings
        self.home_timeline_enabled = config_values.get("HOME_TIMELINE_ENABLED", "on") == "on"
        self.local_timeline_enabled = config_values.get("LOCAL_TIMELINE_ENABLED", "off") == "on"
        self.notifications_timeline_enabled = config_values.get("NOTIFICATIONS_TIMELINE_ENABLED", "on") == "on"
        self.federated_timeline_enabled = config_values.get("FEDERATED_TIMELINE_ENABLED", "on") == "on"
        self.direct_timeline_enabled = config_values.get("DIRECT_TIMELINE_ENABLED", "on") == "on"
        self.force_single_column = config_values.get("FORCE_SINGLE_COLUMN", "off") == "on"

        # Notification settings
        self.notifications_popups_mentions = config_values.get("NOTIFICATIONS_POPUPS_MENTIONS", "off") == "on"
        self.notifications_popups_follows = config_values.get("NOTIFICATIONS_POPUPS_FOLLOWS", "off") == "on"
        self.notifications_popups_reblogs = config_values.get("NOTIFICATIONS_POPUPS_REBLOGS", "off") == "on"
        self.notifications_popups_favourites = config_values.get("NOTIFICATIONS_POPUPS_FAVOURITES", "off") == "on"

        # Language preferences for composer
        stored_languages = config_values.get("POST_LANGUAGES", "")
        if stored_languages:
            parsed_languages = dedupe_language_codes(stored_languages.split(","))
        else:
            parsed_languages = []
        if not parsed_languages:
            parsed_languages = get_default_language_codes()
        self.post_languages = parsed_languages


    def save_config(self):
        with open(self.env_file, "w") as f:
            if self.mastodon_host:
                f.write(f"MASTODON_HOST={self.mastodon_host}\n")
            if self.mastodon_client_id:
                f.write(f"MASTODON_CLIENT_ID={self.mastodon_client_id}\n")
            if self.mastodon_client_secret:
                f.write(f"MASTODON_CLIENT_SECRET={self.mastodon_client_secret}\n")
            if self.mastodon_access_token:
                f.write(f"MASTODON_ACCESS_TOKEN={self.mastodon_access_token}\n")
            if self.theme:
                f.write(f"THEME={self.theme}\n")
            if self.preferred_dark_theme:
                f.write(f"PREFERRED_DARK_THEME={self.preferred_dark_theme}\n")
            if self.preferred_light_theme:
                f.write(f"PREFERRED_LIGHT_THEME={self.preferred_light_theme}\n")
            
            f.write(f"HOME_AUTO_REFRESH={'on' if self.home_auto_refresh else 'off'}\n")
            f.write(f"HOME_AUTO_REFRESH_INTERVAL={self.home_auto_refresh_interval}\n")
            f.write(f"LOCAL_AUTO_REFRESH={'on' if self.local_auto_refresh else 'off'}\n")
            f.write(f"LOCAL_AUTO_REFRESH_INTERVAL={self.local_auto_refresh_interval}\n")
            f.write(f"NOTIFICATIONS_AUTO_REFRESH={'on' if self.notifications_auto_refresh else 'off'}\n")
            f.write(f"NOTIFICATIONS_AUTO_REFRESH_INTERVAL={self.notifications_auto_refresh_interval}\n")
            f.write(f"FEDERATED_AUTO_REFRESH={'on' if self.federated_auto_refresh else 'off'}\n")
            f.write(f"FEDERATED_AUTO_REFRESH_INTERVAL={self.federated_auto_refresh_interval}\n")
            f.write(f"IMAGE_SUPPORT={'on' if self.image_support else 'off'}\n")
            f.write(f"IMAGE_RENDERER={self.image_renderer}\n")
            f.write(f"AUTO_PRUNE_CACHE={'on' if self.auto_prune_cache else 'off'}\n")
            f.write(f"HOME_TIMELINE_ENABLED={'on' if self.home_timeline_enabled else 'off'}\n")
            f.write(f"LOCAL_TIMELINE_ENABLED={'on' if self.local_timeline_enabled else 'off'}\n")
            f.write(f"NOTIFICATIONS_TIMELINE_ENABLED={'on' if self.notifications_timeline_enabled else 'off'}\n")
            f.write(f"FEDERATED_TIMELINE_ENABLED={'on' if self.federated_timeline_enabled else 'off'}\n")
            f.write(f"DIRECT_TIMELINE_ENABLED={'on' if self.direct_timeline_enabled else 'off'}\n")
            f.write(f"FORCE_SINGLE_COLUMN={'on' if self.force_single_column else 'off'}\n")
            f.write(f"NOTIFICATIONS_POPUPS_MENTIONS={'on' if self.notifications_popups_mentions else 'off'}\n")
            f.write(f"NOTIFICATIONS_POPUPS_FOLLOWS={'on' if self.notifications_popups_follows else 'off'}\n")
            f.write(f"NOTIFICATIONS_POPUPS_REBLOGS={'on' if self.notifications_popups_reblogs else 'off'}\n")
            f.write(f"NOTIFICATIONS_POPUPS_FAVOURITES={'on' if self.notifications_popups_favourites else 'off'}\n")
            f.write(f"POST_LANGUAGES={','.join(self.post_languages)}\n")

    def save_credentials(self, host, client_id, client_secret, access_token):
        self.mastodon_host = host
        self.mastodon_client_id = client_id
        self.mastodon_client_secret = client_secret
        self.mastodon_access_token = access_token
        self.save_config()
