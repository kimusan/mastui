from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import VerticalScroll, Container
from mastui.widgets import Post, LikePost, BoostPost
from mastui.messages import ConversationRead
from mastui.reply import ReplyScreen
from mastui.edit_post_screen import EditPostScreen
from mastui.url_selector import URLSelectorScreen
import logging

log = logging.getLogger(__name__)

class ConversationScreen(ModalScreen):
    """A modal screen to display a DM conversation."""

    BINDINGS = [
        ("escape", "dismiss", "Close Conversation"),
        ("up", "scroll_up", "Scroll up"),
        ("down", "scroll_down", "Scroll down"),
        ("l", "like_post", "Like post"),
        ("b", "boost_post", "Boost post"),
        ("a", "reply_to_post", "Reply to post"),
        ("e", "edit_post", "Edit post"),
        ("x", "show_urls", "Show URLs"),
    ]

    def __init__(self, conversation_id: str, last_status_id: str, api, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conversation_id = conversation_id
        self.last_status_id = last_status_id
        self.api = api
        self.selected_item = None

    def compose(self):
        with Container(id="conversation-dialog") as cd:
            cd.border_title = "Direct Message"
            yield VerticalScroll(
                Static("Loading conversation...", classes="status-message"),
                id="conversation-container"
            )

    def on_mount(self):
        self.run_worker(self.load_conversation, thread=True)

    def load_conversation(self):
        """Load the conversation context and mark it as read."""
        try:
            # Mark the conversation as read first
            self.api.conversations_read(self.conversation_id)
            
            # Tell the app to update the UI immediately
            self.app.call_from_thread(
                self.post_message, ConversationRead(self.conversation_id)
            )

            # Then fetch the content
            context = self.api.status_context(self.last_status_id)
            main_post_data = self.api.status(self.last_status_id)
            self.app.call_from_thread(self.render_conversation, context, main_post_data)

        except Exception as e:
            log.error(f"Error loading conversation: {e}", exc_info=True)
            self.app.notify(f"Error loading conversation: {e}", severity="error")
            self.app.call_from_thread(self.dismiss)

    def render_conversation(self, context, main_post_data):
        """Render the conversation."""
        container = self.query_one("#conversation-container")
        container.query("*").remove()

        ancestors = context.get("ancestors", [])
        descendants = context.get("descendants", [])
        
        for post in ancestors:
            container.mount(Post(post, timeline_id="conversation"))

        main_post = Post(main_post_data, timeline_id="conversation")
        main_post.add_class("main-post")
        container.mount(main_post)

        for post in descendants:
            reply_post = Post(post, timeline_id="conversation")
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
            log.error(f"Could not select first item in conversation: {e}", exc_info=True)
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
                log.error(f"Could not scroll up in conversation: {e}", exc_info=True)
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
                log.error(f"Could not scroll down in conversation: {e}", exc_info=True)
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
            self.post_message(BoostPost(status_to_action["id"], status_to_action.get("reblogged", False)))

    def action_reply_to_post(self):
        if isinstance(self.selected_item, Post):
            post_to_reply_to = self.selected_item.post.get("reblog") or self.selected_item.post
            if post_to_reply_to:
                self.app.push_screen(
                    ReplyScreen(
                        post_to_reply_to,
                        max_characters=self.app.max_characters,
                        visibility=post_to_reply_to.get("visibility", "direct"),
                    ),
                    self.app.on_reply_screen_dismiss
                )
            else:
                self.app.notify("This item cannot be replied to.", severity="error")

    def action_edit_post(self):
        """Edit the selected post."""
        if isinstance(self.selected_item, Post):
            status = self.selected_item.post.get("reblog") or self.selected_item.post
            if status["account"]["id"] == self.app.me["id"]:
                self.app.push_screen(
                    EditPostScreen(status=status, max_characters=self.app.max_characters),
                    lambda result: self.app.on_edit_post_screen_dismiss((result, status['id']))
                )
            else:
                self.app.notify("You can only edit your own posts.", severity="error")
        else:
            self.app.notify("This item cannot be edited.", severity="warning")

    def action_show_urls(self):
        """Show URLs from the selected post."""
        if isinstance(self.selected_item, Post):
            self.app.push_screen(URLSelectorScreen(self.selected_item.post))
        else:
            self.app.notify("No post selected.", severity="warning")
