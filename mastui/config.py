import os
from dotenv import load_dotenv
from pathlib import Path

class Config:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "mastui"
        self.image_cache_dir = self.config_dir / "image_cache"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.image_cache_dir.mkdir(exist_ok=True)
        self.env_file = self.config_dir / ".env"
        
        if self.env_file.exists():
            load_dotenv(self.env_file)

        self.mastodon_host = os.getenv("MASTODON_HOST")
        self.mastodon_client_id = os.getenv("MASTODON_CLIENT_ID")
        self.mastodon_client_secret = os.getenv("MASTODON_CLIENT_SECRET")
        self.mastodon_access_token = os.getenv("MASTODON_ACCESS_TOKEN")
        self.ssl_verify = True
        
        self.theme = os.getenv("THEME", "textual-dark")
        self.preferred_dark_theme = os.getenv("PREFERRED_DARK_THEME", "textual-dark")
        self.preferred_light_theme = os.getenv("PREFERRED_LIGHT_THEME", "textual-light")

        # Auto-refresh settings
        self.home_auto_refresh = os.getenv("HOME_AUTO_REFRESH", "on") == "on"
        self.home_auto_refresh_interval = int(os.getenv("HOME_AUTO_REFRESH_INTERVAL", "2"))
        self.notifications_auto_refresh = os.getenv("NOTIFICATIONS_AUTO_REFRESH", "on") == "on"
        self.notifications_auto_refresh_interval = int(os.getenv("NOTIFICATIONS_AUTO_REFRESH_INTERVAL", "10"))
        self.federated_auto_refresh = os.getenv("FEDERATED_AUTO_REFRESH", "on") == "on"
        self.federated_auto_refresh_interval = int(os.getenv("FEDERATED_AUTO_REFRESH_INTERVAL", "2"))

        # Image settings
        self.image_support = os.getenv("IMAGE_SUPPORT", "off") == "on"
        self.image_renderer = os.getenv("IMAGE_RENDERER", "ansi")
        self.auto_prune_cache = os.getenv("AUTO_PRUNE_CACHE", "on") == "on"

        # Timeline settings
        self.home_timeline_enabled = os.getenv("HOME_TIMELINE_ENABLED", "on") == "on"
        self.notifications_timeline_enabled = os.getenv("NOTIFICATIONS_TIMELINE_ENABLED", "on") == "on"
        self.federated_timeline_enabled = os.getenv("FEDERATED_TIMELINE_ENABLED", "on") == "on"
        self.force_single_column = os.getenv("FORCE_SINGLE_COLUMN", "off") == "on"


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
            f.write(f"NOTIFICATIONS_AUTO_REFRESH={'on' if self.notifications_auto_refresh else 'off'}\n")
            f.write(f"NOTIFICATIONS_AUTO_REFRESH_INTERVAL={self.notifications_auto_refresh_interval}\n")
            f.write(f"FEDERATED_AUTO_REFRESH={'on' if self.federated_auto_refresh else 'off'}\n")
            f.write(f"FEDERATED_AUTO_REFRESH_INTERVAL={self.federated_auto_refresh_interval}\n")
            f.write(f"IMAGE_SUPPORT={'on' if self.image_support else 'off'}\n")
            f.write(f"IMAGE_RENDERER={self.image_renderer}\n")
            f.write(f"AUTO_PRUNE_CACHE={'on' if self.auto_prune_cache else 'off'}\n")
            f.write(f"HOME_TIMELINE_ENABLED={'on' if self.home_timeline_enabled else 'off'}\n")
            f.write(f"NOTIFICATIONS_TIMELINE_ENABLED={'on' if self.notifications_timeline_enabled else 'off'}\n")
            f.write(f"FEDERATED_TIMELINE_ENABLED={'on' if self.federated_timeline_enabled else 'off'}\n")
            f.write(f"FORCE_SINGLE_COLUMN={'on' if self.force_single_column else 'off'}\n")

    def save_credentials(self, host, client_id, client_secret, access_token):
        self.mastodon_host = host
        self.mastodon_client_id = client_id
        self.mastodon_client_secret = client_secret
        self.mastodon_access_token = access_token
        self.save_config()

config = Config()
