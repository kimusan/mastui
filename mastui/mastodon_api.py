from mastodon import Mastodon, MastodonError
from requests import Session
from requests.exceptions import RequestException
import logging

log = logging.getLogger(__name__)


def get_api(config_obj):
    """Initializes and returns a Mastodon API instance."""
    conf = config_obj
    if conf.mastodon_access_token:
        s = Session()
        s.verify = conf.ssl_verify
        return Mastodon(
            access_token=conf.mastodon_access_token,
            api_base_url=f"https://{conf.mastodon_host}",
            session=s,
            mastodon_version="4.0.0",
        )
    return None


def login(host, client_id, client_secret, auth_code, ssl_verify=True):
    """Logs in to a Mastodon instance using an auth code (or direct access token) and returns the API object or an error."""
    try:
        import urllib.parse

        # 1. Clean and normalize the auth input
        clean_code = str(auth_code or "").strip().strip("'\"")
        if "code=" in clean_code:
            try:
                parsed = urllib.parse.urlparse(clean_code)
                qs = urllib.parse.parse_qs(parsed.query)
                if "code" in qs:
                    clean_code = qs["code"][0].strip().strip("'\"")
                else:
                    clean_code = clean_code.split("code=", 1)[1].split("&")[0].split()[0].strip().strip("'\"")
            except Exception:
                pass
        if clean_code.startswith("Bearer "):
            clean_code = clean_code[7:].strip()

        # 2. Check if clean_code is directly a valid access token (e.g. created via web UI)
        try:
            direct_session = Session()
            direct_session.verify = ssl_verify
            direct_api = Mastodon(
                access_token=clean_code,
                api_base_url=f"https://{host}",
                session=direct_session,
            )
            me = direct_api.me()
            if me and isinstance(me, dict) and ("username" in me or "id" in me):
                env_content = (
                    f"MASTODON_HOST={host}\n"
                    f"MASTODON_CLIENT_ID={client_id or ''}\n"
                    f"MASTODON_CLIENT_SECRET={client_secret or ''}\n"
                    f"MASTODON_ACCESS_TOKEN={clean_code}\n"
                )
                return direct_api, env_content, None
        except Exception:
            pass

        # 3. Exchange authorization code for access token via OAuth
        s = Session()
        s.verify = ssl_verify
        mastodon = Mastodon(
            client_id=client_id,
            client_secret=client_secret,
            api_base_url=f"https://{host}",
            session=s,
            mastodon_version="4.0.0",
        )
        try:
            access_token = mastodon.log_in(
                code=clean_code,
                redirect_uri="urn:ietf:wg:oauth:2.0:oob",
                scopes=["read", "write", "follow", "push"],
            )
        except Exception as oauth_err:
            # Fallback without 'push' scope in case server does not support webpush scope
            try:
                access_token = mastodon.log_in(
                    code=clean_code,
                    redirect_uri="urn:ietf:wg:oauth:2.0:oob",
                    scopes=["read", "write", "follow"],
                )
            except Exception:
                raise oauth_err

        # Create the content for the .env file
        env_content = (
            f"MASTODON_HOST={host}\n"
            f"MASTODON_CLIENT_ID={client_id}\n"
            f"MASTODON_CLIENT_SECRET={client_secret}\n"
            f"MASTODON_ACCESS_TOKEN={access_token}\n"
        )

        final_session = Session()
        final_session.verify = ssl_verify
        # Re-initialize with the new access token
        api = Mastodon(
            access_token=access_token,
            api_base_url=f"https://{host}",
            session=final_session,
        )
        return api, env_content, None
    except MastodonError as e:
        err_msg = str(e)
        if "invalid_grant" in err_msg:
            err_msg = "Invalid or expired authorization code. Please verify you copied the entire code, or get a fresh link."
        log.warning(f"Mastodon API error during login for host '{host}': {e}")
        return None, None, err_msg
    except (RequestException, OSError, ValueError, TypeError) as e:
        log.error(f"Unexpected error during login for host '{host}': {e}", exc_info=True)
        return None, None, str(e)


def create_app(host, ssl_verify=True):
    """Creates a new Mastodon app and returns the auth URL."""
    try:
        s = Session()
        s.verify = ssl_verify
        client_id, client_secret = Mastodon.create_app(
            "mastui",
            api_base_url=f"https://{host}",
            scopes=["read", "write", "follow", "push"],
            redirect_uris="urn:ietf:wg:oauth:2.0:oob",
            session=s,
        )

        mastodon = Mastodon(
            client_id=client_id,
            client_secret=client_secret,
            api_base_url=f"https://{host}",
            session=s,
            mastodon_version="4.0.0",
        )
        auth_url = mastodon.auth_request_url(
            redirect_uris="urn:ietf:wg:oauth:2.0:oob",
            scopes=["read", "write", "follow", "push"],
        )
        return auth_url, client_id, client_secret, None

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

        return None, None, None, error_message
    except (RequestException, OSError, ValueError, TypeError) as e:
        # Catch any other potential errors (e.g., network issues not caught by MastodonError)
        log.error(
            f"Unexpected error during app creation for host '{host}': {e}",
            exc_info=True,
        )
        return None, None, None, str(e)
