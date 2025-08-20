from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static, TextArea, Input, Switch, Select, Label, Header
from textual.containers import Vertical, Horizontal, Grid, VerticalScroll
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box
from textual import on
from mastui.utils import get_full_content_md, LANGUAGE_OPTIONS

class ReplyScreen(ModalScreen):
    """A modal screen for replying to a post."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel Reply"),
    ]

    def __init__(self, post_to_reply_to, max_characters: int = 500, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.post_to_reply_to = post_to_reply_to
        self.max_characters = max_characters

    def get_mentions(self):
        """Get mentions from the post being replied to."""
        mentions = {f"@{self.post_to_reply_to['account']['acct']}"}
        for mention in self.post_to_reply_to.get('mentions', []):
            mentions.add(f"@{mention['acct']}")
        return " ".join(sorted(list(mentions)))

    def compose(self) -> ComposeResult:
        self.title = "Reply to Post"
        with Vertical(id="reply_dialog"):
            yield Header(show_clock=False)
            with VerticalScroll(id="reply_content_container"):
                yield Static(
                    Panel(
                        Markdown(get_full_content_md(self.post_to_reply_to)),
                        title=f"Replying to @{self.post_to_reply_to['account']['acct']}",
                        box=box.ROUNDED,
                        padding=(0, 1),
                    ),
                    id="original_post_preview"
                )
                reply_text_area = TextArea(id="reply_content", language="markdown")
                reply_text_area.text = self.get_mentions() + " "
                yield reply_text_area
                with Horizontal(id="reply_options"):
                    yield Static("Content Warning:", classes="reply_option_label")
                    yield Switch(id="cw_switch")
                    yield Input(id="cw_input", placeholder="Spoiler text...", disabled=True)
                with Horizontal(id="reply_language_container"):
                    yield Static("Language:", classes="reply_option_label")
                    yield Select(LANGUAGE_OPTIONS, id="language_select", value="en")
            with Horizontal(id="reply_buttons"):
                yield Label(f"{self.max_characters}", id="character_limit")
                yield Button("Post Reply", variant="primary", id="post_button")
                yield Button("Cancel", id="cancel_button")

    def on_mount(self) -> None:
        """Set initial focus."""
        self.query_one("#reply_content").focus()
        self.query_one("#reply_content").cursor_location = (0, len(self.query_one("#reply_content").text))
        self.update_character_limit()

    @on(Input.Changed)
    @on(TextArea.Changed)
    def update_character_limit(self):
        """Updates the character limit."""
        content_len = len(self.query_one("#reply_content").text)
        cw_len = len(self.query_one("#cw_input").value)
        remaining = self.max_characters - content_len - cw_len
        
        limit_label = self.query_one("#character_limit")
        limit_label.update(f"{remaining}")
        limit_label.set_class(remaining < 0, "character-limit-error")

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
            content = self.query_one("#reply_content").text
            cw_text = self.query_one("#cw_input").value
            language = self.query_one("#language_select").value
            
            if content:
                result = {
                    "content": content,
                    "spoiler_text": cw_text if self.query_one("#cw_switch").value else None,
                    "language": language,
                    "in_reply_to_id": self.post_to_reply_to['id']
                }
                self.dismiss(result)
            else:
                self.app.notify("Reply content cannot be empty.", severity="error")

        elif event.button.id == "cancel_button":
            self.dismiss(None)
