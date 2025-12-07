from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Static
from textual import on, events
from textual.screen import ModalScreen
from mastui.header import CustomHeader
from mastui.login import LoginScreen
from mastui.post import PostScreen
from mastui.reply import ReplyScreen
from mastui.edit_post_screen import EditPostScreen
from mastui.splash import SplashScreen
from mastui.mastodon_api import get_api
from mastui.timeline import Timelines, Timeline
from mastui.widgets import (
    Post,
    Notification,
    LikePost,
    BoostPost,
    DeletePost,
    VoteOnPoll,
    PostDeleted,
)
from mastui.thread import ThreadScreen
from mastui.profile import ProfileScreen
from mastui.config_screen import ConfigScreen
from mastui.help_screen import HelpScreen
from mastui.search_screen import SearchScreen
from mastui.hashtag_timeline import HashtagTimeline
from mastui.conversation_screen import ConversationScreen
from mastui.keybind_manager import KeybindManager
from mastui.keybind_screen import KeybindScreen
from mastui.log_viewer_screen import LogViewerScreen
from mastui.logging_config import setup_logging
from mastui.retro import retro_theme_builtin
from mastui.theme_manager import load_custom_themes
from mastui.config import Config
from mastui.profile_manager import profile_manager
from mastui.profile_selection import ProfileSelectionScreen
from mastui.version_check import check_for_update, get_installed_version
from mastui.update_dialog import UpdateAvailableScreen
from mastui.autocomplete import AutocompleteProvider
from mastui.messages import (
    PostStatusUpdate,
    ActionFailed,
    TimelineData,
    FocusNextTimeline,
    FocusPreviousTimeline,
    ViewProfile,
    ViewHashtag,
    ViewConversation,
    ConversationRead,
    ResumeTimers,
)
from mastui.cache import Cache
from mastui.url_selector import URLSelectorScreen
from mastodon.errors import MastodonAPIError
import logging
import argparse
import os
from urllib.parse import urlparse

# Set up logging
log = logging.getLogger(__name__)


# Get the absolute path to the CSS file
css_path = os.path.join(os.path.dirname(__file__), "app.css")


class Mastui(App):
    """A Textual app to interact with Mastodon."""

    BINDINGS = [Binding("?", "show_help", "Help")]
    CSS_PATH = css_path
    initial_data = None
    max_characters = 500  # Default value
    log_file_path: str | None = None
    config: Config = None
    cache: Cache = None
    me: dict | None = None
    notified_dm_ids: set[str] = set()
    keybind_manager: KeybindManager = None
    autocomplete_provider: AutocompleteProvider | None = None
    current_version: str = "0.0.0"
    update_check_timer = None
    _bound_keys: set[str]
    pending_timeline_inits: set[str] | None
    _early_timeline_ready: set[str]
    _timelines_widget: Timelines | None

    def __init__(self, action=None, ssl_verify=True, debug=False):
        super().__init__()
        self.action = action
        self.ssl_verify = ssl_verify
        self._debug = debug
        self._bound_keys = set()
        self.autocomplete_provider = None
        self.pending_timeline_inits = None
        self._early_timeline_ready = set()
        self._timelines_widget = None
        log.debug(f"Mastui app initialized with action: {self.action}")

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield CustomHeader()
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        log.debug("Mastui app mounted.")

        # Load and register all themes
        for theme in load_custom_themes():
            self.register_theme(theme)
        self.register_theme(retro_theme_builtin)

        if self.action == "add_account":
            log.debug(f"Action '{self.action}' specified, showing login screen.")
            self.call_later(self.show_login_screen)
        else:
            log.debug("No 'add_account' action specified, selecting profile.")
            self.select_profile()

    def on_login(self, result: tuple) -> None:
        """Called when the login screen is dismissed."""
        api, env_content = result
        log.info("Login successful.")
        self.api = api

        try:
            # Create a default profile name
            me = api.me()
            # Sanitize username for directory name
            sanitized_username = "".join(
                c for c in me["username"] if c.isalnum() or c in "-_"
            )
            host = urlparse(me["url"]).hostname
            profile_name = f"{sanitized_username}@{host}"

            # Create the new profile
            profile_manager.create_profile(profile_name, env_content)

            self.load_profile(profile_name)
        except Exception as e:
            log.error(f"Error creating profile after login: {e}", exc_info=True)
            self.notify("Failed to create profile. Please try again.", severity="error")
            self.call_later(self.show_login_screen)

    def select_profile(self):
        """Select a profile to use, or load the last used one."""
        migrated = profile_manager.migrate_old_profile()
        if migrated:
            self.notify(
                "Your profile has been migrated to the new multi-profile system.",
                title="Profile Migrated",
            )

        # Try to load the last used profile
        last_profile = profile_manager.get_last_profile()
        if last_profile and last_profile in profile_manager.get_profiles():
            self.load_profile(last_profile)
            return

        # Fallback to selection screen
        profiles = profile_manager.get_profiles()
        if len(profiles) == 1:
            self.load_profile(profiles[0])
        elif len(profiles) > 1:
            self.push_screen(ProfileSelectionScreen(profiles), self.on_profile_selected)
        else:
            self.show_login_screen()

    def on_profile_selected(self, profile_name: str):
        """Called when a profile is selected."""
        if profile_name == "add_new_profile":
            self.show_login_screen()
        else:
            self.load_profile(profile_name)

    def load_profile(self, profile_name: str):
        """Load a profile and start the app."""
        log.debug(f"Loading profile: {profile_name}")
        profile_path = profile_manager.get_profile_path(profile_name)
        log.debug(f"Profile path: {profile_path}")
        self.config = Config(profile_path)
        self.config.ssl_verify = self.ssl_verify
        log.debug(
            f"Loaded access token: {'Yes' if self.config.mastodon_access_token else 'No'}"
        )

        # Check if the profile is incomplete (migrated without access token)
        if not self.config.mastodon_access_token:
            log.error(
                f"Profile '{profile_name}' is incomplete and missing access token."
            )
            self.notify(
                f"Profile '{profile_name}' must be re-authorized.",
                title="Re-authorization Required",
                severity="error",
            )
            # Get the host from the broken profile and go to the login screen
            host = self.config.mastodon_host
            self.call_later(lambda: self.show_login_screen(host=host))
            return

        self.cache = Cache(profile_path / "cache.db")

        # Initialize and load keybindings
        self.keybind_manager = KeybindManager(profile_path)
        self.keybind_manager.load_keymap()
        self.bind_keys()

        # Save this as the last successfully loaded profile
        profile_manager.set_last_profile(profile_name)

        # Update the header with the profile name
        self.sub_title = profile_name

        self.theme = self.config.theme
        self.theme_changed_signal.subscribe(self, self.on_theme_changed)

        self.push_screen(SplashScreen())
        self.api = get_api(self.config)
        if self.api:
            self.run_worker(self._load_profile_data, thread=True, exclusive=True)
        else:
            log.error("API object could not be created. Forcing login.")
            self.call_later(self.show_login_screen)

    def _load_profile_data(self):
        """Worker to fetch initial profile data in the background."""
        splash_screen = self.screen
        try:
            # Update splash screen status
            if isinstance(splash_screen, SplashScreen):
                self.call_from_thread(splash_screen.update_status, "Authenticating")

            # Fetch the user's info once and store it
            self.me = self.api.me()
            self.autocomplete_provider = AutocompleteProvider(self.api, self.config, self.me)

            # Update splash screen status
            if isinstance(splash_screen, SplashScreen):
                self.call_from_thread(
                    splash_screen.update_status, "Fetching instance details"
                )

            # Fetch instance info
            instance = self.api.instance()
            self.max_characters = instance["configuration"]["statuses"][
                "max_characters"
            ]
        except Exception as e:
            log.error(
                f"Failed to verify credentials or fetch instance info: {e}",
                exc_info=True,
            )
            self.call_from_thread(
                self.notify,
                "Failed to connect to your instance. Please try again.",
                severity="error",
            )
            self.call_from_thread(self.show_login_screen)
            return

        # Update splash screen status
        if isinstance(splash_screen, SplashScreen):
            self.call_from_thread(splash_screen.update_status, "Loading timelines")

        # Once data is loaded, show the timelines
        self.call_from_thread(self.show_timelines)

        # Start other background tasks
        if self.config.auto_prune_cache:
            self.run_worker(self.prune_cache, thread=True, exclusive=True)
        self.set_interval(300, self.check_for_dms)  # Check for DMs every 5 minutes
        self.call_from_thread(self.check_for_dms)  # Also check right after startup

    def check_for_dms(self):
        """Background worker to check for new direct messages."""
        header = self.query_one(CustomHeader)
        if not self.api or self.config.direct_timeline_enabled:
            header.hide_dm_notification()
            return

        log.debug("Checking for new direct messages in the background...")
        try:
            all_convos = self.api.conversations()  # Fetches up to 20 by default
            if not all_convos:
                header.hide_dm_notification()
                return

            unread_convos = [c for c in all_convos if c.get("unread")]

            if not unread_convos:
                header.hide_dm_notification()
                return

            header.show_dm_notification()

            for convo in unread_convos:
                if convo["id"] not in self.notified_dm_ids:
                    # Find the other participant
                    other_participants = [
                        acc for acc in convo["accounts"] if acc["id"] != self.me["id"]
                    ]
                    if other_participants:
                        participant_name = other_participants[0]["acct"]
                        self.notify(f"New DM from @{participant_name}", title="New DM")
                    else:  # Should not happen, but as a fallback
                        self.notify("You have a new Direct Message", title="New DM")

                    self.notified_dm_ids.add(convo["id"])

        except Exception as e:
            log.error(f"Background DM check failed: {e}", exc_info=True)

    def fetch_instance_info(self):
        """Fetches instance information from the API."""
        try:
            instance = self.api.instance()
            self.max_characters = instance["configuration"]["statuses"][
                "max_characters"
            ]
        except Exception as e:
            log.error(f"Error fetching instance info: {e}", exc_info=True)
            self.notify("Could not fetch instance information.", severity="error")

    def prune_cache(self):
        """Prunes the image cache."""
        try:
            count = self.cache.prune_image_cache()
            if count > 0:
                self.notify(f"Pruned {count} items from the image cache.")
        except Exception as e:
            log.error(f"Error pruning cache: {e}", exc_info=True)
            self.notify("Error pruning image cache.", severity="error")

    def on_theme_changed(self, event) -> None:
        """Called when the app's theme is changed."""
        new_theme = event.name
        self.config.theme = new_theme
        if "light" in new_theme:
            self.config.preferred_light_theme = new_theme
        else:
            self.config.preferred_dark_theme = new_theme
        self.config.save_config()

    def show_login_screen(self, host: str = None):
        log.debug(f"Attempting to show login screen for host: {host}")
        if isinstance(self.screen, SplashScreen):
            self.pop_screen()
        self.push_screen(LoginScreen(host=host), self.on_login)

    def on_login(self, result: tuple) -> None:
        """Called when the login screen is dismissed."""
        api, env_content = result
        log.info("Login successful.")
        self.api = api

        # Create a default profile name
        me = api.me()
        # Sanitize username for directory name
        sanitized_username = "".join(
            c for c in me["username"] if c.isalnum() or c in "-_"
        ).rstrip()
        host = urlparse(me["url"]).hostname
        profile_name = f"{sanitized_username}@{host}"

        # Create the new profile
        log.debug(f"Creating profile '{profile_name}' with content:\n{env_content}")
        profile_manager.create_profile(profile_name, env_content)

        self.load_profile(profile_name)

    def show_timelines(self):
        log.info("Showing timelines...")
        self._early_timeline_ready.clear()
        timelines = Timelines()
        self._timelines_widget = timelines

        try:
            base_screen = self._screen_stack[0]
            base_screen.mount(timelines)
        except Exception as exc:
            log.error(f"Failed to mount timelines on base screen: {exc}", exc_info=True)
            self.mount(timelines)

        def register_timelines():
            timeline_ids = {timeline.id for timeline in timelines.query(Timeline)}
            self.pending_timeline_inits = set(timeline_ids)
            if self._early_timeline_ready:
                self.pending_timeline_inits -= self._early_timeline_ready
                self._early_timeline_ready.clear()
            if not self.pending_timeline_inits:
                self._dismiss_splash_screen()

        self.call_after_refresh(register_timelines)
        self.call_later(self.check_layout_mode)
        self.call_later(lambda: self.schedule_update_checks(initial=True))

    @on(events.Resize)
    def on_resize(self, event: events.Resize) -> None:
        """Called when the app is resized."""
        self.check_layout_mode()

    def check_layout_mode(self) -> None:
        """Check and apply the layout mode based on screen size."""
        if not self.config:
            return
        is_narrow = (
            self.config.force_single_column or self.size.width < self.size.height
        )
        timelines = self._timelines_widget
        if timelines:
            timelines.set_class(is_narrow, "single-column-mode")
        else:
            log.debug("Timelines widget not yet mounted; skipping layout check.")

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        if "light" in self.theme:
            self.theme = self.config.preferred_dark_theme
        else:
            self.theme = self.config.preferred_light_theme

    def action_open_options(self) -> None:
        """An action to open the options screen."""
        if isinstance(self.screen, ModalScreen):
            return
        self.pause_timers()
        self.push_screen(ConfigScreen(), self.on_config_screen_dismiss)

    def action_show_help(self) -> None:
        """An action to show the help screen."""
        if isinstance(self.screen, ModalScreen):
            return
        self.pause_timers()
        self.push_screen(HelpScreen(), self.on_help_screen_dismiss)

    def action_search(self) -> None:
        """An action to open the search screen."""
        if isinstance(self.screen, ModalScreen):
            return
        self.pause_timers()
        log.debug(f"SEARCH: API object base URL is {self.api.api_base_url}")
        self.push_screen(SearchScreen(api=self.api), self.on_search_screen_dismiss)

    def on_search_screen_dismiss(self, _) -> None:
        """Called when the search screen is dismissed."""
        self.resume_timers()

    def on_help_screen_dismiss(self) -> None:
        """Called when the help screen is dismissed."""
        self.resume_timers()

    def on_config_screen_dismiss(self, result: bool) -> None:
        """Called when the config screen is dismissed."""
        self.resume_timers()
        if result:
            self.query_one(Timelines).remove()
            self.mount(Timelines())
            self.call_later(self.check_layout_mode)

    def action_refresh_timelines(self) -> None:
        """An action to refresh the timelines."""
        log.info("Refreshing all timelines...")
        for timeline in self.query(Timeline):
            timeline.refresh_posts()

    def action_compose_post(self) -> None:
        """An action to compose a new post."""
        if isinstance(self.screen, ModalScreen):
            return
        self.pause_timers()
        self.push_screen(
            PostScreen(max_characters=self.max_characters), self.on_post_screen_dismiss
        )

    def action_reply_to_post(self) -> None:
        focused = self.query("Timeline:focus")
        if focused:
            self.pause_timers()
            focused.first().reply_to_post()

    def action_delete_post(self) -> None:
        """Action to delete the selected post if it belongs to the current user."""
        focused = self.query("Timeline:focus")
        if focused:
            focused.first().delete_post()

    def schedule_update_checks(self, initial: bool = False) -> None:
        """Schedule update checks (immediately and every 24 hours)."""
        try:
            self.current_version = get_installed_version()
        except Exception as e:
            log.debug(f"Could not detect installed version, using package version: {e}")
            self.current_version = package_version

        # Kick off an immediate check (respecting 24h window inside check_for_update)
        self.run_worker(
            lambda: self.check_for_updates(force=initial), thread=True, exclusive=False
        )

        # Set up daily checks
        if not self.update_check_timer:
            self.update_check_timer = self.set_interval(
                24 * 60 * 60,
                lambda: self.run_worker(
                    self.check_for_updates, thread=True, exclusive=False
                ),
            )

    def check_for_updates(self, force: bool = False) -> None:
        """Background update check against PyPI."""
        if not self.config:
            return
        try:
            result = check_for_update(
                profile_path=self.config.profile_path,
                current_version=self.current_version,
                force=force,
            )
            if result.get("should_notify") and result.get("latest_version"):
                latest = result["latest_version"]
                release_url = result.get("release_url", "")
                self.call_from_thread(self.show_update_dialog, latest, release_url)
        except Exception as e:
            log.debug(f"Update check failed: {e}", exc_info=True)

    def show_update_dialog(self, latest_version: str, release_url: str) -> None:
        """Show a modal dialog about a newer version."""
        if isinstance(self.screen, ModalScreen):
            # Avoid stacking on top of other modals; try again shortly.
            self.call_later(
                lambda: self.show_update_dialog(latest_version, release_url)
            )
            return
        dialog = UpdateAvailableScreen(
            current_version=self.current_version,
            latest_version=latest_version,
            release_url=release_url,
        )
        self.push_screen(dialog)

    def action_edit_post(self) -> None:
        """Action to edit the selected post."""
        focused = self.query("Timeline:focus")
        if not focused:
            return

        selected_item = focused.first().content_container.selected_item
        if not isinstance(selected_item, Post):
            self.notify("Only your own posts can be edited.", severity="warning")
            return

        status = selected_item.post.get("reblog") or selected_item.post

        # Check if the post is by the current user
        if status["account"]["id"] != self.me["id"]:
            self.notify("You can only edit your own posts.", severity="error")
            return

        self.pause_timers()
        self.push_screen(
            EditPostScreen(status=status, max_characters=self.max_characters),
            lambda result: self.on_edit_post_screen_dismiss((result, status["id"])),
        )

    def on_post_screen_dismiss(self, result: dict) -> None:
        """Called when the post screen is dismissed."""
        self.resume_timers()
        if result:
            try:
                log.info("Sending post...")
                self.api.status_post(
                    status=result["content"],
                    spoiler_text=result["spoiler_text"],
                    language=result["language"],
                    poll=result["poll"],
                    visibility=result["visibility"],
                )
                log.info("Post sent successfully.")
                self.notify("Post sent successfully!", severity="information")
                self.action_refresh_timelines()
            except Exception as e:
                log.error(f"Error sending post: {e}", exc_info=True)
                self.notify(f"Error sending post: {e}", severity="error")

    def on_reply_screen_dismiss(self, result: dict) -> None:
        """Called when the reply screen is dismissed."""
        self.resume_timers()
        if result:
            try:
                log.info(f"Sending reply to post {result['in_reply_to_id']}...")
                self.api.status_post(
                    status=result["content"],
                    spoiler_text=result["spoiler_text"],
                    language=result["language"],
                    in_reply_to_id=result["in_reply_to_id"],
                    visibility=result["visibility"],
                )
                log.info("Reply sent successfully.")
                self.notify("Reply sent successfully!", severity="information")
                self.action_refresh_timelines()
            except Exception as e:
                log.error(f"Error sending reply: {e}", exc_info=True)
                self.notify(f"Error sending reply: {e}", severity="error")

    def on_edit_post_screen_dismiss(self, result: tuple) -> None:
        """Called when the edit post screen is dismissed."""
        self.resume_timers()
        if result and result[0] is not None:
            new_content, post_id = result
            try:
                log.info(f"Updating post {post_id}...")
                updated_post = self.api.status_update(
                    id=post_id,
                    status=new_content["content"],
                    spoiler_text=new_content["spoiler_text"],
                )
                log.info(f"Post {post_id} updated successfully.")
                self.notify("Post updated successfully!", severity="information")

                # Update the post in the cache for all timelines it might be in
                for timeline_id in [
                    "home",
                    "notifications",
                ]:  # Add other relevant timelines
                    self.cache.bulk_insert_posts(timeline_id, [updated_post])

                self.post_message(PostStatusUpdate(updated_post))
            except Exception as e:
                log.error(f"Error updating post: {e}", exc_info=True)
                self.notify(f"Error updating post: {e}", severity="error")

    @on(LikePost)
    def handle_like_post(self, message: LikePost):
        self.run_worker(
            lambda: self.do_like_post(message.post_id, message.favourited),
            exclusive=True,
            thread=True,
        )

    def do_like_post(self, post_id: str, favourited: bool):
        try:
            if favourited:
                post_data = self.api.status_unfavourite(post_id)
            else:
                post_data = self.api.status_favourite(post_id)
            self.post_message(PostStatusUpdate(post_data))
        except Exception as e:
            log.error(f"Error liking/unliking post {post_id}: {e}", exc_info=True)
            self.post_message(ActionFailed(post_id))

    @on(BoostPost)
    def handle_boost_post(self, message: BoostPost):
        self.run_worker(
            lambda: self.do_boost_post(message.post_id, message.reblogged),
            exclusive=True,
            thread=True,
        )

    def do_boost_post(self, post_id: str, already_reblogged: bool):
        try:
            if already_reblogged:
                post_data = self.api.status_unreblog(post_id)
            else:
                post_data = self.api.status_reblog(post_id)
            self.post_message(PostStatusUpdate(post_data))
        except Exception as e:
            log.error(f"Error boosting/unboosting post {post_id}: {e}", exc_info=True)
            self.post_message(ActionFailed(post_id))

    @on(DeletePost)
    def handle_delete_post(self, message: DeletePost):
        self.run_worker(
            lambda: self.do_delete_post(message.post_id), exclusive=True, thread=True
        )

    def do_delete_post(self, post_id: str):
        try:
            self.api.status_delete(post_id)
            self.cache.delete_post(post_id)
            self.post_message(PostDeleted(post_id))
            self.notify("Post deleted.", severity="information")
        except Exception as e:
            log.error(f"Error deleting post {post_id}: {e}", exc_info=True)
            self.post_message(ActionFailed(post_id))

    @on(VoteOnPoll)
    def handle_vote_on_poll(self, message: VoteOnPoll):
        self.run_worker(
            lambda: self.do_vote_on_poll(
                message.poll_id, message.choice, message.timeline_id, message.post_id
            ),
            exclusive=True,
            thread=True,
        )

    def do_vote_on_poll(
        self, poll_id: str, choice: int, timeline_id: str, post_id: str
    ):
        try:
            # The API returns the updated post object after voting
            updated_post_data = self.api.poll_vote(poll_id, [choice])

            # Update the cache with the new post data
            if timeline_id not in ["thread", "search"]:
                self.cache.bulk_insert_posts(timeline_id, [updated_post_data])

            self.post_message(PostStatusUpdate(updated_post_data))
            self.notify("Vote cast successfully!", severity="information")
        except MastodonAPIError as e:
            if "You have already voted on this poll" in str(e):
                log.info(
                    f"User already voted on poll {poll_id}. Fetching latest post state for post {post_id}."
                )
                try:
                    # Fetch the latest post data to get the correct poll state
                    updated_post_data = self.api.status(post_id)
                    if timeline_id not in ["thread", "search"]:
                        self.cache.bulk_insert_posts(timeline_id, [updated_post_data])
                    self.post_message(PostStatusUpdate(updated_post_data))
                except Exception as fetch_e:
                    log.error(
                        f"Error fetching post {post_id} after 'already voted' error: {fetch_e}",
                        exc_info=True,
                    )
                    self.notify("Could not refresh poll state.", severity="error")
            else:
                log.error(f"Error voting on poll {poll_id}: {e}", exc_info=True)
                self.notify(f"Error casting vote: {e}", severity="error")
                self.action_refresh_timelines()  # Fallback
        except Exception as e:
            log.error(f"Unexpected error voting on poll {poll_id}: {e}", exc_info=True)
            self.notify(f"Error casting vote: {e}", severity="error")
            self.action_refresh_timelines()

    def on_post_status_update(self, message: PostStatusUpdate) -> None:
        updated_post_data = message.post_data
        target_post = updated_post_data.get("reblog") or updated_post_data
        target_id = target_post["id"]
        target_id_str = str(target_id)
        log.debug(f"Received PostStatusUpdate for post ID {target_id_str}")

        found_widget = False
        # Search on the active screen (could be a modal) and in the main timelines
        for container in [self.screen, *self.query(Timelines)]:
            for post_widget in container.query(Post):
                original_status = post_widget.post.get("reblog") or post_widget.post
                if original_status and str(original_status["id"]) == target_id_str:
                    log.debug(f"Found matching post widget: {post_widget}")
                    post_widget.update_from_post(updated_post_data)
                    found_widget = True
            for notif_widget in container.query(Notification):
                notif_status = notif_widget.notif.get("status")
                if notif_status and hasattr(notif_widget, "update_from_post"):
                    original_status = notif_status.get("reblog") or notif_status
                    if (
                        original_status
                        and str(original_status.get("id")) == target_id_str
                    ):
                        log.debug(f"Found matching notification widget: {notif_widget}")
                        notif_widget.update_from_post(updated_post_data)
                        found_widget = True

        # Fallback: search globally for any Notification widgets (covers nested layouts)
        if not found_widget:
            for notif_widget in self.query(Notification):
                notif_status = notif_widget.notif.get("status")
                if notif_status and hasattr(notif_widget, "update_from_post"):
                    original_status = notif_status.get("reblog") or notif_status
                    if (
                        original_status
                        and str(original_status.get("id")) == target_id_str
                    ):
                        log.debug(
                            f"Found matching notification widget via fallback: {notif_widget}"
                        )
                        notif_widget.update_from_post(updated_post_data)
                        found_widget = True

        if not found_widget:
            log.warning(f"Could not find a Post widget to update for ID {target_id}")

    @on(PostDeleted)
    def on_post_deleted(self, message: PostDeleted) -> None:
        deleted_id = str(message.post_id)
        log.debug(f"Received PostDeleted for post ID {deleted_id}")
        for container in [self.screen, *self.query(Timelines)]:
            for post_widget in list(container.query(Post)):
                original_status = post_widget.post.get("reblog") or post_widget.post
                if original_status and str(original_status["id"]) == deleted_id:
                    log.debug(
                        f"Removing post widget {post_widget} for deleted ID {deleted_id}"
                    )
                    content_container = post_widget.parent
                    post_widget.remove()
                    if (
                        hasattr(content_container, "selected_item")
                        and content_container.selected_item is post_widget
                    ):
                        content_container.selected_item = None
                        content_container.select_first_item()
            for notif_widget in list(container.query(Notification)):
                notif_status = notif_widget.notif.get("status")
                if notif_status:
                    original_status = notif_status.get("reblog") or notif_status
                    if original_status and str(original_status.get("id")) == deleted_id:
                        log.debug(
                            f"Removing notification widget {notif_widget} for deleted ID {deleted_id}"
                        )
                        notif_widget.remove()

    def on_action_failed(self, message: ActionFailed) -> None:
        log.debug(f"Received ActionFailed for post ID {message.post_id}")
        found_widget = False
        for container in [self.screen, *self.query(Timelines)]:
            log.debug(f"Searching for post in container {container}")
            for post_widget in container.query(Post):
                original_status = post_widget.post.get("reblog") or post_widget.post
                if original_status and str(original_status["id"]) == str(
                    message.post_id
                ):
                    log.debug(
                        f"Found matching post widget to hide spinner: {post_widget}"
                    )
                    post_widget.hide_spinner()
                    found_widget = True
            for notif_widget in container.query(Notification):
                notif_status = notif_widget.notif.get("status")
                if notif_status and hasattr(notif_widget, "hide_spinner"):
                    original_status = notif_status.get("reblog") or notif_status
                    if original_status and str(original_status.get("id")) == str(
                        message.post_id
                    ):
                        log.debug(
                            f"Found matching notification widget to hide spinner: {notif_widget}"
                        )
                        notif_widget.hide_spinner()
                        found_widget = True

        if not found_widget:
            for notif_widget in self.query(Notification):
                notif_status = notif_widget.notif.get("status")
                if notif_status and hasattr(notif_widget, "hide_spinner"):
                    original_status = notif_status.get("reblog") or notif_status
                    if original_status and str(original_status.get("id")) == str(
                        message.post_id
                    ):
                        notif_widget.hide_spinner()
                        found_widget = True

        if not found_widget:
            log.warning(
                f"Could not find a Post widget to hide spinner for ID {message.post_id}"
            )
        else:
            log.debug(f"Spinner hidden for post ID {message.post_id}")

    @on(FocusNextTimeline)
    def on_focus_next_timeline(self, message: FocusNextTimeline) -> None:
        self._focus_timeline(1)

    @on(FocusPreviousTimeline)
    def on_focus_previous_timeline(self, message: FocusPreviousTimeline) -> None:
        self._focus_timeline(-1)

    def _focus_timeline(self, offset: int) -> None:
        """Focus the timeline offset from the current focused timeline."""
        timelines = self.query(Timeline)
        if not timelines:
            return
        for i, timeline in enumerate(timelines):
            if timeline.has_focus:
                timelines[(i + offset) % len(timelines)].focus()
                return
        # If none focused, focus the first timeline
        timelines.first().focus()

    def action_focus_next_column(self) -> None:
        """Focus the next visible timeline column."""
        self._focus_timeline(1)

    def action_focus_previous_column(self) -> None:
        """Focus the previous visible timeline column."""
        self._focus_timeline(-1)

    @on(ViewProfile)
    def on_view_profile(self, message: ViewProfile) -> None:
        if isinstance(self.screen, ModalScreen):
            return
        self.pause_timers()
        self.push_screen(
            ProfileScreen(message.account_id, self.api), self.on_profile_screen_dismiss
        )

    @on(ViewHashtag)
    def on_view_hashtag(self, message: ViewHashtag) -> None:
        """Called when a hashtag is clicked."""
        if isinstance(self.screen, ModalScreen):
            return
        self.pause_timers()
        self.push_screen(
            HashtagTimeline(hashtag=message.hashtag, api=self.api),
            self.on_hashtag_screen_dismiss,
        )

    @on(ViewConversation)
    def on_view_conversation(self, message: ViewConversation) -> None:
        """Called when a conversation is selected."""
        if isinstance(self.screen, ModalScreen):
            return
        self.pause_timers()
        self.push_screen(
            ConversationScreen(
                conversation_id=message.conversation_id,
                last_status_id=message.last_status_id,
                api=self.api,
            ),
            self.on_conversation_screen_dismiss,
        )

    def on_hashtag_screen_dismiss(self, _) -> None:
        """Called when the hashtag timeline screen is dismissed."""
        self.resume_timers()

    @on(ConversationRead)
    def on_conversation_read(self, message: ConversationRead) -> None:
        """Called when a conversation has been marked as read."""
        try:
            # Update the cache immediately
            self.cache.mark_conversation_as_read(message.conversation_id)

            # Find the summary widget and update it for responsiveness
            summary_widget = self.query_one(f"#conv-{message.conversation_id}")
            summary_widget.conversation["unread"] = False
            summary_widget.remove_class("unread")
            summary_widget.border_title = summary_widget.border_title.replace(
                "📩", "📭"
            )
        except Exception as e:
            log.warning(
                f"Could not update conversation summary after marking as read: {e}"
            )

    def on_conversation_screen_dismiss(self, conversation_id: str) -> None:
        """Called when the conversation screen is dismissed."""
        self.resume_timers()
        try:
            # Trigger a refresh from the server to confirm
            self.query_one("#direct").refresh_posts()
        except Exception as e:
            log.warning(
                f"Could not refresh DM timeline after closing conversation: {e}"
            )

    def action_link_clicked(self, link: str) -> None:
        """Called when a link is clicked."""
        import webbrowser

        webbrowser.open(link)

    def on_profile_screen_dismiss(self, _) -> None:
        """Called when the profile screen is dismissed."""
        self.resume_timers()

    def action_toggle_dms(self) -> None:
        """Toggles the visibility of the Direct Messages timeline."""
        self.config.direct_timeline_enabled = not self.config.direct_timeline_enabled
        self.config.save_config()

        try:
            timelines_container = self.query_one(Timelines)
            dm_timeline_query = timelines_container.query("#direct")

            if self.config.direct_timeline_enabled:
                # Show the timeline
                self.query_one(CustomHeader).hide_dm_notification()
                if not dm_timeline_query:  # If it doesn't exist, create it
                    new_timeline = Timeline("Direct Messages", id="direct")
                    timelines_container.mount(new_timeline)
                    new_timeline.scroll_visible()  # Make sure it's visible
                    new_timeline.focus()  # Focus the new timeline
            else:
                # Hide the timeline
                if dm_timeline_query:
                    timeline_to_remove = dm_timeline_query.first()
                    # If the timeline to be removed has focus, move focus first
                    if timeline_to_remove.has_focus:
                        all_timelines = timelines_container.query(Timeline)
                        try:
                            idx = all_timelines.nodes.index(timeline_to_remove)
                            if idx > 0:
                                all_timelines[idx - 1].focus()
                            elif len(all_timelines) > 1:
                                all_timelines[1].focus()
                        except ValueError:
                            # Fallback if something goes wrong
                            if len(all_timelines) > 1:
                                all_timelines[0].focus()
                    timeline_to_remove.remove()

        except Exception as e:
            log.error(f"Error toggling DM timeline smoothly: {e}", exc_info=True)
            # Fallback to the old method if the smooth one fails
            try:
                self.query_one(Timelines).remove()
                self.mount(Timelines())
            except Exception as fallback_e:
                log.error(
                    f"Error re-rendering timelines after DM toggle fallback: {fallback_e}",
                    exc_info=True,
                )

        self.call_later(self.check_layout_mode)

    def action_view_profile(self) -> None:
        """An action to view the profile of the selected post's author."""
        focused = self.query("Timeline:focus")
        if focused:
            focused.first().view_profile()

    def action_like_post(self) -> None:
        """An action to like the selected post."""
        focused = self.query("Timeline:focus")
        if focused:
            focused.first().like_post()

    def action_boost_post(self) -> None:
        """An action to boost the selected post."""
        focused = self.query("Timeline:focus")
        if focused:
            focused.first().boost_post()

    def action_scroll_up(self) -> None:
        """An action to scroll up the focused timeline."""
        focused = self.query("Timeline:focus")
        if focused:
            focused.first().scroll_up()

    def action_scroll_down(self) -> None:
        """An action to scroll down the focused timeline."""
        focused = self.query("Timeline:focus")
        if focused:
            focused.first().scroll_down()

    def action_go_to_top(self) -> None:
        """An action to scroll to the top of the focused timeline."""
        focused = self.query("Timeline:focus")
        if focused:
            focused.first().go_to_top()

    def action_show_urls(self) -> None:
        """Find the selected post and show the URL selector screen."""
        post_to_extract = None

        # Case 1: A modal screen is active (e.g., Thread, Conversation)
        if isinstance(self.screen, ModalScreen) and hasattr(
            self.screen, "selected_item"
        ):
            selected_item = self.screen.selected_item
            if isinstance(selected_item, Post):
                post_to_extract = selected_item.post

        # Case 2: A main timeline is focused
        else:
            focused = self.query("Timeline:focus")
            if focused:
                selected_item = focused.first().content_container.selected_item
                if isinstance(selected_item, Post):
                    post_to_extract = selected_item.post
                elif isinstance(
                    selected_item, Notification
                ) and selected_item.notif.get("status"):
                    post_to_extract = selected_item.notif["status"]

        if post_to_extract:
            self.pause_timers()
            self.push_screen(
                URLSelectorScreen(post_to_extract), lambda _: self.resume_timers()
            )
        else:
            self.notify("No post selected or post has no content.", severity="warning")

    def action_switch_profile(self) -> None:
        """An action to switch the user profile."""
        if isinstance(self.screen, ModalScreen):
            return
        self.pause_timers()
        profiles = profile_manager.get_profiles()
        self.push_screen(
            ProfileSelectionScreen(profiles), self.on_profile_selected_for_switch
        )

    def on_profile_selected_for_switch(self, profile_name: str) -> None:
        """Called when a profile is selected from the switcher."""
        if profile_name == "add_new_profile":
            self._tear_down_profile()
            self.show_login_screen()
        elif profile_name and profile_name != self.config.profile_path.name:
            self.switch_profile(profile_name)
        else:
            # If the same profile is chosen, or selection is cancelled, just resume
            self.resume_timers()

    def bind_keys(self):
        """(Re)bind all keys from the keybind manager."""
        if self._bound_keys:
            for key in self._bound_keys:
                self.bind(key, "", show=False)
            self._bound_keys.clear()

        # Load the latest map from disk (in case it was just changed)
        self.keybind_manager.load_keymap()

        # Bind the new keys without showing them in the footer (help screen covers these)
        for action, key in self.keybind_manager.keymap.items():
            self.bind(
                key,
                action,
                description=self.keybind_manager.action_descriptions.get(action, ""),
                show=False,
            )
            self._bound_keys.add(key)
        self.bind("x", "show_urls", description="Extract URLs from post", show=False)

    def notify_timeline_initialized(self, timeline_id: str) -> None:
        if self.pending_timeline_inits is None:
            self._early_timeline_ready.add(timeline_id)
            return
        if timeline_id in self.pending_timeline_inits:
            self.pending_timeline_inits.discard(timeline_id)
            if not self.pending_timeline_inits:
                self._dismiss_splash_screen()

    def _dismiss_splash_screen(self) -> None:
        if isinstance(self.screen, SplashScreen):
            self.pop_screen()

    def get_autocomplete_provider(self) -> AutocompleteProvider | None:
        if not self.autocomplete_provider and self.api and self.config:
            try:
                self.autocomplete_provider = AutocompleteProvider(
                    self.api, self.config, self.me
                )
            except Exception as exc:  # pragma: no cover - depends on runtime API availability
                log.warning("Unable to initialize autocomplete provider: %s", exc)
                self.autocomplete_provider = None
        return self.autocomplete_provider

    def switch_profile(self, profile_name: str) -> None:
        """Performs a soft restart to switch to a new profile."""
        log.info(f"Switching profile to {profile_name}...")
        self._tear_down_profile()
        self.load_profile(profile_name)

    def _tear_down_profile(self):
        """Removes the current profile's UI and data."""
        log.debug("Tearing down current profile.")
        if self._timelines_widget:
            try:
                self._timelines_widget.remove()
            except Exception as e:
                log.warning(f"Could not remove Timelines widget during tear down: {e}")
            self._timelines_widget = None

        self.api = None
        self.config = None
        self.cache = None
        self.me = None
        self.notified_dm_ids = set()
        self.sub_title = ""
        self.autocomplete_provider = None
        if self.pending_timeline_inits is not None:
            self.pending_timeline_inits.clear()
        self.pending_timeline_inits = None
        self._early_timeline_ready.clear()

    def pause_timers(self):
        """Pauses all timeline timers."""
        for timeline in self.query(Timeline):
            timeline.pause_timers()

    def resume_timers(self):
        """Resumes all timeline timers."""
        for timeline in self.query(Timeline):
            timeline.resume_timers()

    def action_view_log(self) -> None:
        """An action to view the application log file."""
        if self._debug and self.log_file_path:
            if not isinstance(self.screen, LogViewerScreen):
                self.push_screen(LogViewerScreen(self.log_file_path))


def main():
    parser = argparse.ArgumentParser(
        description="A Textual app to interact with Mastodon."
    )
    parser.add_argument(
        "--no-ssl-verify",
        action="store_false",
        dest="ssl_verify",
        help="Disable SSL verification.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--add-account", action="store_true", help="Add a new account.")
    args = parser.parse_args()

    log_file_path = setup_logging(debug=args.debug)

    action = "add_account" if args.add_account else None
    app = Mastui(action=action, ssl_verify=args.ssl_verify, debug=args.debug)
    app.log_file_path = log_file_path
    app.run()

    if app.log_file_path:
        print(f"Log file written to: {app.log_file_path}")
