from textual.containers import VerticalScroll
from textual import on, events
from textual.screen import ModalScreen
from mastui.widgets import Post, Notification, LikePost, BoostPost
from mastui.reply import ReplyScreen
from mastui.thread import ThreadScreen
from mastui.profile import ProfileScreen
from mastui.messages import ViewProfile, SelectPost
import logging

log = logging.getLogger(__name__)

class TimelineContent(VerticalScroll):
    """A container for timeline posts with shared navigation logic."""

    def __init__(self, timeline, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_item = None
        self.timeline = timeline

    def on_focus(self):
        if not self.selected_item:
            self.select_first_item()

    def on_blur(self):
        if self.selected_item:
            self.selected_item.remove_class("selected")

    @on(SelectPost)
    def on_select_post(self, message: SelectPost) -> None:
        if self.selected_item:
            self.selected_item.remove_class("selected")
        self.selected_item = message.post_widget
        self.selected_item.add_class("selected")
        self.focus()

    def select_first_item(self):
        if self.selected_item:
            self.selected_item.remove_class("selected")
        try:
            items = self.query("Post, Notification, ConversationSummary")
            if items:
                self.selected_item = items.first()
                self.selected_item.add_class("selected")
            else:
                self.selected_item = None
        except Exception as e:
            log.error(f"Could not select first item in timeline: {e}", exc_info=True)
            self.selected_item = None


    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        if self.scroll_y >= self.max_scroll_y - 2:
            if not self.timeline.loading_more:
                self.timeline.load_older_posts()

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        if self.scroll_y == 0:
            if not self.timeline.loading_more:
                self.timeline.refresh_posts()

    def scroll_up(self):
        items = self.query("Post, Notification, ConversationSummary")
        if self.selected_item and items:
            try:
                idx = items.nodes.index(self.selected_item)
                if idx > 0:
                    self.selected_item.remove_class("selected")
                    self.selected_item = items[idx - 1]
                    self.selected_item.add_class("selected")
                    self.selected_item.scroll_visible()
                else:
                    # Reached the top, refresh for newer posts
                    if not self.timeline.loading_more:
                        self.timeline.refresh_posts()
            except ValueError as e:
                log.error(f"Could not scroll up in timeline: {e}", exc_info=True)
                self.select_first_item()

    def scroll_down(self):
        items = self.query("Post, Notification, ConversationSummary")
        if self.selected_item and items:
            try:
                idx = items.nodes.index(self.selected_item)
                if idx < len(items) - 1:
                    self.selected_item.remove_class("selected")
                    self.selected_item = items[idx + 1]
                    self.selected_item.add_class("selected")
                    self.selected_item.scroll_visible()
                else:
                    # Reached the bottom, load older posts
                    if not self.timeline.loading_more:
                        self.timeline.load_older_posts()
            except ValueError as e:
                log.error(f"Could not scroll down in timeline: {e}", exc_info=True)
                self.select_first_item()

    def like_post(self):
        if isinstance(self.selected_item, Post):
            status_to_action = self.selected_item.post.get("reblog") or self.selected_item.post
            if not status_to_action:
                self.app.notify("Cannot like a post that has been deleted.", severity="error")
                return
            self.selected_item.show_spinner()
            self.timeline.post_message(LikePost(status_to_action["id"], status_to_action.get("favourited", False)))

    def boost_post(self):
        if isinstance(self.selected_item, Post):
            status_to_action = self.selected_item.post.get("reblog") or self.selected_item.post
            if not status_to_action:
                self.app.notify("Cannot boost a post that has been deleted.", severity="error")
                return
            self.selected_item.show_spinner()
            self.timeline.post_message(BoostPost(status_to_action["id"]))

    def reply_to_post(self):
        if isinstance(self.app.screen, ModalScreen):
            return
        post_to_reply_to = None
        if isinstance(self.selected_item, Post):
            post_to_reply_to = self.selected_item.post.get("reblog") or self.selected_item.post
        elif isinstance(self.selected_item, Notification):
            if self.selected_item.notif["type"] == "mention":
                post_to_reply_to = self.selected_item.notif.get("status")

        if post_to_reply_to:
            self.app.push_screen(
                ReplyScreen(
                    post_to_reply_to,
                    max_characters=self.app.max_characters,
                    visibility=post_to_reply_to.get("visibility", "public"),
                ),
                self.app.on_reply_screen_dismiss
            )
        else:
            self.app.notify("This item cannot be replied to.", severity="error")

    def edit_post(self):
        """Edit the selected post."""
        if isinstance(self.selected_item, Post):
            status = self.selected_item.post.get("reblog") or self.selected_item.post
            if status["account"]["id"] == self.app.me["id"]:
                self.app.action_edit_post()
            else:
                self.app.notify("You can only edit your own posts.", severity="error")
        else:
            self.app.notify("This item cannot be edited.", severity="warning")

    def view_profile(self):
        if isinstance(self.selected_item, Post):
            status = self.selected_item.post.get("reblog") or self.selected_item.post
            account_id = status["account"]["id"]
            self.timeline.post_message(ViewProfile(account_id))
        elif isinstance(self.selected_item, Notification):
            account_id = self.selected_item.notif["account"]["id"]
            self.timeline.post_message(ViewProfile(account_id))

    def open_thread(self):
        if isinstance(self.app.screen, ModalScreen):
            return
        if isinstance(self.selected_item, Post):
            status = self.selected_item.post.get("reblog") or self.selected_item.post
            self.app.push_screen(ThreadScreen(status["id"], self.app.api))
        elif isinstance(self.selected_item, Notification):
            if self.selected_item.notif["type"] in ["mention", "favourite", "reblog"]:
                status = self.selected_item.notif.get("status")
                if status:
                    self.app.push_screen(ThreadScreen(status["id"], self.app.api))

    def go_to_top(self) -> None:
        """Scrolls the timeline to the top and selects the first item."""
        self.scroll_y = 0
        self.select_first_item()
