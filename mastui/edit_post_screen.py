from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Input, Static, TextArea, Select, Header
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual import on
from mastui.utils import LANGUAGE_OPTIONS, html_to_plain_text

class EditPostScreen(ModalScreen):
    """A modal screen for editing a post."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel Edit"),
    ]

    def __init__(self, status: dict, max_characters: int = 500, **kwargs):
        super().__init__(**kwargs)
        self.status = status
        self.max_characters = max_characters

    def compose(self):
        with Vertical(id="post_dialog") as d:
            d.border_title = "Edit Post"
            with VerticalScroll(id="post_content_container"):
                yield TextArea(html_to_plain_text(self.status.get('content', '')), id="post_content", language="markdown")
                with Horizontal(id="post_options"):
                    yield Label("CW:", classes="post_option_label")
                    yield Input(
                        value=self.status.get('spoiler_text', ''),
                        placeholder="Content warning", 
                        id="cw_input"
                    )
                with Horizontal(id="post_language_container"):
                    yield Label("Language:", classes="post_option_label")
                    yield Select(
                        LANGUAGE_OPTIONS, 
                        value=self.status.get('language', 'en'), 
                        id="language_select"
                    )
            with Horizontal(id="post_buttons"):
                yield Label(f"{self.max_characters}", id="character_limit")
                yield Button("Save", variant="primary", id="save_button")
                yield Button("Cancel", id="cancel_button")

    def on_mount(self):
        self.query_one("#post_content").focus()
        self.update_character_limit()

    @on(Input.Changed)
    @on(TextArea.Changed)
    def update_character_limit(self):
        """Updates the character limit."""
        content_len = len(self.query_one("#post_content").text)
        cw_len = len(self.query_one("#cw_input").value)
        remaining = self.max_characters - content_len - cw_len
        
        limit_label = self.query_one("#character_limit")
        limit_label.update(f"{remaining}")
        limit_label.set_class(remaining < 0, "character-limit-error")

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_button":
            content = self.query_one("#post_content").text
            spoiler_text = self.query_one("#cw_input").value
            language = self.query_one("#language_select").value
            
            result = {
                "content": content,
                "spoiler_text": spoiler_text,
                "language": language,
            }
            self.dismiss(result)
        elif event.button.id == "cancel_button":
            self.dismiss(None)
