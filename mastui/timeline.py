import html2text
from textual.widgets import Static, LoadingIndicator
from textual.widget import Widget
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.events import Key
from textual.message import Message
from mastui.utils import get_full_content_md
from mastui.reply import ReplyScreen


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
            booster_name = self.post["account"]["acct"]
            yield Static(f"🚀 Boosted by @{booster_name}", classes="boost-header")

        spoiler_text = status_to_display.get("spoiler_text")
        author = f"@{status_to_display['account']['acct']}"

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
        with Horizontal(classes="post-footer"):
            yield Static(
                f"Boosts: {status_to_display.get('reblogs_count', 0)}", id="boost-count"
            )
            yield Static(
                f"Likes: {status_to_display.get('favourites_count', 0)}", id="like-count"
            )

    def update_stats(self):
        status_to_display = self.post.get("reblog") or self.post
        self.query_one("#boost-count").update(
            f"Boosts: {status_to_display.get('reblogs_count', 0)}"
        )
        self.query_one("#like-count").update(
            f"Likes: {status_to_display.get('favourites_count', 0)}"
        )


class Notification(Widget):
    """A widget to display a single notification."""

    def __init__(self, notif, **kwargs):
        super().__init__(**kwargs)
        self.notif = notif
        self.add_class("timeline-item")

    def compose(self):
        notif_type = self.notif["type"]
        author = self.notif["account"]
        author_acct = f"@{author['acct']}"

        if notif_type == "mention":
            status = self.notif["status"]
            spoiler_text = status.get("spoiler_text")
            panel_title = f"Mention from {author_acct}"
            panel_subtitle = ""
            if spoiler_text:
                panel_title = spoiler_text
                panel_subtitle = f"Mention from {author_acct}"

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

        elif notif_type == "favourite":
            status = self.notif["status"]
            yield Static(f"❤️ {author_acct} favourited your post:")
            yield Static(
                Panel(
                    Markdown(get_full_content_md(status)),
                    box=box.ROUNDED,
                    padding=(0, 1),
                )
            )

        elif notif_type == "reblog":
            status = self.notif["status"]
            yield Static(f"🚀 {author_acct} boosted your post:")
            yield Static(
                Panel(
                    Markdown(get_full_content_md(status)),
                    box=box.ROUNDED,
                    padding=(0, 1),
                )
            )

        elif notif_type == "follow":
            yield Static(f"👋 {author_acct} followed you.")

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

        else:
            yield Static(f"Unsupported notification type: {notif_type}")


class Timeline(Static, can_focus=True):
    """A widget to display a single timeline."""

    def __init__(self, title, posts_data=None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.posts_data = posts_data
        self.selected_item = None
        self.post_ids = set()

    @property
    def content_container(self) -> VerticalScroll:
        return self.query_one(".timeline-content", VerticalScroll)

    @property
    def loading_indicator(self) -> LoadingIndicator:
        return self.query_one(LoadingIndicator)

    def on_mount(self):
        if self.posts_data is not None:
            self.render_posts(self.posts_data)
        else:
            self.app.call_later(self.load_posts)

    def load_posts(self):
        self.loading_indicator.display = True
        self.content_container.display = False
        
        api = self.app.api
        posts = []
        if api:
            try:
                if self.id == "home":
                    posts = api.timeline_home()
                elif self.id == "notifications":
                    posts = api.notifications()
                elif self.id == "federated":
                    posts = api.timeline_public()
            except Exception as e:
                self.content_container.mount(
                    Static(f"[red]Error: {e}[/red]", classes="status-message")
                )
        
        self.render_posts(posts)

    def render_posts(self, posts_data):
        """Renders the given posts data in the timeline."""
        is_initial_load = not self.post_ids

        if is_initial_load:
            # Clear any existing messages
            for item in self.content_container.query(".status-message"):
                item.remove()

        new_posts_mounted = False

        # On refresh, we prepend so we reverse.
        # On initial load, we append, so no reverse.
        post_iterator = reversed(posts_data) if not is_initial_load else posts_data

        for post in post_iterator:
            if post["id"] not in self.post_ids:
                new_posts_mounted = True
                self.post_ids.add(post["id"])

                widget_to_mount = None
                if self.id == "home" or self.id == "federated":
                    widget_to_mount = Post(post)
                elif self.id == "notifications":
                    widget_to_mount = Notification(post)

                if widget_to_mount:
                    if is_initial_load:
                        self.content_container.mount(widget_to_mount)
                    else:
                        self.content_container.mount(widget_to_mount, before=0)

        if is_initial_load and not posts_data:
            if self.id == "home" or self.id == "federated":
                self.content_container.mount(Static(f"{self.title} timeline is empty.", classes="status-message"))
            elif self.id == "notifications":
                self.content_container.mount(Static("No new notifications.", classes="status-message"))

        self.loading_indicator.display = False
        self.content_container.display = True

        if new_posts_mounted or self.selected_item is None:
            self.select_first_item()

    def on_focus(self):
        self.select_first_item()

    def on_blur(self):
        if self.selected_item:
            self.selected_item.remove_class("selected")

    def on_key(self, event: Key) -> None:
        if event.key == "tab":
            return
        if event.key == "down":
            self.scroll_down()
            event.stop()
        elif event.key == "up":
            self.scroll_up()
            event.stop()
        elif event.key == "l":
            self.like_post()
            event.stop()
        elif event.key == "b":
            self.boost_post()
            event.stop()
        elif event.key == "a":
            self.reply_to_post()
            event.stop()

    def select_first_item(self):
        if self.selected_item:
            self.selected_item.remove_class("selected")
        try:
            self.selected_item = self.content_container.query(
                "Post, Notification"
            ).first()
            self.selected_item.add_class("selected")
        except Exception:
            self.selected_item = None

    def get_selected_item(self):
        return self.selected_item

    def reply_to_post(self):
        post_to_reply_to = None
        if isinstance(self.selected_item, Post):
            post_to_reply_to = self.selected_item.post.get("reblog") or self.selected_item.post
        elif isinstance(self.selected_item, Notification):
            if self.selected_item.notif["type"] == "mention":
                post_to_reply_to = self.selected_item.notif.get("status")

        if post_to_reply_to:
            self.app.push_screen(ReplyScreen(post_to_reply_to), self.app.on_reply_screen_dismiss)
        else:
            self.app.notify("This item cannot be replied to.", severity="error")

    def like_post(self):
        if isinstance(self.selected_item, Post):
            status_to_action = self.selected_item.post.get("reblog") or self.selected_item.post
            if not status_to_action:
                self.app.notify("Cannot like a post that has been deleted.", severity="error")
                return
            self.post_message(LikePost(status_to_action["id"]))

    def boost_post(self):
        if isinstance(self.selected_item, Post):
            status_to_action = self.selected_item.post.get("reblog") or self.selected_item.post
            if not status_to_action:
                self.app.notify("Cannot boost a post that has been deleted.", severity="error")
                return
            self.post_message(BoostPost(status_to_action["id"]))

    def scroll_up(self):
        items = self.content_container.query("Post, Notification")
        if self.selected_item and items:
            try:
                idx = items.nodes.index(self.selected_item)
                if idx > 0:
                    self.selected_item.remove_class("selected")
                    self.selected_item = items[idx - 1]
                    self.selected_item.add_class("selected")
                    self.selected_item.scroll_visible()
            except ValueError:
                self.select_first_item()

    def scroll_down(self):
        items = self.content_container.query("Post, Notification")
        if self.selected_item and items:
            try:
                idx = items.nodes.index(self.selected_item)
                if idx < len(items) - 1:
                    self.selected_item.remove_class("selected")
                    self.selected_item = items[idx + 1]
                    self.selected_item.add_class("selected")
                    self.selected_item.scroll_visible()
            except ValueError:
                self.select_first_item()

    def compose(self):
        yield Static(self.title, classes="timeline_title")
        yield LoadingIndicator()
        yield VerticalScroll(classes="timeline-content")


class Timelines(Static):
    """A widget to display the three timelines."""
    def __init__(self, initial_data=None, **kwargs):
        super().__init__(**kwargs)
        self.initial_data = initial_data or {}

    def compose(self):
        yield Timeline("Home", id="home", posts_data=self.initial_data.get("home"))
        yield Timeline("Notifications", id="notifications", posts_data=self.initial_data.get("notifications"))
        yield Timeline("Federated", id="federated", posts_data=self.initial_data.get("federated"))
