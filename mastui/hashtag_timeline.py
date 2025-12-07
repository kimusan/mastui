from textual.screen import ModalScreen
from textual.widgets import Static, Header
from textual.containers import Container
from textual.events import Key
from rich.markup import escape as escape_markup
from mastui.widgets import Post
from mastui.timeline_content import TimelineContent
import logging

log = logging.getLogger(__name__)


class HashtagTimeline(ModalScreen):
    """A modal screen to display a hashtag timeline."""

    BINDINGS = [
        ("escape", "dismiss", "Close Timeline"),
        ("l", "like_post", "Like Post"),
        ("b", "boost_post", "Boost Post"),
        ("a", "reply_to_post", "Reply to Post"),
        ("p", "view_profile", "View Profile"),
        ("x", "show_urls", "Show URLs"),
        ("enter", "open_thread", "Open Thread"),
    ]

    def __init__(self, hashtag: str, api, **kwargs) -> None:
        super().__init__(**kwargs)
        self.hashtag = hashtag
        self.api = api

    def compose(self):
        safe_tag = escape_markup(self.hashtag)
        with Container(id="hashtag-timeline-dialog") as d:
            d.border_title = f"#{safe_tag}"
            yield TimelineContent(
                self,
                Static(
                    f"Loading posts for #{safe_tag}...", classes="status-message"
                ),
                id="hashtag-timeline-container",
            )

    def on_mount(self):
        self.run_worker(self.load_posts, thread=True)

    def load_posts(self):
        """Load the posts for the hashtag."""
        try:
            posts = self.api.timeline_hashtag(self.hashtag)
            self.app.call_from_thread(self.render_posts, posts)
        except Exception as e:
            log.error(f"Error loading hashtag timeline: {e}", exc_info=True)
            self.app.notify(f"Error loading hashtag timeline: {e}", severity="error")
            self.dismiss()

    def render_posts(self, posts):
        """Render the posts."""
        container = self.query_one("#hashtag-timeline-container")
        container.query("*").remove()

        if not posts:
            container.mount(
                Static(f"No posts found for #{self.hashtag}.", classes="status-message")
            )
            return

        for post in posts:
            container.mount(Post(post, timeline_id="hashtag"))

        container.select_first_item()

    def on_key(self, event: Key) -> None:
        if event.key == "up":
            self.action_scroll_up()
            event.stop()
        elif event.key == "down":
            self.action_scroll_down()
            event.stop()

    def action_scroll_up(self):
        self.query_one(TimelineContent).scroll_up()

    def action_scroll_down(self):
        self.query_one(TimelineContent).scroll_down()

    def action_like_post(self):
        self.query_one(TimelineContent).like_post()

    def action_boost_post(self):
        self.query_one(TimelineContent).boost_post()

    def action_reply_to_post(self):
        self.query_one(TimelineContent).reply_to_post()

    def action_view_profile(self):
        self.query_one(TimelineContent).view_profile()

    def action_show_urls(self):
        self.query_one(TimelineContent).show_urls()

    def action_open_thread(self):
        self.query_one(TimelineContent).open_thread()
