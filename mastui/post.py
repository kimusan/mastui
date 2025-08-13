from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Input, Static, TextArea, Select
from textual.containers import Grid, Horizontal
from textual import on
from mastui.utils import LANGUAGE_OPTIONS

class PostScreen(ModalScreen):
    """A modal screen for composing a new post."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel Post"),
    ]

    DEFAULT_CSS = """
    PostScreen {
        align: center middle;
    }
    """

    def __init__(self, max_characters: int = 500, **kwargs):
        super().__init__(**kwargs)
        self.max_characters = max_characters

    def compose(self):
        with Grid(id="post_dialog"):
            yield Label("New Post", id="post_title")
            yield TextArea(id="post_content", language="markdown")
            
            with Horizontal(id="post_options"):
                yield Label("CW:", classes="post_option_label")
                yield Input(placeholder="Content warning", id="cw_input")
            
            with Horizontal(id="post_language_container"):
                yield Label("Language:", classes="post_option_label")
                yield Select(LANGUAGE_OPTIONS, value="en", id="language_select")

            with Horizontal(id="post_buttons"):
                yield Label(f"{self.max_characters}", id="character_limit")
                yield Button("Post", variant="primary", id="post")
                yield Button("Cancel", id="cancel")

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "post":
            content = self.query_one("#post_content").text
            spoiler_text = self.query_one("#cw_input").value
            language = self.query_one("#language_select").value
            self.dismiss({
                "content": content,
                "spoiler_text": spoiler_text,
                "language": language
            })
        else:
            self.dismiss(None)
