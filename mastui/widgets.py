import html2text
from textual.widgets import (
    Static,
    LoadingIndicator,
    RadioSet,
    RadioButton,
    Button,
    Input,
    Markdown,
)
from textual.widget import Widget
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual import events, on
from textual.message import Message
from mastui.utils import get_full_content_md, format_datetime, to_markdown
from mastui.reply import ReplyScreen
from mastui.image import ImageWidget
from mastui.messages import SelectPost, VoteOnPoll, ViewHashtag
import logging
from datetime import datetime
from rich.markup import escape as escape_markup

log = logging.getLogger(__name__)


def safe_markup(text: str | None) -> str:
    """Escape user content for Static widgets that render Rich markup."""
    if text is None:
        return ""
    return escape_markup(str(text))


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

    def __init__(self, post_id: str, reblogged: bool):
        super().__init__(post_id)
        self.reblogged = reblogged

class DeletePost(PostMessage):
    """A message to delete a post."""

    pass

class PostDeleted(PostMessage):
    """A message indicating a post was deleted."""

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
        self.remove_button: Button | None = None

    def compose(self):
        yield Input(placeholder="Choice...")
        btn = Button("X", variant="error", classes="remove-choice", disabled=True)
        self.remove_button = btn
        yield btn

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

                is_own_vote = i in self.poll.get("own_votes", [])

                label_prefix = "✓ " if is_own_vote else "  "
                option_title = safe_markup(option.get("title", ""))
                label = f"{label_prefix}{option_title} ({votes} votes, {percentage:.2f}%)"

                bar_color = "green" if is_own_vote else "blue"
                result_bar = Static(f"[{bar_color}] {'█' * int(percentage / 2)} [/]")

                yield Static(label)
                yield result_bar
        else:
            # Show radio buttons to vote
            yield Static("Cast your vote:", classes="poll-header")
            with RadioSet(id="poll-options"):
                for option in self.poll["options"]:
                    yield RadioButton(option["title"])

        # Add the footer with expiry and total votes
        with Horizontal(classes="poll-footer"):
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
            self.post_message(
                VoteOnPoll(
                    self.poll["id"],
                    event.radio_set.pressed_index,
                    self.timeline_id,
                    self.post_id,
                )
            )
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

        # Check for mentions
        try:
            user_id = self.app.me["id"]
            if any(
                mention["id"] == user_id
                for mention in status_to_display.get("mentions", [])
            ):
                self.add_class("mention")
        except Exception as e:
            log.error(f"Could not check for mentions: {e}")

    def compose(self):
        reblog = self.post.get("reblog")
        is_reblog = reblog is not None
        status_to_display = reblog or self.post

        if is_reblog:
            booster_display_name = safe_markup(self.post["account"]["display_name"])
            booster_acct = safe_markup(self.post["account"]["acct"])
            yield Static(
                f"🚀 Boosted by {booster_display_name} (@{booster_acct})",
                classes="boost-header",
            )

        spoiler_text = status_to_display.get("spoiler_text")
        author_display_name = safe_markup(status_to_display["account"]["display_name"])
        author_acct = safe_markup(status_to_display["account"]["acct"])
        author = f"{author_display_name} (@{author_acct})"
        self.border_title = safe_markup(author)
        if spoiler_text:
            self.border_title = safe_markup(spoiler_text)
            self.border_subtitle = author

        yield Markdown(get_full_content_md(status_to_display), open_links=False)

        if status_to_display.get("poll"):
            yield PollWidget(
                status_to_display["poll"],
                timeline_id=self.timeline_id,
                post_id=status_to_display["id"],
            )

        if self.app.config.image_support and status_to_display.get("media_attachments"):
            for media in status_to_display["media_attachments"]:
                if media["type"] == "image":
                    yield ImageWidget(media["url"], self.app.config)

        with Horizontal(classes="post-footer"):
            yield LoadingIndicator(classes="action-spinner")
            yield Static(
                f"Boosts: {status_to_display.get('reblogs_count', 0)}", id="boost-count"
            )
            yield Static(
                f"Likes: {status_to_display.get('favourites_count', 0)}",
                id="like-count",
            )
            yield Static(format_datetime(status_to_display["created_at"]), classes="timestamp")

            visibility_icons = {
                "public": "🌐",
                "unlisted": "🔑",
                "private": "👥",
                "direct": "🔒",
            }
            visibility = status_to_display.get("visibility")
            vis_icon = visibility_icons.get(visibility, "")
            yield Static(vis_icon, classes="visibility-icon")

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

        # Force re-render of the content
        for md in self.query(Markdown):
            md.remove()
        self.mount(Markdown(get_full_content_md(status_to_display), open_links=False), before=self.query_one(".post-footer"))

        # Re-render the poll if it exists
        for poll_widget in self.query(PollWidget):
            poll_widget.remove()
        if status_to_display.get("poll"):
            self.mount(
                PollWidget(
                    status_to_display["poll"],
                    timeline_id=self.timeline_id,
                    post_id=status_to_display["id"],
                ),
                after=self.query_one(".post-footer"),
            )

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.post_message(SelectPost(self))

    @on(Markdown.LinkClicked)
    def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        """Handle a link being clicked in the Markdown."""
        event.stop()
        href = event.href
        # Heuristic to check if the link is a hashtag
        if "/tags/" in href:
            hashtag = href.split("/tags/")[-1].rstrip("/")
            self.post_message(ViewHashtag(hashtag))
            return  # Explicitly stop processing here

        # If it's not a hashtag, open it in the browser
        self.app.action_link_clicked(href)

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
        author_display_name = safe_markup(author.get("display_name", ""))
        author_acct = safe_markup(f"@{author.get('acct', '')}")
        author_str = f"{author_display_name} ({author_acct})"

        created_at = None
        if self.notif["type"] == "mention":
            created_at = self.notif["status"]["created_at"]
        else:
            created_at = self.notif["created_at"]

        if notif_type == "mention":
            status = self.notif["status"]
            spoiler_text = status.get("spoiler_text")

            self.border_title = f"Mention from {author_str}"
            if spoiler_text:
                self.border_title = safe_markup(spoiler_text)
                self.border_subtitle = f"Mention from {author_str}"

            yield Markdown(get_full_content_md(status), open_links=False)
            if self.app.config.image_support and status.get("media_attachments"):
                for media in status["media_attachments"]:
                    if media["type"] == "image":
                        yield ImageWidget(media["url"], self.app.config)
            with Horizontal(classes="post-footer"):
                spinner = LoadingIndicator(classes="action-spinner")
                spinner.display = False
                yield spinner
                yield Static(
                    f"Boosts: {status.get('reblogs_count', 0)}", id="boost-count"
                )
                yield Static(
                    f"Likes: {status.get('favourites_count', 0)}", id="like-count"
                )
                yield Static(format_datetime(created_at), classes="timestamp")

        elif notif_type == "favourite":
            status = self.notif["status"]
            self.border_title = f"❤️ {author_str} favourited your post:"
            yield Markdown(get_full_content_md(status), open_links=False)
            if self.app.config.image_support and status.get("media_attachments"):
                for media in status["media_attachments"]:
                    if media["type"] == "image":
                        yield ImageWidget(media["url"], self.app.config)
            with Horizontal(classes="post-footer"):
                spinner = LoadingIndicator(classes="action-spinner")
                spinner.display = False
                yield spinner
                yield Static(format_datetime(created_at), classes="timestamp")

        elif notif_type == "reblog":
            status = self.notif["status"]
            self.border_title = f"🚀 {author_str} boosted your post:"
            yield Markdown(get_full_content_md(status), open_links=False)
            if self.app.config.image_support and status.get("media_attachments"):
                for media in status["media_attachments"]:
                    if media["type"] == "image":
                        yield ImageWidget(media["url"], self.app.config)
            with Horizontal(classes="post-footer"):
                spinner = LoadingIndicator(classes="action-spinner")
                spinner.display = False
                yield spinner
                yield Static(format_datetime(created_at), classes="timestamp")

        elif notif_type == "follow":
            self.border_title = f"👋 {author_str} followed you."
            with Horizontal(classes="post-footer"):
                yield Static(format_datetime(created_at), classes="timestamp")

        elif notif_type == "poll":
            status = self.notif.get("status")
            if not status:
                self.border_title = "📊 A poll you participated in has ended"
                yield Static("(The original post appears to have been deleted.)")
                with Horizontal(classes="post-footer"):
                    yield Static(format_datetime(created_at), classes="timestamp")
                return

            self.border_title = "📊 A poll you participated in has ended:"
            yield PollWidget(
                status["poll"], timeline_id="notifications", post_id=status["id"]
            )
            with Horizontal(classes="post-footer"):
                spinner = LoadingIndicator(classes="action-spinner")
                spinner.display = False
                yield spinner
                yield Static(format_datetime(created_at), classes="timestamp")
        elif notif_type == "update":
            status = self.notif["status"]
            self.border_title = (
                f"✍️ A post by {author_str} you interacted with was updated"
            )
            self.border_subtitle = f"{author_str}"
            yield Markdown(get_full_content_md(status))
            if self.app.config.image_support and status.get("media_attachments"):
                for media in status["media_attachments"]:
                    if media["type"] == "image":
                        yield ImageWidget(media["url"], self.app.config)
            with Horizontal(classes="post-footer"):
                spinner = LoadingIndicator(classes="action-spinner")
                spinner.display = False
                yield spinner
                yield Static(format_datetime(created_at), classes="timestamp")

        else:
            yield Static(f"Unsupported notification type: {safe_markup(notif_type)}")

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.post_message(SelectPost(self))

    def show_spinner(self):
        try:
            spinner = self.query_one(".action-spinner")
            spinner.display = True
        except Exception as e:
            log.debug(f"Notification spinner not found to show: {e}")

    def hide_spinner(self):
        try:
            spinner = self.query_one(".action-spinner")
            spinner.display = False
        except Exception as e:
            log.debug(f"Notification spinner not found to hide: {e}")

    def update_from_post(self, post):
        """Update notification contents after an action on the underlying status."""
        status = post.get("reblog") or post
        if self.notif.get("status"):
            self.notif["status"] = status

        if self.notif["type"] == "mention":
            self.query_one("#boost-count").update(
                f"Boosts: {status.get('reblogs_count', 0)}"
            )
            self.query_one("#like-count").update(
                f"Likes: {status.get('favourites_count', 0)}"
            )
        self.hide_spinner()

    def get_created_at(self) -> datetime | None:
        """Expose the creation time for timeline sorting and gap detection."""
        created_at = None
        if self.notif["type"] == "mention" and self.notif.get("status"):
            created_at = self.notif["status"].get("created_at")
        else:
            created_at = self.notif.get("created_at")

        if not created_at:
            return None
        if isinstance(created_at, datetime):
            return created_at
        try:
            return datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        except Exception:
            return None

    @on(Markdown.LinkClicked)
    def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        """Handle a link being clicked in the Markdown."""
        event.stop()
        href = event.href
        # Heuristic to check if the link is a hashtag
        if "/tags/" in href:
            hashtag = href.split("/tags/")[-1].rstrip("/")
            self.post_message(ViewHashtag(hashtag))
            return  # Explicitly stop processing here

        # If it's not a hashtag, open it in the browser
        self.app.action_link_clicked(href)


class SearchResult(Widget, can_focus=True):
    """A base class for search results."""

    pass


class AccountResult(SearchResult):
    """A widget to display an account search result."""

    def __init__(self, account: dict, **kwargs):
        super().__init__(**kwargs)
        self.account = account
        self.add_class("search-result")

    def compose(self):
        with Vertical():
            display_name = safe_markup(self.account.get("display_name", ""))
            acct = safe_markup(self.account.get("acct", ""))
            yield Static(
                f"[bold]{display_name}[/bold] @{acct}"
            )
            yield Markdown(to_markdown(self.account["note"]), open_links=False)


class HashtagResult(SearchResult):
    """A widget to display a hashtag search result."""

    def __init__(self, hashtag: dict, **kwargs):
        super().__init__(**kwargs)
        self.hashtag = hashtag
        self.add_class("search-result")

    def compose(self):
        yield Static(f"#{self.hashtag['name']}")
        # You can add more info here, like recent usage stats if available


class StatusResult(SearchResult):
    """A widget to display a status search result."""

    def __init__(self, status: dict, **kwargs):
        super().__init__(**kwargs)
        self.status = status
        self.add_class("search-result")

    def compose(self):
        yield Post(self.status, timeline_id="search")


class ConversationSummary(Widget, can_focus=True):
    """A widget to display a conversation summary."""

    def __init__(self, conversation: dict, **kwargs):
        super().__init__(**kwargs)
        self.conversation = conversation
        self.add_class("timeline-item")
        if conversation.get("unread"):
            self.add_class("unread")

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.post_message(SelectPost(self))

    def compose(self):
        accounts = self.conversation.get("accounts", [])
        last_status = self.conversation.get("last_status")
        is_unread = self.conversation.get("unread")

        # Filter out the current user's account to display others
        other_accounts = [
            acc for acc in accounts if acc["id"] != self.app.me["id"]
        ]
        
        participant_names = ", ".join(
            [f"@{safe_markup(acc.get('acct', ''))}" for acc in other_accounts]
        )
        
        icon = "📩" if is_unread else "📭"
        self.border_title = f"{icon} DM with {participant_names}"

        if last_status:
            snippet = to_markdown(last_status.get("content", ""))
            # Truncate snippet to a reasonable length
            if len(snippet) > 100:
                snippet = snippet[:97] + "..."
            yield Markdown(snippet, open_links=False)
            
            timestamp = format_datetime(last_status.get("created_at"))
            with Horizontal(classes="post-footer"):
                yield Static(format_datetime(last_status.get("created_at")), classes="timestamp")
        else:
            yield Static("No messages yet.")
