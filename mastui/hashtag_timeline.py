from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import VerticalScroll, Container
from mastui.widgets import Post
import logging

log = logging.getLogger(__name__)

class HashtagTimeline(ModalScreen):
    """A modal screen to display a hashtag timeline."""

    BINDINGS = [
        ("escape", "dismiss", "Close Timeline"),
    ]

    def __init__(self, hashtag: str, api, **kwargs) -> None:
        super().__init__(**kwargs)
        self.hashtag = hashtag
        self.api = api

    def compose(self):
        self.title = f"#{self.hashtag}"
        with Container(id="hashtag-timeline-dialog"):
            yield VerticalScroll(
                Static(f"Loading posts for #{self.hashtag}...", classes="status-message"),
                id="hashtag-timeline-container"
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
            container.mount(Static(f"No posts found for #{self.hashtag}.", classes="status-message"))
            return

        for post in posts:
            container.mount(Post(post, timeline_id="hashtag"))
