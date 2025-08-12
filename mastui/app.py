from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.containers import Container
from textual import work
from textual.message import Message
from mastui.login import LoginScreen
from mastui.post import PostScreen
from mastui.reply import ReplyScreen
from mastui.splash import SplashScreen
from mastui.mastodon_api import get_api
from mastui.timeline import Timelines, Timeline, Post, LikePost, BoostPost
from textual import on
from mastui.logging_config import setup_logging
import logging

# Set up logging
setup_logging()
log = logging.getLogger(__name__)


class PostStatusUpdate(Message):
    """A message to update a post's status."""
    def __init__(self, post_data: dict) -> None:
        self.post_data = post_data
        super().__init__()


class ActionFailed(Message):
    """A message to indicate that an action failed."""
    def __init__(self, post_id: str) -> None:
        self.post_id = post_id
        super().__init__()


class Mastui(App):
    """A Textual app to interact with Mastodon."""

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("r", "refresh_timelines", "Refresh timelines"),
        ("c", "compose_post", "Compose post"),
        ("a", "reply_to_post", "Reply to post"),
        ("tab", "focus_next", "Focus next timeline"),
        ("shift+tab", "focus_previous", "Focus previous timeline"),
        ("l", "like_post", "Like post"),
        ("b", "boost_post", "Boost post"),
        ("up", "scroll_up", "Scroll up"),
        ("down", "scroll_down", "Scroll down"),
    ]
    CSS_PATH = "app.css"
    initial_data = None

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.push_screen(SplashScreen())
        self.api = get_api()
        if self.api:
            self.load_initial_data()
        else:
            self.call_later(self.show_login_screen)

    def show_login_screen(self):
        self.app.pop_screen()
        self.push_screen(LoginScreen(), self.on_login)

    def load_initial_data(self):
        """Starts the worker to load initial data."""
        self.run_worker(self.do_load_initial_data, exclusive=True, thread=True)

    def do_load_initial_data(self):
        """Worker to load initial data from the Mastodon API."""
        log.info("Starting initial data load...")
        def update_status(message):
            log.info(f"Splash screen status: {message}")
            # It's safe to call methods on other threads via call_from_thread
            self.call_from_thread(self.screen.update_status, message)

        try:
            update_status("Fetching home timeline...")
            home_timeline = self.api.timeline_home()
            log.info(f"Fetched {len(home_timeline)} posts for home timeline.")

            update_status("Fetching notifications...")
            notifications = self.api.notifications()
            log.info(f"Fetched {len(notifications)} notifications.")

            update_status("Fetching federated timeline...")
            federated_timeline = self.api.timeline_public()
            log.info(f"Fetched {len(federated_timeline)} posts for federated timeline.")

            self.initial_data = {
                "home": home_timeline,
                "notifications": notifications,
                "federated": federated_timeline,
            }
        except Exception as e:
            log.error(f"Error loading initial data: {e}", exc_info=True)
            self.notify(f"Error loading initial data: {e}", severity="error")
            self.initial_data = {}  # Ensure it's not None

        log.info("Initial data load complete.")
        self.call_from_thread(self.app.pop_screen)
        self.call_from_thread(self.show_timelines)

    def on_login(self, api) -> None:
        """Called when the login screen is dismissed."""
        log.info("Login successful.")
        self.api = api
        self.show_timelines()

    def show_timelines(self):
        log.info("Showing timelines...")
        self.query("Timelines").remove()
        self.mount(Timelines(initial_data=self.initial_data))
        self.call_later(self.focus_first_timeline)

    def focus_first_timeline(self):
        """Focuses the first timeline."""
        try:
            self.query("Timeline").first().focus()
        except:
            pass

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_refresh_timelines(self) -> None:
        """An action to refresh the timelines."""
        log.info("Refreshing all timelines...")
        for timeline in self.query(Timeline):
            timeline.refresh_posts()

    def action_compose_post(self) -> None:
        """An action to compose a new post."""
        self.push_screen(PostScreen(), self.on_post_screen_dismiss)

    def action_reply_to_post(self) -> None:
        """An action to reply to the selected post."""
        for timeline in self.query("Timeline"):
            if timeline.has_focus:
                timeline.reply_to_post()
                return

    def on_post_screen_dismiss(self, result: dict) -> None:
        """Called when the post screen is dismissed."""
        if result:
            try:
                log.info("Sending post...")
                self.api.status_post(
                    status=result["content"],
                    spoiler_text=result["spoiler_text"],
                    language=result["language"],
                )
                log.info("Post sent successfully.")
                self.notify("Post sent successfully!", severity="information")
                self.action_refresh_timelines()
            except Exception as e:
                log.error(f"Error sending post: {e}", exc_info=True)
                self.notify(f"Error sending post: {e}", severity="error")

    def on_reply_screen_dismiss(self, result: dict) -> None:
        """Called when the reply screen is dismissed."""
        if result:
            try:
                log.info(f"Sending reply to post {result['in_reply_to_id']}...")
                self.api.status_post(
                    status=result["content"],
                    spoiler_text=result["spoiler_text"],
                    language=result["language"],
                    in_reply_to_id=result["in_reply_to_id"],
                )
                log.info("Reply sent successfully.")
                self.notify("Reply sent successfully!", severity="information")
                self.action_refresh_timelines()
            except Exception as e:
                log.error(f"Error sending reply: {e}", exc_info=True)
                self.notify(f"Error sending reply: {e}", severity="error")

    @on(LikePost)
    def handle_like_post(self, message: LikePost):
        """Called when a post is liked. Starts a worker to perform the action."""
        log.info(f"Liking post {message.post_id}...")
        self.run_worker(lambda: self.do_like_post(message.post_id), exclusive=True, thread=True)

    def do_like_post(self, post_id: str):
        """Worker to like a post."""
        try:
            post_data = self.api.status_favourite(post_id)
            log.info(f"Successfully liked post {post_id}.")
            self.post_message(PostStatusUpdate(post_data))
        except Exception as e:
            log.error(f"Error liking post {post_id}: {e}", exc_info=True)
            self.post_message(ActionFailed(post_id))
            self.notify(f"Error liking post: {e}", severity="error")

    @on(BoostPost)
    def handle_boost_post(self, message: BoostPost):
        """Called when a post is boosted. Starts a worker to perform the action."""
        log.info(f"Boosting post {message.post_id}...")
        self.run_worker(lambda: self.do_boost_post(message.post_id), exclusive=True, thread=True)

    def do_boost_post(self, post_id: str):
        """Worker to boost a post."""
        try:
            post_data = self.api.status_reblog(post_id)
            log.info(f"Successfully boosted post {post_id}.")
            self.post_message(PostStatusUpdate(post_data))
        except Exception as e:
            log.error(f"Error boosting post {post_id}: {e}", exc_info=True)
            self.post_message(ActionFailed(post_id))
            self.notify(f"Error boosting post: {e}", severity="error")

    def on_post_status_update(self, message: PostStatusUpdate) -> None:
        """Called when a post's status is updated."""
        updated_post_data = message.post_data
        target_post = updated_post_data.get("reblog") or updated_post_data
        target_id = target_post["id"]
        log.info(f"Updating post {target_id} in UI.")

        # The same post may appear in multiple timelines, so we don't stop after the first match.
        for timeline in self.query(Timeline):
            for post_widget in timeline.query(Post):
                original_status_in_widget = post_widget.post.get("reblog") or post_widget.post
                if original_status_in_widget["id"] == target_id:
                    log.info(f"Found post {target_id} in timeline {timeline.id}, updating.")
                    post_widget.update_from_post(updated_post_data)

    def on_action_failed(self, message: ActionFailed) -> None:
        """Called when an action fails."""
        log.warning(f"Action failed for post {message.post_id}.")
        for timeline in self.query(Timeline):
            for post in timeline.query(Post):
                original_status_in_widget = post.post.get("reblog") or post.post
                if original_status_in_widget["id"] == message.post_id:
                    log.info(f"Hiding spinner for post {message.post_id} in timeline {timeline.id}.")
                    post.hide_spinner()

    def action_focus_next(self) -> None:
        """An action to focus the next timeline."""
        timelines = self.query("Timeline")
        for i, timeline in enumerate(timelines):
            if timeline.has_focus:
                timelines[(i + 1) % len(timelines)].focus()
                return

    def action_focus_previous(self) -> None:
        """An action to focus the previous timeline."""
        timelines = self.query("Timeline")
        for i, timeline in enumerate(timelines):
            if timeline.has_focus:
                timelines[(i - 1) % len(timelines)].focus()
                return

    def action_like_post(self) -> None:
        """An action to like the selected post."""
        for timeline in self.query(Timeline):
            if timeline.has_focus:
                timeline.like_post()
                return

    def action_boost_post(self) -> None:
        """An action to boost the selected post."""
        for timeline in self.query(Timeline):
            if timeline.has_focus:
                timeline.boost_post()
                return

    def action_scroll_up(self) -> None:
        """An action to scroll up in the focused timeline."""
        for timeline in self.query("Timeline"):
            if timeline.has_focus:
                timeline.scroll_up()
                return

    def action_scroll_down(self) -> None:
        """An action to scroll down in the focused timeline."""
        for timeline in self.query("Timeline"):
            if timeline.has_focus:
                timeline.scroll_down()
                return


def main():
    """Run the app."""
    app = Mastui()
    app.run()


if __name__ == "__main__":
    main()
