from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static, TextArea, Input, Switch, Select, Label, Header, Markdown
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual import on, events

from rich.markup import escape as escape_markup

from mastui.languages import get_language_options, get_default_language_codes
from mastui.utils import get_full_content_md, VISIBILITY_OPTIONS
from mastui.autocomplete import AutocompletePanel, ComposerAutocompleteController

class ReplyScreen(ModalScreen):
    """A modal screen for replying to a post."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel Reply"),
    ]

    def __init__(self, post_to_reply_to: dict, max_characters: int, visibility: str = "public", **kwargs):
        super().__init__(**kwargs)
        self.post_to_reply_to = post_to_reply_to
        self.max_characters = max_characters
        self.visibility = visibility
        self.autocomplete: ComposerAutocompleteController | None = None

    def get_mentions(self):
        """Get all unique mentions from the post being replied to, excluding the current user."""
        # Start with the author of the post
        mentions = {f"@{self.post_to_reply_to['account']['acct']}"}

        # Add all mentioned users
        for mention in self.post_to_reply_to.get('mentions', []):
            mentions.add(f"@{mention['acct']}")

        # Remove the current user's own handle
        my_acct = f"@{self.app.me['acct']}"
        mentions.discard(my_acct)

        return " ".join(sorted(list(mentions)))

    def compose(self) -> ComposeResult:
        with Vertical(id="reply_dialog") as d:
            d.border_title = "Reply to Post"
            with VerticalScroll(id="reply_content_container"):
                with Vertical(id="original_post_preview") as v:
                    acct = escape_markup(self.post_to_reply_to['account']['acct'])
                    v.border_title = f"Replying to @{acct}"
                    yield Markdown(get_full_content_md(self.post_to_reply_to))
                reply_text_area = TextArea(id="reply_content", language="markdown")
                reply_text_area.text = self.get_mentions() + " "
                yield reply_text_area
                yield AutocompletePanel(id="reply_autocomplete")
                with Horizontal(id="reply_options"):
                    yield Static("Content Warning:", classes="reply_option_label")
                    yield Switch(id="cw_switch")
                    yield Input(id="cw_input", placeholder="Spoiler text...", disabled=True)
                language_source = self.post_to_reply_to.get("language")
                preferred = self.app.config.post_languages or get_default_language_codes()
                language_options = get_language_options(
                    preferred, extra_codes=[language_source] if language_source else None
                )
                default_language = language_source or (language_options[0][1] if language_options else "en")

                with Horizontal(id="reply_language_container"):
                    yield Static("Language:", classes="reply_option_label")
                    yield Select(language_options, id="language_select", value=default_language)
                with Horizontal(id="reply_visibility_container"):
                    yield Static("Visibility:", classes="reply_option_label")
                    yield Select(
                        VISIBILITY_OPTIONS,
                        value=self.visibility,
                        id="visibility_select",
                    )
            with Horizontal(id="reply_buttons"):
                yield Label(f"{self.max_characters}", id="character_limit")
                yield Button("Post Reply", variant="primary", id="post_button")
                yield Button("Cancel", id="cancel_button")

    def on_mount(self) -> None:
        """Set initial focus."""
        self.query_one("#reply_content").focus()
        self.query_one("#reply_content").cursor_location = (0, len(self.query_one("#reply_content").text))
        self.update_character_limit()
        self.autocomplete = ComposerAutocompleteController(self, "reply_content", "reply_autocomplete")
        self.autocomplete.attach()

    def on_unmount(self) -> None:
        if self.autocomplete:
            self.autocomplete.detach()
            self.autocomplete = None

    @on(Input.Changed, "#cw_input")
    def on_cw_text_changed(self, _: Input.Changed) -> None:
        self.update_character_limit()

    @on(TextArea.Changed, "#reply_content")
    def on_reply_content_changed(self, _: TextArea.Changed) -> None:
        self.update_character_limit()
        if self.autocomplete:
            self.autocomplete.on_text_changed()

    def update_character_limit(self) -> None:
        """Update the character count."""
        content_len = len(self.query_one("#reply_content").text)
        cw_len = len(self.query_one("#cw_input").value)
        remaining = self.max_characters - content_len - cw_len
        
        limit_label = self.query_one("#character_limit")
        limit_label.update(f"{remaining}")
        limit_label.set_class(remaining < 0, "character-limit-error")
        self.query_one("#post_button").disabled = remaining < 0 or remaining == self.max_characters

    @on(Switch.Changed, "#cw_switch")
    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Toggle the content warning input."""
        cw_input = self.query_one("#cw_input")
        if event.value:
            cw_input.disabled = False
            cw_input.focus()
        else:
            cw_input.disabled = True
            cw_input.value = ""

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "post_button":
            content = self.query_one("#reply_content").text
            cw_text = self.query_one("#cw_input").value
            language = self.query_one("#language_select").value
            visibility = self.query_one("#visibility_select").value
            
            if content:
                result = {
                    "content": content,
                    "spoiler_text": cw_text if self.query_one("#cw_switch").value else None,
                    "language": language,
                    "visibility": visibility,
                    "in_reply_to_id": self.post_to_reply_to['id']
                }
                self.dismiss(result)
            else:
                self.app.notify("Reply content cannot be empty.", severity="error")

        elif event.button.id == "cancel_button":
            self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        if self.autocomplete and self.autocomplete.handle_key(event):
            return
        return None
