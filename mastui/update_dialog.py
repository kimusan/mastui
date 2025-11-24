from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Static
from textual.screen import ModalScreen
from textual.containers import Center


class UpdateAvailableScreen(ModalScreen):
    """Modal dialog shown when a newer version is available."""

    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, current_version: str, latest_version: str, release_url: str, **kwargs):
        super().__init__(**kwargs)
        self.current_version = current_version
        self.latest_version = latest_version
        self.release_url = release_url

    def compose(self):
        with Center():
            with Vertical(id="update-dialog"):
                yield Static("A new version of Mastui is available.")
                yield Static(f"Installed: {self.current_version}", classes="muted")
                yield Static(f"Latest: {self.latest_version}")
                yield Static("Upgrade with: pipx upgrade mastui", classes="muted")
                yield Static(f"Release notes: {self.release_url}", classes="muted")
                with Horizontal(classes="update-actions"):
                    yield Button("Dismiss", id="dismiss", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "dismiss":
            self.dismiss()
