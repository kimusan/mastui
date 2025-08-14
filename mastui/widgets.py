import html2text
from textual.widgets import Static, LoadingIndicator
from textual.widget import Widget
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.events import Key
from textual.message import Message
from mastui.utils import get_full_content_md, format_datetime
from mastui.reply import ReplyScreen
from mastui.image import ImageWidget
from mastui.config import config
import logging

log = logging.getLogger(__name__)


class PostMessage(Message):
    """A message relating to a post."""

    def __init__(self, post_id: str) -> None:
        self.post_id = post_id
        super().__init__()


class LikePost(PostMessage):
    """A message to like a post."""

    pass


class BoostPost(PostMessage):
    """A message to boost a post."""

    pass


class Post(Widget):
    """A widget to display a single post."""

    def __init__(self, post, **kwargs):
        super().__init__(**kwargs)
        self.post = post
        self.add_class("timeline-item")
        status_to_display = self.post.get("reblog") or self.post
        self.created_at_str = format_datetime(status_to_display['created_at'])

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
            yield Static(f"🚀 Boosted by {booster_display_name} (@{booster_acct})", classes="boost-header")

        spoiler_text = status_to_display.get("spoiler_text")
        author_display_name = status_to_display['account']['display_name']
        author_acct = status_to_display['account']['acct']
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
                f"Likes: {status_to_display.get('favourites_count', 0)}", id="like-count"
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


class Notification(Widget):
    """A widget to display a single notification."""

    def __init__(self, notif, **kwargs):
        super().__init__(**kwargs)
        self.notif = notif
        self.add_class("timeline-item")
        
        created_at = None
        if self.notif['type'] == 'mention':
            created_at = self.notif['status']['created_at']
        else:
            created_at = self.notif['created_at']
        self.created_at_str = format_datetime(created_at)

    def compose(self):
        notif_type = self.notif["type"]
        author = self.notif["account"]
        author_display_name = author['display_name']
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
                title = option.get('title', 'N/A')
                votes = option.get('votes_count', 0)
                percentage = (votes / total_votes * 100) if total_votes > 0 else 0
                yield Static(f"  - {title}: {votes} votes ({percentage:.2f}%)")
            with Horizontal(classes="post-footer"):
                yield Static(self.created_at_str, classes="timestamp")

        else:
            yield Static(f"Unsupported notification type: {notif_type}")
