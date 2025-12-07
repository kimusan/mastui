from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Input, Static, TextArea, Select, Header, Switch
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual import on, events
from textual.css.query import NoMatches
import logging

from mastui.languages import get_language_options, get_default_language_codes
from mastui.utils import VISIBILITY_OPTIONS
from mastui.widgets import PollChoice, RemovePollChoice, PollChoiceMounted
from mastui.autocomplete import AutocompletePanel, ComposerAutocompleteController

log = logging.getLogger(__name__)

class PostScreen(ModalScreen):
    """A modal screen for composing a new post."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel Post"),
    ]

    def __init__(self, max_characters: int = 500, **kwargs):
        super().__init__(**kwargs)
        self.max_characters = max_characters
        self.autocomplete: ComposerAutocompleteController | None = None

    def compose(self):
        with Vertical(id="post_dialog") as d:
            d.border_title = "New Post"
            with VerticalScroll(id="post_content_container"):
                yield TextArea(id="post_content", language="markdown")
                yield AutocompletePanel(id="post_autocomplete")
                with Horizontal(id="post_options"):
                    yield Label("CW:", classes="post_option_label")
                    yield Input(placeholder="Content warning", id="cw_input")
                languages = self.app.config.post_languages or get_default_language_codes()
                language_options = get_language_options(languages)
                default_language = language_options[0][1] if language_options else "en"

                with Horizontal(id="post_language_container"):
                    yield Label("Language:", classes="post_option_label")
                    yield Select(language_options, value=default_language, id="language_select")
                
                with Horizontal(id="post_visibility_container"):
                    yield Label("Visibility:", classes="post_option_label")
                    yield Select(
                        VISIBILITY_OPTIONS,
                        value="public",
                        id="visibility_select",
                    )

                with Horizontal(id="add_poll_container"):
                    yield Label("Add Poll:", classes="post_option_label")
                    yield Switch(id="add_poll_switch")

                with Vertical(id="poll_creation_area", classes="hidden"):
                    yield Label("Poll Choices:")
                    yield Vertical(id="poll_choices_container")
                    yield Button("Add Choice", id="add_choice_button")
                    
                    yield Label("Poll Duration:")
                    yield Select(
                        [
                            ("5 minutes", 300),
                            ("30 minutes", 1800),
                            ("1 hour", 3600),
                            ("6 hours", 21600),
                            ("1 day", 86400),
                            ("3 days", 259200),
                            ("7 days", 604800),
                        ],
                        value=86400,
                        id="poll_duration_select",
                    )

            with Horizontal(id="post_buttons"):
                yield Label(f"{self.max_characters}", id="character_limit")
                yield Button("Post", variant="primary", id="post")
                yield Button("Cancel", id="cancel")

    def on_mount(self):
        self.query_one("#post_content").focus()
        self.update_character_limit()
        self.autocomplete = ComposerAutocompleteController(self, "post_content", "post_autocomplete")
        self.autocomplete.attach()

    def on_unmount(self) -> None:
        if self.autocomplete:
            self.autocomplete.detach()
            self.autocomplete = None

    @on(Switch.Changed, "#add_poll_switch")
    def on_add_poll_switch_changed(self, event: Switch.Changed) -> None:
        """Toggle the poll creation area."""
        poll_area = self.query_one("#poll_creation_area")
        choices_container = self.query_one("#poll_choices_container")
        if event.value:
            poll_area.remove_class("hidden")
            # Add initial choices if none exist
            if not self.query(PollChoice):
                choices_container.mount(PollChoice())
                choices_container.mount(PollChoice())
                self.call_after_refresh(self.update_remove_buttons)
        else:
            poll_area.add_class("hidden")
            for choice in self.query(PollChoice):
                choice.remove()

    @on(Button.Pressed, "#add_choice_button")
    def on_add_choice_button_pressed(self, event: Button.Pressed) -> None:
        """Handle the 'Add Choice' button press."""
        self.query_one("#poll_choices_container").mount(PollChoice())
        self.call_after_refresh(self.update_remove_buttons)

    @on(RemovePollChoice)
    def on_remove_poll_choice(self, message: RemovePollChoice) -> None:
        """Handle the removal of a poll choice."""
        message.poll_choice_widget.remove()
        self.update_remove_buttons()

    @on(PollChoiceMounted)
    def on_poll_choice_mounted(self, message: PollChoiceMounted) -> None:
        """Handle a poll choice being mounted."""
        self.update_remove_buttons()

    def update_remove_buttons(self) -> None:
        """Enable or disable remove buttons based on the number of choices."""
        choices = self.query(PollChoice)
        can_remove = len(choices) > 2
        for choice in choices:
            if choice.remove_button:
                choice.remove_button.disabled = not can_remove

    @on(Input.Changed, "#cw_input")
    def on_cw_changed(self, _: Input.Changed) -> None:
        self.update_character_limit()

    @on(TextArea.Changed, "#post_content")
    def on_post_content_changed(self, _: TextArea.Changed) -> None:
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "post":
            content = self.query_one("#post_content").text
            spoiler_text = self.query_one("#cw_input").value
            language = self.query_one("#language_select").value
            visibility = self.query_one("#visibility_select").value
            
            result = {
                "content": content,
                "spoiler_text": spoiler_text,
                "language": language,
                "visibility": visibility,
                "poll": None,
            }

            if self.query_one("#add_poll_switch").value:
                choices = [
                    choice.query_one(Input).value
                    for choice in self.query(PollChoice)
                ]
                if any(choices): # Only add poll if there are choices
                    result["poll"] = {
                        "options": choices,
                        "expires_in": self.query_one("#poll_duration_select").value,
                    }

            self.dismiss(result)
        elif event.button.id == "cancel":
            self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        if self.autocomplete and self.autocomplete.handle_key(event):
            return
        # Fall back to default handling
        return None
