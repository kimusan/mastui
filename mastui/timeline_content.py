from textual.containers import VerticalScroll
from textual import on, events
from textual.screen import ModalScreen
from mastui.widgets import Post, Notification, LikePost, BoostPost, DeletePost
from mastui.reply import ReplyScreen
from mastui.thread import ThreadScreen
from mastui.profile import ProfileScreen
from mastui.messages import ViewProfile, SelectPost
from mastui.url_selector import URLSelectorScreen
from mastui.confirm_dialog import ConfirmDeleteScreen
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
            self.selected_item = None

    @on(SelectPost)
    def on_select_post(self, message: SelectPost) -> None:
        if self.selected_item:
            self.selected_item.remove_class("selected")
        self.selected_item = message.post_widget
        self.selected_item.add_class("selected")
        self.focus()

    def select_first_item(self):
        first_item = self._first_item()
        self._set_selected(first_item)

    def _first_item(self):
        try:
            items = self.query("Post, Notification, ConversationSummary")
            return items.first() if items else None
        except Exception as e:
            log.error(f"Could not select first item in timeline: {e}", exc_info=True)
            return None

    def _set_selected(self, widget):
        if self.selected_item:
            self.selected_item.remove_class("selected")
        self.selected_item = widget
        if self.selected_item:
            self.selected_item.add_class("selected")


    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        if self.scroll_y >= self.max_scroll_y - 2:
            if getattr(self.timeline, "loading_more", False):
                return
            if hasattr(self.timeline, "load_older_posts"):
                self.timeline.load_older_posts()

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        if self.scroll_y == 0:
            if not getattr(self.timeline, "loading_more", False):
                self.timeline.refresh_posts()

    def scroll_up(self):
        previous_item = self._adjacent_item(-1)
        if previous_item:
            self._set_selected(previous_item)
            previous_item.scroll_visible()
        else:
            if not getattr(self.timeline, "loading_more", False):
                self.timeline.refresh_posts()

    def scroll_down(self):
        next_item = self._adjacent_item(1)
        if next_item:
            self._set_selected(next_item)
            next_item.scroll_visible()
        else:
            if not getattr(self.timeline, "loading_more", False):
                if hasattr(self.timeline, "load_older_posts"):
                    self.timeline.load_older_posts()

    def _adjacent_item(self, offset: int):
        try:
            items = self.query("Post, Notification, ConversationSummary")
        except Exception:
            return None

        if not items:
            return None

        current = self.selected_item or items.first()
        if current not in items:
            return items.first()

        idx = items.nodes.index(current)
        new_index = idx + offset
        if 0 <= new_index < len(items):
            return items[new_index]
        return None

    def _get_status_for_action(self):
        """Return the status object associated with the selected item, if any."""
        if isinstance(self.selected_item, Post):
            return self.selected_item.post.get("reblog") or self.selected_item.post
        if isinstance(self.selected_item, Notification):
            status = self.selected_item.notif.get("status")
            if status:
                return status.get("reblog") or status
        return None

    def _show_action_spinner(self):
        if self.selected_item and hasattr(self.selected_item, "show_spinner"):
            try:
                self.selected_item.show_spinner()
            except Exception as e:
                log.warning(f"Could not show spinner on selected item: {e}")

    def like_post(self):
        status_to_action = self._get_status_for_action()
        if not status_to_action:
            self.app.notify("This item has no status to like.", severity="error")
            return
        self._show_action_spinner()
        self.timeline.post_message(
            LikePost(status_to_action["id"], status_to_action.get("favourited", False))
        )

    def boost_post(self):
        status_to_action = self._get_status_for_action()
        if not status_to_action:
            self.app.notify("This item has no status to boost.", severity="error")
            return
        self._show_action_spinner()
        self.timeline.post_message(
            BoostPost(status_to_action["id"], status_to_action.get("reblogged", False))
        )

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

    def delete_post(self):
        """Delete the selected post, only if it belongs to the current user."""
        status = self._get_status_for_action()
        if not status:
            self.app.notify("This item cannot be deleted.", severity="warning")
            return
        if status["account"]["id"] != self.app.me["id"]:
            self.app.notify("You can only delete your own posts.", severity="error")
            return

        def on_confirm(result: bool | None):
            self.app.resume_timers()
            if result:
                self._show_action_spinner()
                self.timeline.post_message(DeletePost(status["id"]))
            else:
                self.app.notify("Deletion cancelled.", severity="information")

        self.app.pause_timers()
        self.app.push_screen(ConfirmDeleteScreen(), on_confirm)

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

    def show_urls(self):
        """Show URLs from the selected post."""
        post_to_extract = None

        if isinstance(self.selected_item, Post):
            post_to_extract = self.selected_item.post
        elif isinstance(self.selected_item, Notification):
            if self.selected_item.notif.get("status"):
                post_to_extract = self.selected_item.notif["status"]

        if post_to_extract:
            self.app.push_screen(URLSelectorScreen(post_to_extract))
        else:
            self.app.notify(
                "No post selected or post has no content.", severity="warning"
            )
