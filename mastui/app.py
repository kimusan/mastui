from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual import on
from textual.screen import ModalScreen
from mastui.login import LoginScreen
from mastui.post import PostScreen
from mastui.reply import ReplyScreen
from mastui.splash import SplashScreen
from mastui.mastodon_api import get_api
from mastui.timeline import Timelines, Timeline
from mastui.widgets import Post, LikePost, BoostPost
from mastui.thread import ThreadScreen
from mastui.profile import ProfileScreen
from mastui.config_screen import ConfigScreen
from mastui.logging_config import setup_logging
import logging
import argparse
import os
from mastui.config import config
from mastui.messages import (
    PostStatusUpdate,
    ActionFailed,
    TimelineData,
    FocusNextTimeline,
    FocusPreviousTimeline,
    ViewProfile,
)

# Set up logging
log = logging.getLogger(__name__)


# Get the absolute path to the CSS file
css_path = os.path.join(os.path.dirname(__file__), "app.css")


class Mastui(App):
    """A Textual app to interact with Mastodon."""

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("r", "refresh_timelines", "Refresh timelines"),
        ("c", "compose_post", "Compose post"),
        ("p", "view_profile", "View profile"),
        ("a", "reply_to_post", "Reply to post"),
        ("o", "open_options", "Options"),
        ("l", "like_post", "Like post"),
        ("b", "boost_post", "Boost post"),
        ("up", "scroll_up", "Scroll up"),
        ("down", "scroll_down", "Scroll down"),
    ]
    CSS_PATH = css_path
    initial_data = None
    max_characters = 500 # Default value

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.theme = config.theme
        self.theme_changed_signal.subscribe(self, self.on_theme_changed)
        self.push_screen(SplashScreen())
        self.api = get_api()
        if self.api:
            self.run_worker(self.fetch_instance_info, thread=True, exclusive=True)
            self.set_timer(2, self.show_timelines)
        else:
            self.call_later(self.show_login_screen)

    def fetch_instance_info(self):
        """Fetches instance information from the API."""
        try:
            instance = self.api.instance()
            self.max_characters = instance['configuration']['statuses']['max_characters']
        except Exception as e:
            log.error(f"Error fetching instance info: {e}", exc_info=True)
            # Stick with the default
            pass

    def on_theme_changed(self, event) -> None:
        """Called when the app's theme is changed."""
        new_theme = event.name
        config.theme = new_theme
        if "light" in new_theme:
            config.preferred_light_theme = new_theme
        else:
            config.preferred_dark_theme = new_theme
        config.save_config()

    def show_login_screen(self):
        if isinstance(self.screen, SplashScreen):
            self.pop_screen()
        self.push_screen(LoginScreen(), self.on_login)

    def on_login(self, api) -> None:
        """Called when the login screen is dismissed."""
        log.info("Login successful.")
        self.api = api
        self.show_timelines()

    def show_timelines(self):
        if isinstance(self.screen, SplashScreen):
            self.pop_screen()
        log.info("Showing timelines...")
        self.mount(Timelines())
        try:
            self.query_one("#home", Timeline).focus()
        except Exception:
            pass

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        if "light" in self.theme:
            self.theme = config.preferred_dark_theme
        else:
            self.theme = config.preferred_light_theme

    def action_open_options(self) -> None:
        """An action to open the options screen."""
        if isinstance(self.screen, ModalScreen):
            return
        self.push_screen(ConfigScreen(), self.on_config_screen_dismiss)

    def on_config_screen_dismiss(self, result: bool) -> None:
        """Called when the config screen is dismissed."""
        if result:
            for timeline in self.query(Timeline):
                timeline.update_auto_refresh_timer()

    def action_refresh_timelines(self) -> None:
        """An action to refresh the timelines."""
        log.info("Refreshing all timelines...")
        for timeline in self.query(Timeline):
            timeline.refresh_posts()

    def action_compose_post(self) -> None:
        """An action to compose a new post."""
        if isinstance(self.screen, ModalScreen):
            return
        self.push_screen(PostScreen(max_characters=self.max_characters), self.on_post_screen_dismiss)

    def action_reply_to_post(self) -> None:
        focused = self.query("Timeline:focus")
        if focused:
            focused.first().reply_to_post()

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
        self.run_worker(lambda: self.do_like_post(message.post_id), exclusive=True, thread=True)

    def do_like_post(self, post_id: str):
        try:
            post_data = self.api.status_favourite(post_id)
            self.post_message(PostStatusUpdate(post_data))
        except Exception as e:
            log.error(f"Error liking post {post_id}: {e}", exc_info=True)
            self.post_message(ActionFailed(post_id))

    @on(BoostPost)
    def handle_boost_post(self, message: BoostPost):
        self.run_worker(lambda: self.do_boost_post(message.post_id), exclusive=True, thread=True)

    def do_boost_post(self, post_id: str):
        try:
            post_data = self.api.status_reblog(post_id)
            self.post_message(PostStatusUpdate(post_data))
        except Exception as e:
            log.error(f"Error boosting post {post_id}: {e}", exc_info=True)
            self.post_message(ActionFailed(post_id))

    def on_post_status_update(self, message: PostStatusUpdate) -> None:
        updated_post_data = message.post_data
        target_post = updated_post_data.get("reblog") or updated_post_data
        target_id = target_post["id"]

        for container in [self.screen, *self.query(Timelines)]:
            for post_widget in container.query(Post):
                original_status = post_widget.post.get("reblog") or post_widget.post
                if original_status["id"] == target_id:
                    post_widget.update_from_post(updated_post_data)

    def on_action_failed(self, message: ActionFailed) -> None:
        for container in [self.screen, *self.query(Timelines)]:
            for post_widget in container.query(Post):
                original_status = post_widget.post.get("reblog") or post_widget.post
                if original_status["id"] == message.post_id:
                    post_widget.hide_spinner()

    @on(FocusNextTimeline)
    def on_focus_next_timeline(self, message: FocusNextTimeline) -> None:
        timelines = self.query(Timeline)
        for i, timeline in enumerate(timelines):
            if timeline.has_focus:
                timelines[(i + 1) % len(timelines)].focus()
                return

    @on(FocusPreviousTimeline)
    def on_focus_previous_timeline(self, message: FocusPreviousTimeline) -> None:
        timelines = self.query(Timeline)
        for i, timeline in enumerate(timelines):
            if timeline.has_focus:
                timelines[(i - 1) % len(timelines)].focus()
                return

    @on(ViewProfile)
    def on_view_profile(self, message: ViewProfile) -> None:
        if isinstance(self.screen, ModalScreen):
            return
        self.push_screen(ProfileScreen(message.account_id, self.api))

    def action_like_post(self) -> None:
        focused = self.query("Timeline:focus")
        if focused:
            focused.first().like_post()

    def action_boost_post(self) -> None:
        focused = self.query("Timeline:focus")
        if focused:
            focused.first().boost_post()

    def action_scroll_up(self) -> None:
        focused = self.query("Timeline:focus")
        if focused:
            focused.first().scroll_up()

    def action_scroll_down(self) -> None:
        focused = self.query("Timeline:focus")
        if focused:
            focused.first().scroll_down()


def main():
    parser = argparse.ArgumentParser(description="A Textual app to interact with Mastodon.")
    parser.add_argument("--no-ssl-verify", action="store_false", dest="ssl_verify", help="Disable SSL verification.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()
    setup_logging(debug=args.debug)
    config.ssl_verify = args.ssl_verify
    app = Mastui()
    app.run()


if __name__ == "__main__":
    main()
