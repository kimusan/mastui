from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import VerticalScroll, Container
from mastui.widgets import Post
from mastui.messages import ConversationRead
import logging

log = logging.getLogger(__name__)

class ConversationScreen(ModalScreen):
    """A modal screen to display a DM conversation."""

    BINDINGS = [
        ("escape", "dismiss", "Close Conversation"),
        # Add other bindings for replying, etc. later
    ]

    def __init__(self, conversation_id: str, last_status_id: str, api, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conversation_id = conversation_id
        self.last_status_id = last_status_id
        self.api = api

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
