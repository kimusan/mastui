from textual.screen import ModalScreen
from textual.widgets import Button, Label, Input, TextArea
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual import on, events

from mastui.utils import html_to_plain_text
from mastui.autocomplete import AutocompletePanel, ComposerAutocompleteController

class EditPostScreen(ModalScreen):
    """A modal screen for editing a post."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel Edit"),
    ]

    def __init__(self, status: dict, max_characters: int = 500, **kwargs):
        super().__init__(**kwargs)
        self.status = status
        self.max_characters = max_characters
        self.autocomplete: ComposerAutocompleteController | None = None

    def compose(self):
        with Vertical(id="post_dialog") as d:
            d.border_title = "Edit Post"
            with VerticalScroll(id="post_content_container"):
                yield TextArea(html_to_plain_text(self.status.get('content', '')), id="post_content", language="markdown")
                yield AutocompletePanel(id="edit_autocomplete")
                with Horizontal(id="post_options"):
                    yield Label("CW:", classes="post_option_label")
                    yield Input(
                        value=self.status.get('spoiler_text', ''),
                        placeholder="Content warning", 
                        id="cw_input"
                    )
            with Horizontal(id="post_buttons"):
                yield Label(f"{self.max_characters}", id="character_limit")
                yield Button("Save", variant="primary", id="save_button")
                yield Button("Cancel", id="cancel_button")

    def on_mount(self):
        self.query_one("#post_content").focus()
        self.update_character_limit()
        self.autocomplete = ComposerAutocompleteController(self, "post_content", "edit_autocomplete")
        self.autocomplete.attach()

    def on_unmount(self) -> None:
        if self.autocomplete:
            self.autocomplete.detach()
            self.autocomplete = None

    @on(Input.Changed, "#cw_input")
    def on_cw_changed(self, _: Input.Changed) -> None:
        self.update_character_limit()

    @on(TextArea.Changed, "#post_content")
    def on_content_changed(self, _: TextArea.Changed) -> None:
        self.update_character_limit()
        if self.autocomplete:
            self.autocomplete.on_text_changed()

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
            result = {
                "content": content,
                "spoiler_text": spoiler_text,
            }
            self.dismiss(result)
        elif event.button.id == "cancel_button":
            self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        if self.autocomplete and self.autocomplete.handle_key(event):
            return
        return None
