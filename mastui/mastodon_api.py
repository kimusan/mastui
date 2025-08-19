from mastodon import Mastodon, MastodonError
from mastui.config import config
from requests import Session
import logging

log = logging.getLogger(__name__)


def get_api():
    """Initializes and returns a Mastodon API instance."""
    if config.mastodon_access_token:
        s = Session()
        s.verify = config.ssl_verify
        return Mastodon(
            access_token=config.mastodon_access_token,
            api_base_url=f"https://{config.mastodon_host}",
            session=s,
        )
    return None


def login(host, auth_code):
    """Logs in to a Mastodon instance using an auth code and returns the API object or an error."""
    try:
        s = Session()
        s.verify = config.ssl_verify
        mastodon = Mastodon(
            client_id=config.mastodon_client_id,
            client_secret=config.mastodon_client_secret,
            api_base_url=f"https://{host}",
            session=s,
        )
        access_token = mastodon.log_in(
            code=auth_code,
            redirect_uri="urn:ietf:wg:oauth:2.0:oob",
            scopes=["read", "write", "follow", "push"],
        )
        config.save_credentials(
            host, config.mastodon_client_id, config.mastodon_client_secret, access_token
        )
        final_session = Session()
        final_session.verify = config.ssl_verify
        # Re-initialize with the new access token
        api = Mastodon(
            access_token=access_token,
            api_base_url=f"https://{host}",
            session=final_session,
        )
        return api, None
    except Exception as e:
        return None, str(e)


def create_app(host):
    """Creates a new Mastodon app and returns the auth URL."""
    try:
        s = Session()
        s.verify = config.ssl_verify
        client_id, client_secret = Mastodon.create_app(
            "mastui",
            api_base_url=f"https://{host}",
            scopes=["read", "write", "follow", "push"],
            redirect_uris="urn:ietf:wg:oauth:2.0:oob",
            session=s,
        )
        # We need to save the client creds to the .env file for the login step
        config.mastodon_host = host
        config.mastodon_client_id = client_id
        config.mastodon_client_secret = client_secret
        config.save_config()

        mastodon = Mastodon(
            client_id=client_id,
            client_secret=client_secret,
            api_base_url=f"https://{host}",
        )
        auth_url = mastodon.auth_request_url(
            redirect_uris="urn:ietf:wg:oauth:2.0:oob",
            scopes=["read", "write", "follow", "push"],
        )
        return auth_url, None
    except MastodonError as e:
        log.error(
            f"Mastodon API error during app creation for host '{host}': {e}",
            exc_info=True,
        )

        # Log the raw response if available on the exception
        if hasattr(e, "text") and e.text:
            log.debug(f"Raw server response from '{host}':\n{e.text}")

        error_message = str(e)
        if "Expecting value" in error_message:
            error_message = f"Could not parse server response from '{host}'. The instance may be offline, misconfigured, or not a Mastodon instance."

        return None, error_message
    except Exception as e:
        # Catch any other potential errors (e.g., network issues not caught by MastodonError)
        log.error(
            f"Unexpected error during app creation for host '{host}': {e}",
            exc_info=True,
        )
        return None, str(e)
