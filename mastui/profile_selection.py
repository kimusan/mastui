from textual.screen import ModalScreen
from textual.widgets import Button, Select, Static
from textual.containers import Vertical
from mastui.logo import LogoWidget

class ProfileSelectionScreen(ModalScreen):
    """A modal screen for selecting a profile."""

    BINDINGS = [("escape", "dismiss", "Dismiss")]

    def __init__(self, profiles: list[str], **kwargs):
        super().__init__(**kwargs)
        self.profiles = profiles

    def compose(self):
        with Vertical(id="profile-selection-dialog"):
            yield LogoWidget()
            yield Static("Select a profile to continue:", classes="label")
            yield Select([(p, p) for p in self.profiles], id="profile-select")
            yield Button("Login", variant="primary", id="login-button")
            yield Button("Add New Profile", id="add-profile-button")

    def on_mount(self) -> None:
        # Auto-focus the select widget if there are profiles
        if self.profiles:
            self.query_one("#profile-select").focus()
        else:
            self.query_one("#add-profile-button").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login-button":
            selected_profile = self.query_one("#profile-select").value
            if selected_profile:
                self.dismiss(selected_profile)
        elif event.button.id == "add-profile-button":
            self.dismiss("add_new_profile")
