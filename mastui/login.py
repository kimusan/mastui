import clipman
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical
from textual.widgets import Button, Label, Input, Static, TextArea, LoadingIndicator, Header, ContentSwitcher
from textual.screen import ModalScreen
from urllib.parse import urlparse
from rich.panel import Panel

from mastui.mastodon_api import login, create_app
import logging

log = logging.getLogger(__name__)


class LoginScreen(ModalScreen):
    """Screen for user to login."""

    def __init__(self, host: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host = host
        self.client_id = None
        self.client_secret = None

    def compose(self) -> ComposeResult:
        with Vertical(id="login-dialog") as d:
            d.border_title = "Mastui Login"
            with ContentSwitcher(initial="login-initial-view"):
                with Vertical(id="login-initial-view"):
                    yield Static("[bold]Welcome to Mastui![/bold]\n\nEnter your Mastodon instance to get started.")
                    with Grid(id="login-grid"):
                        yield Label("Mastodon Instance:")
                        yield Input(placeholder="mastodon.social", id="host", value=self.host or "")
                    yield Static() # Spacer
                    yield Button("Get Auth Link", variant="primary", id="get_auth")

                with Vertical(id="login-auth-view"):
                    yield Static("1. An authorization link has been copied to your clipboard (if possible).")
                    yield Static("   Open it in your browser to grant Mastui access.")
                    yield TextArea("", id="auth_link", read_only=True)
                    yield Static("\n2. Paste the authorization code you received here:")
                    yield Input(placeholder="Authorization Code", id="auth_code")
                    yield Button("Login", variant="primary", id="login")

                with Vertical(id="login-loading-view", classes="centered"):
                     yield Static("Working...")
                     yield LoadingIndicator()

            yield Static(id="login-status")


    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        host_input = self.query_one("#host")
        if self.host:
            host_input.disabled = True
            self.query_one("#get_auth").focus()
        else:
            host_input.focus()

    def clean_host(self, host_input: str) -> str:
        """Cleans the host input to be a valid domain."""
        if not host_input:
            return ""
        
        # Prepend a scheme if one isn't present, for urlparse to work correctly.
        if not host_input.startswith(('http://', 'https ')):
            host_input = 'https://' + host_input
            
        parsed_url = urlparse(host_input)
        # netloc contains the domain and potentially the port
        return parsed_url.netloc

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        status = self.query_one("#login-status")
        switcher = self.query_one(ContentSwitcher)

        if event.button.id == "get_auth":
            host_input_widget = self.query_one("#host")
            host_value = host_input_widget.value
            if not host_value:
                status.update("Please enter a Mastodon instance.")
                return

            cleaned_host = self.clean_host(host_value)
            if not cleaned_host:
                status.update("Invalid instance name.")
                return
            
            host_input_widget.value = cleaned_host
            switcher.current = "login-loading-view"
            status.update("")
            self.run_worker(
                lambda: (
                    result := create_app(cleaned_host, self.app.ssl_verify),
                    log.debug(f"create_app() returned: {result}"),
                    self.app.call_from_thread(self.on_auth_link_created, result),
                ),
                exclusive=True,
                thread=True,
            )

        elif event.button.id == "login":
            auth_code = self.query_one("#auth_code").value
            host = self.query_one("#host").value
            if not auth_code:
                status.update("Please enter the authorization code.")
                return

            switcher.current = "login-loading-view"
            status.update("")
            self.run_worker(
                lambda: (
                    result := login(
                        host,
                        self.client_id,
                        self.client_secret,
                        auth_code,
                        self.app.ssl_verify,
                    ),
                    log.debug(f"login() returned: {result}"),
                    self.app.call_from_thread(self.on_login_complete, result),
                ),
                exclusive=True,
                thread=True,
            )

    def on_auth_link_created(self, result) -> None:
        """Callback for when the auth link is created."""
        status = self.query_one("#login-status")
        switcher = self.query_one(ContentSwitcher)
        
        try:
            auth_url, client_id, client_secret, error = result
            self.client_id = client_id
            self.client_secret = client_secret

            if error:
                status.update(f"Error: {error}")
                switcher.current = "login-initial-view"
                return

            try:
                clipman.init()
                clipman.set(auth_url)
            except clipman.exceptions.ClipmanBaseException as e:
                log.warning(f"Could not copy to clipboard: {e}")
                status.update(
                    "Link copied to clipboard: failed.\n"
                    "Wayland users may need wl-clipboard (e.g., `sudo apt install wl-clipboard`)."
                )

            auth_link_input = self.query_one("#auth_link")
            auth_link_input.text = auth_url
            switcher.current = "login-auth-view"
            self.query_one("#auth_code").focus()
        except (TypeError, ValueError) as e:
            log.error(f"Error unpacking result in on_auth_link_created: {result} - {e}", exc_info=True)
            status.update("An unexpected error occurred. See log for details.")
            switcher.current = "login-initial-view"
        except Exception as e:
            log.error(f"Unexpected error in on_auth_link_created: {e}", exc_info=True)
            status.update("An unexpected error occurred. See log for details.")
            switcher.current = "login-initial-view"

    def on_login_complete(self, result) -> None:
        """Callback for when the login is complete."""
        log.debug(f"on_login_complete received result: {result}")
        status = self.query_one("#login-status")
        switcher = self.query_one(ContentSwitcher)

        api, env_content, error = result

        if api:
            self.dismiss((api, env_content))
            return
        else:
            status.update(f"Login failed: {error}")
            switcher.current = "login-auth-view"
