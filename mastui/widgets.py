import html2text
from textual.widgets import Static, LoadingIndicator, RadioSet, RadioButton, Button, Input
from textual.widget import Widget
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual import events, on
from textual.message import Message
from mastui.utils import get_full_content_md, format_datetime
from mastui.reply import ReplyScreen
from mastui.image import ImageWidget
from mastui.config import config
from mastui.messages import SelectPost, VoteOnPoll
import logging
from datetime import datetime

log = logging.getLogger(__name__)


class PostMessage(Message):
    """A message relating to a post."""

    def __init__(self, post_id: str) -> None:
        self.post_id = post_id
        super().__init__()


class LikePost(PostMessage):
    """A message to like a post."""

    def __init__(self, post_id: str, favourited: bool):
        super().__init__(post_id)
        self.favourited = favourited


class BoostPost(PostMessage):
    """A message to boost a post."""

    pass


class RemovePollChoice(Message):
    """A message to remove a poll choice."""
    def __init__(self, poll_choice_widget: Widget) -> None:
        self.poll_choice_widget = poll_choice_widget
        super().__init__()


class PollChoiceMounted(Message):
    """A message to indicate that a poll choice has been mounted."""
    pass


class PollChoice(Horizontal):
    """A widget for a single poll choice."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_class("poll-choice")

    def compose(self):
        yield Input(placeholder="Choice...")
        yield Button("X", variant="error", classes="remove-choice", disabled=True)

    def on_mount(self) -> None:
        """When the widget is mounted, tell the parent to check button states."""
        self.post_message(PollChoiceMounted())

    @on(Button.Pressed, ".remove-choice")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(RemovePollChoice(self))


class PollWidget(Vertical):
    """A widget to display a poll."""

    def __init__(self, poll: dict, timeline_id: str, post_id: str, **kwargs):
        super().__init__(**kwargs)
        self.poll = poll
        self.timeline_id = timeline_id
        self.post_id = post_id
        self.add_class("poll-container")
        self.styles.height = "auto"

    def compose(self):
        # The PollWidget itself acts as a vertical container for its children.
        if self.poll.get("voted") or self.poll.get("expired"):
            # Show results
            total_votes = self.poll.get("votes_count", 0)
            yield Static("Poll Results:", classes="poll-header")
            for i, option in enumerate(self.poll["options"]):
                votes = option.get("votes_count", 0)
                percentage = (votes / total_votes * 100) if total_votes > 0 else 0
                
                is_own_vote = i in self.poll.get('own_votes', [])
                
                label_prefix = "✓ " if is_own_vote else "  "
                label = f"{label_prefix}{option['title']} ({votes} votes, {percentage:.2f}%)"
                
                bar_color = "green" if is_own_vote else "blue"
                result_bar = Static(f"[{bar_color}] {'█' * int(percentage / 2)} [/]")
                
                yield Static(label)
                yield result_bar
        else:
            # Show radio buttons to vote
            yield Static("Cast your vote:", classes="poll-header")
            with RadioSet(id="poll-options") as rs:
                for option in self.poll["options"]:
                    yield RadioButton(option["title"])

        # Add the footer with expiry and total votes
        with Horizontal(classes="poll-footer") as h:
            h.styles.height = "auto"
            total_votes = self.poll.get("votes_count", 0)
            yield Static(f"{total_votes} votes", classes="poll-total-votes")

            expires_at = self.poll.get("expires_at")
            if expires_at:
                expiry_str = format_datetime(expires_at)
                status_text = "Expired" if self.poll.get("expired") else "Expires"
                yield Static(f"{status_text}: {expiry_str}", classes="poll-expiry")

    @on(RadioSet.Changed)
    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle a vote."""
        if event.radio_set.pressed_index is not None:
            # Check if already voted, just in case
            if self.poll.get("voted"):
                return
            self.post_message(VoteOnPoll(self.poll["id"], event.radio_set.pressed_index, self.timeline_id, self.post_id))
            # Disable the radio set to prevent re-voting
            event.radio_set.disabled = True


class Post(Vertical):
    """A widget to display a single post."""

    def __init__(self, post, timeline_id: str, **kwargs):
        super().__init__(**kwargs)
        self.post = post
        self.timeline_id = timeline_id
        self.add_class("timeline-item")
        status_to_display = self.post.get("reblog") or self.post
        self.created_at_str = format_datetime(status_to_display["created_at"])

    def on_mount(self):
        status_to_display = self.post.get("reblog") or self.post
        if status_to_display.get("favourited"):
            self.add_class("favourited")
        if status_to_display.get("reblogged"):
            self.add_class("reblogged")

    def compose(self):
        reblog = self.post.get("reblog")
        is_reblog = reblog is not None
        status_to_display = reblog or self.post

        if is_reblog:
            booster_display_name = self.post["account"]["display_name"]
            booster_acct = self.post["account"]["acct"]
            yield Static(
                f"🚀 Boosted by {booster_display_name} (@{booster_acct})",
                classes="boost-header",
            )

        spoiler_text = status_to_display.get("spoiler_text")
        author_display_name = status_to_display["account"]["display_name"]
        author_acct = status_to_display["account"]["acct"]
        author = f"{author_display_name} (@{author_acct})"

        panel_title = author
        panel_subtitle = ""

        if spoiler_text:
            panel_title = spoiler_text
            panel_subtitle = author

        yield Static(
            Panel(
                Markdown(get_full_content_md(status_to_display)),
                title=panel_title,
                subtitle=panel_subtitle,
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )
        if status_to_display.get("poll"):
            yield PollWidget(status_to_display["poll"], timeline_id=self.timeline_id, post_id=status_to_display["id"])
            
        if config.image_support and status_to_display.get("media_attachments"):
            for media in status_to_display["media_attachments"]:
                if media["type"] == "image":
                    yield ImageWidget(media["url"], config.image_renderer)

        with Horizontal(classes="post-footer"):
            yield LoadingIndicator(classes="action-spinner")
            yield Static(
                f"Boosts: {status_to_display.get('reblogs_count', 0)}", id="boost-count"
            )
            yield Static(
                f"Likes: {status_to_display.get('favourites_count', 0)}",
                id="like-count",
            )
            yield Static(self.created_at_str, classes="timestamp")

    def show_spinner(self):
        self.query_one(".action-spinner").display = True

    def hide_spinner(self):
        self.query_one(".action-spinner").display = False

    def update_from_post(self, post):
        self.post = post
        status_to_display = self.post.get("reblog") or self.post
        
        # Update classes
        self.remove_class("favourited", "reblogged")
        if status_to_display.get("favourited"):
            self.add_class("favourited")
        if status_to_display.get("reblogged"):
            self.add_class("reblogged")

        # Update stats
        self.query_one("#boost-count").update(
            f"Boosts: {status_to_display.get('reblogs_count', 0)}"
        )
        self.query_one("#like-count").update(
            f"Likes: {status_to_display.get('favourites_count', 0)}"
        )
        self.hide_spinner()

        # Re-render the poll if it exists
        for poll_widget in self.query(PollWidget):
            poll_widget.remove()
        if status_to_display.get("poll"):
            self.mount(PollWidget(status_to_display["poll"], timeline_id=self.timeline_id, post_id=status_to_display["id"]), after=self.query_one(".post-footer"))

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.post_message(SelectPost(self))

    def get_created_at(self) -> datetime | None:
        status = self.post.get("reblog") or self.post
        if status and "created_at" in status:
            ts = status["created_at"]
            if isinstance(ts, datetime):
                return ts
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return None


class GapIndicator(Widget):
    """A widget to indicate a gap in the timeline."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_class("gap-indicator")

    def compose(self):
        yield Static("...")


class Notification(Widget):
    """A widget to display a single notification."""

    def __init__(self, notif, **kwargs):
        super().__init__(**kwargs)
        self.notif = notif
        self.add_class("timeline-item")

        created_at = None
        if self.notif["type"] == "mention":
            created_at = self.notif["status"]["created_at"]
        else:
            created_at = self.notif["created_at"]
        self.created_at_str = format_datetime(created_at)

    def compose(self):
        notif_type = self.notif["type"]
        author = self.notif["account"]
        author_display_name = author["display_name"]
        author_acct = f"@{author['acct']}"
        author_str = f"{author_display_name} ({author_acct})"

        if notif_type == "mention":
            status = self.notif["status"]
            spoiler_text = status.get("spoiler_text")
            panel_title = f"Mention from {author_str}"
            panel_subtitle = ""
            if spoiler_text:
                panel_title = spoiler_text
                panel_subtitle = f"Mention from {author_str}"

            yield Static(
                Panel(
                    Markdown(get_full_content_md(status)),
                    title=panel_title,
                    subtitle=panel_subtitle,
                    box=box.ROUNDED,
                    padding=(0, 1),
                )
            )
            with Horizontal(classes="post-footer"):
                yield Static(
                    f"Boosts: {status.get('reblogs_count', 0)}", id="boost-count"
                )
                yield Static(
                    f"Likes: {status.get('favourites_count', 0)}", id="like-count"
                )
                yield Static(self.created_at_str, classes="timestamp")

        elif notif_type == "favourite":
            status = self.notif["status"]
            yield Static(f"❤️ {author_str} favourited your post:")
            yield Static(
                Panel(
                    Markdown(get_full_content_md(status)),
                    box=box.ROUNDED,
                    padding=(0, 1),
                )
            )
            with Horizontal(classes="post-footer"):
                yield Static(self.created_at_str, classes="timestamp")

        elif notif_type == "reblog":
            status = self.notif["status"]
            yield Static(f"🚀 {author_str} boosted your post:")
            yield Static(
                Panel(
                    Markdown(get_full_content_md(status)),
                    box=box.ROUNDED,
                    padding=(0, 1),
                )
            )
            with Horizontal(classes="post-footer"):
                yield Static(self.created_at_str, classes="timestamp")

        elif notif_type == "follow":
            yield Static(f"👋 {author_str} followed you.")
            with Horizontal(classes="post-footer"):
                yield Static(self.created_at_str, classes="timestamp")

        elif notif_type == "poll":
            status = self.notif["status"]
            poll = status.get("poll", {})
            options = poll.get("options", [])
            total_votes = poll.get("votes_count", 0)

            yield Static("📊 A poll you participated in has ended:")

            for option in options:
                title = option.get("title", "N/A")
                votes = option.get("votes_count", 0)
                percentage = (votes / total_votes * 100) if total_votes > 0 else 0
                yield Static(f"  - {title}: {votes} votes ({percentage:.2f}%)")
            with Horizontal(classes="post-footer"):
                yield Static(self.created_at_str, classes="timestamp")

        else:
            yield Static(f"Unsupported notification type: {notif_type}")

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.post_message(SelectPost(self))

    def get_created_at(self) -> datetime | None:
        ts_str = None
        if self.notif["type"] == "mention":
            ts_str = self.notif.get("status", {}).get("created_at")
        else:
            ts_str = self.notif.get("created_at")

        if ts_str:
            if isinstance(ts_str, datetime):
                return ts_str
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return None


class GapIndicator(Widget):
    """A widget to indicate a gap in the timeline."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_class("gap-indicator")

    def compose(self):
        yield Static("...")
