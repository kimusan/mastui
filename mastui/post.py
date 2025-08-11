from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static, TextArea, Input, Switch, Select
from textual.containers import Vertical, Horizontal, Grid
from mastui.utils import LANGUAGE_OPTIONS

class PostScreen(ModalScreen):
    """A modal screen for composing a new post."""

    def compose(self) -> ComposeResult:
        with Grid(id="post_dialog"):
            yield Static("Compose New Post", id="post_title")

            yield TextArea(id="post_content", language="markdown")

            with Horizontal(id="post_options"):
                yield Static("Content Warning:", classes="post_option_label")
                yield Switch(id="cw_switch")
                yield Input(id="cw_input", placeholder="Spoiler text...", disabled=True)

            with Horizontal(id="post_language_container"):
                yield Static("Language:", classes="post_option_label")
                yield Select(LANGUAGE_OPTIONS, id="language_select", value="en")

            with Horizontal(id="post_buttons"):
                yield Button("Post", variant="primary", id="post_button")
                yield Button("Cancel", id="cancel_button")

    def on_mount(self) -> None:
        """Set initial focus."""
        self.query_one("#post_content").focus()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Toggle the content warning input."""
        cw_input = self.query_one("#cw_input")
        if event.value:
            cw_input.disabled = False
            cw_input.focus()
        else:
            cw_input.disabled = True
            cw_input.value = ""

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "post_button":
            content = self.query_one("#post_content").text
            cw_text = self.query_one("#cw_input").value
            language = self.query_one("#language_select").value
            
            if content:
                result = {
                    "content": content,
                    "spoiler_text": cw_text if self.query_one("#cw_switch").value else None,
                    "language": language,
                }
                self.dismiss(result)
            else:
                self.app.notify("Post content cannot be empty.", severity="error")

        elif event.button.id == "cancel_button":
            self.dismiss(None)
