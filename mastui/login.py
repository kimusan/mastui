import clipman
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical
from textual.widgets import Button, Label, Input, Static, TextArea, LoadingIndicator, Header
from textual.screen import ModalScreen
from urllib.parse import urlparse

from mastui.mastodon_api import login, create_app
import logging

log = logging.getLogger(__name__)


class LoginScreen(ModalScreen):
    """Screen for user to login."""

    def compose(self) -> ComposeResult:
        self.title = "Mastui Login"
        with Grid(id="dialog"):
            yield Header(show_clock=False)
            yield Label("Mastodon Instance:", id="host_label")
            yield Input(placeholder="mastodon.social", id="host")

            yield Static()  # Spacer
            yield Button("Get Auth Link", variant="primary", id="get_auth")

            yield LoadingIndicator(classes="hidden")
            yield Static(id="status", classes="hidden")

            with Vertical(id="auth_link_container", classes="hidden"):
                yield Static(
                    "1. Link copied to clipboard! Open it in your browser to authorize.",
                    id="clipboard-status",
                )
                yield TextArea(
                    "",
                    id="auth_link",
                )
                yield Static("2. Paste the authorization code here:")
                yield Input(placeholder="Authorization Code", id="auth_code")
                yield Button("Login", variant="primary", id="login")

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        self.query_one("#host").focus()

    def clean_host(self, host_input: str) -> str:
        """Cleans the host input to be a valid domain."""
        if not host_input:
            return ""
        
        # Prepend a scheme if one isn't present, for urlparse to work correctly.
        if not host_input.startswith(('http://', 'https://')):
            host_input = 'https://' + host_input
            
        parsed_url = urlparse(host_input)
        # netloc contains the domain and potentially the port
        return parsed_url.netloc

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        status = self.query_one("#status")
        spinner = self.query_one(LoadingIndicator)

        if event.button.id == "get_auth":
            host_input_widget = self.query_one("#host")
            host_value = host_input_widget.value
            if not host_value:
                status.update("[red]Please enter a Mastodon instance.[/red]")
                status.remove_class("hidden")
                return

            cleaned_host = self.clean_host(host_value)
            if not cleaned_host:
                status.update("[red]Invalid instance name.[/red]")
                status.remove_class("hidden")
                return
            
            # Update the input field with the cleaned value for user feedback
            host_input_widget.value = cleaned_host

            spinner.remove_class("hidden")
            status.add_class("hidden")
            self.run_worker(
                lambda: self.app.call_from_thread(
                    self.on_auth_link_created, create_app(cleaned_host)
                ),
                exclusive=True,
                thread=True,
            )

        elif event.button.id == "login":
            auth_code = self.query_one("#auth_code").value
            host = self.query_one("#host").value
            if not auth_code:
                status.update("[red]Please enter the authorization code.[/red]")
                status.remove_class("hidden")
                return

            spinner.remove_class("hidden")
            status.add_class("hidden")
            self.run_worker(
                lambda: self.app.call_from_thread(
                    self.on_login_complete, login(host, auth_code)
                ),
                exclusive=True,
                thread=True,
            )

    def on_auth_link_created(self, result) -> None:
        """Callback for when the auth link is created."""
        status = self.query_one("#status")
        spinner = self.query_one(LoadingIndicator)
        spinner.add_class("hidden")
        
        try:
            auth_url, error = result

            if error:
                status.update(f"[red]Error: {error}[/red]")
                status.remove_class("hidden")
                return

            try:
                clipman.init()
                clipman.set(auth_url)
                self.query_one("#clipboard-status").update(
                    "1. Link copied to clipboard! Open it in your browser to authorize."
                )
            except clipman.exceptions.ClipmanBaseException as e:
                log.warning(f"Could not copy to clipboard: {e}")
                self.query_one("#clipboard-status").update(
                    "1. Could not copy to clipboard. Please copy the link below manually:"
                )

            auth_link_input = self.query_one("#auth_link")
            auth_link_input.text = auth_url
            auth_link_input.read_only = True
            self.query_one("#auth_link_container").remove_class("hidden")
            self.query_one("#get_auth").add_class("hidden")
            self.query_one("#host_label").add_class("hidden")
            self.query_one("#host").disabled = True
            self.query_one("#auth_code").focus()
        except Exception as e:
            log.error(f"Error in on_auth_link_created: {e}", exc_info=True)
            status.update(f"[red]An unexpected error occurred. See log for details.[/red]")
            status.remove_class("hidden")

    def on_login_complete(self, result) -> None:
        """Callback for when the login is complete."""
        api, error = result
        status = self.query_one("#status")
        spinner = self.query_one(LoadingIndicator)
        spinner.add_class("hidden")

        if api:
            self.dismiss(api)
        else:
            status.update(f"[red]Login failed: {error}[/red]")
            status.remove_class("hidden")
