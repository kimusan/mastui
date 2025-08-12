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

    def save_credentials(self, host, client_id, client_secret, access_token):
        with open(".env", "w") as f:
            f.write(f"MASTODON_HOST={host}\n")
            f.write(f"MASTODON_CLIENT_ID={client_id}\n")
            f.write(f"MASTODON_CLIENT_SECRET={client_secret}\n")
            f.write(f"MASTODON_ACCESS_TOKEN={access_token}\n")

config = Config()
