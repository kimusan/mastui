from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.containers import Vertical, Horizontal


class ConfirmDeleteScreen(ModalScreen):
    """Simple yes/no confirmation dialog for deletions."""

    BINDINGS = [("escape", "dismiss(False)", "Cancel")]

    def __init__(self, message: str = "Are you sure you want to delete this post?", **kwargs):
        super().__init__(**kwargs)
        self.message = message

    def compose(self):
        with Vertical(id="confirm-delete-dialog"):
            yield Static(self.message, classes="label")
            with Horizontal(classes="confirm-actions"):
                yield Button("Yes", variant="error", id="confirm-yes")
                yield Button("No", variant="primary", id="confirm-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)
