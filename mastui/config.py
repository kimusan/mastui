import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.mastodon_host = os.getenv("MASTODON_HOST")
        self.mastodon_client_id = os.getenv("MASTODON_CLIENT_ID")
        self.mastodon_client_secret = os.getenv("MASTODON_CLIENT_SECRET")
        self.mastodon_access_token = os.getenv("MASTODON_ACCESS_TOKEN")
        self.ssl_verify = True
        self.theme = os.getenv("THEME", "dark")

    def save_config(self):
        with open(".env", "w") as f:
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

    def save_credentials(self, host, client_id, client_secret, access_token):
        self.mastodon_host = host
        self.mastodon_client_id = client_id
        self.mastodon_client_secret = client_secret
        self.mastodon_access_token = access_token
        self.save_config()

config = Config()
