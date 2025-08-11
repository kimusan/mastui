from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.containers import Container
from textual import work
from mastui.login import LoginScreen
from mastui.post import PostScreen
from mastui.reply import ReplyScreen
from mastui.splash import SplashScreen
from mastui.mastodon_api import get_api
from mastui.timeline import Timelines, Timeline


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

    @work(exclusive=True, thread=True)
    def load_initial_data(self):
        """Load initial data from the Mastodon API."""
        try:
            home_timeline = self.api.timeline_home()
            notifications = self.api.notifications()
            federated_timeline = self.api.timeline_public()
            self.initial_data = {
                "home": home_timeline,
                "notifications": notifications,
                "federated": federated_timeline,
            }
        except Exception as e:
            self.notify(f"Error loading initial data: {e}", severity="error")
            self.initial_data = {}  # Ensure it's not None

        self.call_from_thread(self.app.pop_screen)
        self.call_from_thread(self.show_timelines)

    def on_login(self, api) -> None:
        """Called when the login screen is dismissed."""
        self.api = api
        self.show_timelines()

    def show_timelines(self):
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
        for timeline in self.query("Timeline"):
            timeline.load_posts()

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
                self.api.status_post(
                    status=result["content"],
                    spoiler_text=result["spoiler_text"],
                    language=result["language"],
                )
                self.notify("Post sent successfully!", severity="information")
                self.action_refresh_timelines()
            except Exception as e:
                self.notify(f"Error sending post: {e}", severity="error")

    def on_reply_screen_dismiss(self, result: dict) -> None:
        """Called when the reply screen is dismissed."""
        if result:
            try:
                self.api.status_post(
                    status=result["content"],
                    spoiler_text=result["spoiler_text"],
                    language=result["language"],
                    in_reply_to_id=result["in_reply_to_id"],
                )
                self.notify("Reply sent successfully!", severity="information")
                self.action_refresh_timelines()
            except Exception as e:
                self.notify(f"Error sending reply: {e}", severity="error")

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
        for timeline in self.query("Timeline"):
            if timeline.has_focus:
                timeline.like_post()
                return

    def action_boost_post(self) -> None:
        """An action to boost the selected post."""
        for timeline in self.query("Timeline"):
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
