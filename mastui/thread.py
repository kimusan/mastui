from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import VerticalScroll, Container
from textual.events import Key
from mastui.widgets import Post, Notification, LikePost, BoostPost
from mastui.reply import ReplyScreen
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
        ("up", "scroll_up", "Scroll up"),
        ("down", "scroll_down", "Scroll down"),
    ]

    def __init__(self, post_id: str, api, **kwargs) -> None:
        super().__init__(**kwargs)
        self.post_id = post_id
        self.api = api
        self.selected_item = None

    def compose(self):
        with Container(id="thread-dialog"):
            yield VerticalScroll(
                Static("Loading thread...", classes="status-message"),
                id="thread-container"
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
        container = self.query_one("#thread-container")
        container.query("*").remove()

        ancestors = context.get("ancestors", [])
        descendants = context.get("descendants", [])
        
        for post in ancestors:
            container.mount(Post(post, id=f"thread-{post['id']}"))

        main_post = Post(main_post_data, id=f"thread-{main_post_data['id']}")
        main_post.add_class("main-post")
        container.mount(main_post)

        for post in descendants:
            reply_post = Post(post, id=f"thread-{post['id']}")
            reply_post.add_class("reply-post")
            container.mount(reply_post)
            
        self.select_first_item()

    def select_first_item(self):
        if self.selected_item:
            self.selected_item.remove_class("selected")
        try:
            self.selected_item = self.query(Post).first()
            self.selected_item.add_class("selected")
        except Exception as e:
            log.error(f"Could not select first item in thread: {e}", exc_info=True)
            self.selected_item = None

    def on_key(self, event: Key) -> None:
        if event.key == "down":
            self.scroll_down()
            event.stop()
        elif event.key == "up":
            self.scroll_up()
            event.stop()
        elif event.key == "l":
            self.action_like_post()
            event.stop()
        elif event.key == "b":
            self.action_boost_post()
            event.stop()
        elif event.key == "a":
            self.action_reply_to_post()
            event.stop()

    def scroll_up(self):
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

    def scroll_down(self):
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
            status_to_action = self.selected_item.post.get("reblog") or self.selected_item.post
            if not status_to_action:
                self.app.notify("Cannot like a post that has been deleted.", severity="error")
                return
            self.selected_item.show_spinner()
            self.post_message(LikePost(status_to_action["id"], status_to_action.get("favourited", False)))

    def action_boost_post(self):
        if isinstance(self.selected_item, Post):
            status_to_action = self.selected_item.post.get("reblog") or self.selected_item.post
            if not status_to_action:
                self.app.notify("Cannot boost a post that has been deleted.", severity="error")
                return
            self.selected_item.show_spinner()
            self.post_message(BoostPost(status_to_action["id"]))

    def action_reply_to_post(self):
        if isinstance(self.selected_item, Post):
            post_to_reply_to = self.selected_item.post.get("reblog") or self.selected_item.post
            if post_to_reply_to:
                self.app.push_screen(ReplyScreen(post_to_reply_to), self.app.on_reply_screen_dismiss)
            else:
                self.app.notify("This item cannot be replied to.", severity="error")