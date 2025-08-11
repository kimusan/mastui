import pyperclip
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical
from textual.widgets import Button, Label, Input, Static, TextArea
from textual.screen import ModalScreen

from mastui.mastodon_api import login, create_app

class LoginScreen(ModalScreen):
    """Screen for user to login."""

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            yield Label("Mastodon Instance:")
            yield Input(placeholder="mastodon.social", id="host")
            
            yield Static() # Spacer
            yield Button("Get Auth Link", variant="primary", id="get_auth")

            yield Static(id="status", classes="hidden")

            with Vertical(id="auth_link_container", classes="hidden"):
                yield Static("1. Link copied to clipboard! Open it in your browser to authorize.")
                yield TextArea("", id="auth_link",)
                yield Static("2. Paste the authorization code here:")
                yield Input(placeholder="Authorization Code", id="auth_code")
                yield Button("Login", variant="primary", id="login")


    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        self.query_one("#host").focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        status = self.query_one("#status")
        if event.button.id == "get_auth":
            host = self.query_one("#host").value
            if not host:
                status.update("[red]Please enter a Mastodon instance.[/red]")
                status.remove_class("hidden")
                return

            status.update("Generating authorization link...")
            status.remove_class("hidden")
            auth_url, error = create_app(host)
            if error:
                status.update(f"[red]Error: {error}[/red]")
                return
            
            pyperclip.set_clipboard("xclip")
            pyperclip.copy(auth_url)

            auth_link_input = self.query_one("#auth_link")
            auth_link_input.text = auth_url
            auth_link_input.read_only = True
            self.query_one("#auth_link_container").remove_class("hidden")
            self.query_one("#get_auth").parent.add_class("hidden") # Hide the button's parent container
            self.query_one("#host").disabled = True
            self.query_one("#auth_code").focus()
            status.add_class("hidden")

        elif event.button.id == "login":
            auth_code = self.query_one("#auth_code").value
            host = self.query_one("#host").value
            if not auth_code:
                status.update("[red]Please enter the authorization code.[/red]")
                status.remove_class("hidden")
                return

            status.update("Logging in...")
            status.remove_class("hidden")
            api, error = login(host, auth_code)
            if api:
                self.dismiss(api)
            else:
                status.update(f"[red]Login failed: {error}[/red]")
