import clipman
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical
from textual.widgets import Button, Label, Input, Static, TextArea, LoadingIndicator, Header
from textual.screen import ModalScreen

from mastui.mastodon_api import login, create_app


class LoginScreen(ModalScreen):
    """Screen for user to login."""

    def compose(self) -> ComposeResult:
        self.title = "Mastui Login"
        with Grid(id="dialog"):
            yield Header(show_clock=False)
            yield Label("Mastodon Instance:")
            yield Input(placeholder="mastodon.social", id="host")

            yield Static()  # Spacer
            yield Button("Get Auth Link", variant="primary", id="get_auth")

            yield LoadingIndicator(classes="hidden")
            yield Static(id="status", classes="hidden")

            with Vertical(id="auth_link_container", classes="hidden"):
                yield Static(
                    "1. Link copied to clipboard! Open it in your browser to authorize."
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

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        status = self.query_one("#status")
        spinner = self.query_one(LoadingIndicator)

        if event.button.id == "get_auth":
            host = self.query_one("#host").value
            if not host:
                status.update("[red]Please enter a Mastodon instance.[/red]")
                status.remove_class("hidden")
                return

            spinner.remove_class("hidden")
            status.add_class("hidden")
            self.run_worker(
                lambda: self.app.call_from_thread(
                    self.on_auth_link_created, create_app(host)
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
        auth_url, error = result
        status = self.query_one("#status")
        spinner = self.query_one(LoadingIndicator)
        spinner.add_class("hidden")

        if error:
            status.update(f"[red]Error: {error}[/red]")
            status.remove_class("hidden")
            return

        try:
            clipman.init()
            clipman.set(auth_url)
            self.query_one("#auth_link_container > Static").update(
                "1. Link copied to clipboard! Open it in your browser to authorize."
            )
        except clipman.exceptions.ClipmanBaseException:
            self.query_one("#auth_link_container > Static").update(
                "1. Could not copy to clipboard. Please copy the link below manually:"
            )

        auth_link_input = self.query_one("#auth_link")
        auth_link_input.text = auth_url
        auth_link_input.read_only = True
        self.query_one("#auth_link_container").remove_class("hidden")
        self.query_one("#get_auth").parent.add_class(
            "hidden"
        )  # Hide the button's parent container
        self.query_one("#host").disabled = True
        self.query_one("#auth_code").focus()

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
