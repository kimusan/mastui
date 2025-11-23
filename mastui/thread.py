from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import VerticalScroll, Container
from textual.events import Key
from mastui.widgets import Post, Notification, LikePost, BoostPost
from mastui.reply import ReplyScreen
from mastui.url_selector import URLSelectorScreen
import logging

log = logging.getLogger(__name__)


class ThreadScreen(ModalScreen):
    """A modal screen to display a post thread."""

    BINDINGS = [
        ("r", "refresh_thread", "Refresh thread"),
        ("escape", "dismiss", "Close thread"),
        ("l", "like_post", "Like post"),
        ("b", "boost_post", "Boost post"),
        ("a", "reply_to_post", "Reply to post"),
        ("x", "show_urls", "Show URLs"),
    ]

    def __init__(self, post_id: str, api, **kwargs) -> None:
        super().__init__(**kwargs)
        self.post_id = post_id
        self.api = api
        self.selected_item = None
        self._rendering = False

    def compose(self):
        with Container(id="thread-dialog") as td:
            td.border_title = "Thread View"
            yield VerticalScroll(
                Static("Loading thread...", classes="status-message"),
                id="thread-container",
            )

    def on_mount(self):
        self.run_worker(self.load_thread, thread=True)

    def action_refresh_thread(self):
        """Refresh the thread."""
        self.run_worker(self.load_thread, exclusive=True, thread=True)

    def load_thread(self):
        """Load the thread context."""
        try:
            context = self.api.status_context(self.post_id)
            main_post_data = self.api.status(self.post_id)
            self.app.call_from_thread(self.render_thread, context, main_post_data)
        except Exception as e:
            log.error(f"Error loading thread: {e}", exc_info=True)
            self.app.notify(f"Error loading thread: {e}", severity="error")
            self.dismiss()

    def render_thread(self, context, main_post_data):
        """Render the thread."""
        if self._rendering:
            return

        self._rendering = True
        container = self.query_one("#thread-container")
        container.query("*").remove()

        def mount_posts():
            try:
                ancestors = context.get("ancestors", [])
                descendants = context.get("descendants", [])

                for post in ancestors:
                    container.mount(Post(post, timeline_id="thread"))

                main_post = Post(main_post_data, timeline_id="thread")
                main_post.add_class("main-post")
                container.mount(main_post)

                for post in descendants:
                    reply_post = Post(post, timeline_id="thread")
                    reply_post.add_class("reply-post")
                    container.mount(reply_post)
                self.select_first_item()
            finally:
                self._rendering = False

        self.call_after_refresh(mount_posts)

    def on_key(self, event: Key) -> None:
        if event.key == "up":
            self.action_scroll_up()
            event.stop()
        elif event.key == "down":
            self.action_scroll_down()
            event.stop()

    def select_first_item(self):
        if self.selected_item:
            self.selected_item.remove_class("selected")
        try:
            self.selected_item = self.query(Post).first()
            self.selected_item.add_class("selected")
        except Exception as e:
            log.error(f"Could not select first item in thread: {e}", exc_info=True)
            self.selected_item = None

    def action_scroll_up(self):
        items = self.query("Post")
        if self.selected_item and items:
            try:
                idx = items.nodes.index(self.selected_item)
                if idx > 0:
                    self.selected_item.remove_class("selected")
                    self.selected_item = items[idx - 1]
                    self.selected_item.add_class("selected")
                    self.selected_item.scroll_visible()
            except ValueError as e:
                log.error(f"Could not scroll up in thread: {e}", exc_info=True)
                self.select_first_item()

    def action_scroll_down(self):
        items = self.query("Post")
        if self.selected_item and items:
            try:
                idx = items.nodes.index(self.selected_item)
                if idx < len(items) - 1:
                    self.selected_item.remove_class("selected")
                    self.selected_item = items[idx + 1]
                    self.selected_item.add_class("selected")
                    self.selected_item.scroll_visible()
            except ValueError as e:
                log.error(f"Could not scroll down in thread: {e}", exc_info=True)
                self.select_first_item()

    def action_like_post(self):
        if isinstance(self.selected_item, Post):
            status_to_action = (
                self.selected_item.post.get("reblog") or self.selected_item.post
            )
            if not status_to_action:
                self.app.notify(
                    "Cannot like a post that has been deleted.", severity="error"
                )
                return
            self.selected_item.show_spinner()
            self.post_message(
                LikePost(
                    status_to_action["id"], status_to_action.get("favourited", False)
                )
            )

    def action_boost_post(self):
        if isinstance(self.selected_item, Post):
            status_to_action = (
                self.selected_item.post.get("reblog") or self.selected_item.post
            )
            if not status_to_action:
                self.app.notify(
                    "Cannot boost a post that has been deleted.", severity="error"
                )
                return
            self.selected_item.show_spinner()
            self.post_message(BoostPost(status_to_action["id"], status_to_action.get("reblogged", False)))

    def action_reply_to_post(self):
        if isinstance(self.selected_item, Post):
            post_to_reply_to = (
                self.selected_item.post.get("reblog") or self.selected_item.post
            )
            if post_to_reply_to:
                self.app.push_screen(
                    ReplyScreen(
                        post_to_reply_to, max_characters=self.app.max_characters
                    ),
                    self.app.on_reply_screen_dismiss,
                )
            else:
                self.app.notify("This item cannot be replied to.", severity="error")

    def action_show_urls(self):
        """Show URLs from the selected post."""
        if isinstance(self.selected_item, Post):
            self.app.push_screen(URLSelectorScreen(self.selected_item.post))
        else:
            self.app.notify("No post selected.", severity="warning")
