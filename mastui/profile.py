from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import Vertical
from textual.containers import Center
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.markup import escape as escape_markup
from mastui.utils import to_markdown
from mastui.image import ImageWidget
from mastodon.errors import MastodonAPIError
import logging

log = logging.getLogger(__name__)


class ProfileScreen(ModalScreen):
    """A modal screen to display a user profile."""

    BINDINGS = [
        ("f", "follow", "Follow/Unfollow"),
        ("m", "mute", "Mute/Unmute"),
        ("x", "block", "Block/Unblock"),
        ("escape", "dismiss", "Dismiss"),
    ]

    def __init__(self, account_id: str, api, **kwargs) -> None:
        super().__init__(**kwargs)
        self.account_id = account_id
        self.api = api
        self.profile = None
        self._rendered_profile_id: str | None = None
        self._avatar_widget: ImageWidget | None = None
        self._avatar_url: str | None = None
        self._bio_widget: Static | None = None
        self._links_widget: Static | None = None
        self._stats_widget: Static | None = None
        self._status_widget: Static | None = None

    def compose(self):
        with Center(id="profile-modal"):
            with Static(id="profile-dialog"):
                yield Static("Loading profile...", classes="status-message")
            yield Static(
                "Keys: f=follow/unfollow • m=mute/unmute • x=block/unblock • Esc=close",
                id="profile-hotkeys",
            )

    def on_mount(self):
        self.run_worker(self.load_profile, thread=True)

    def load_profile(self):
        """Load the user profile."""
        try:
            self.profile = self.api.account(self.account_id)
            # Check relationship
            relationships = self.api.account_relationships([self.account_id])
            if relationships:
                self._apply_relationship(relationships[0])
            self.app.call_from_thread(self.render_profile)
        except Exception as e:
            log.error(f"Error loading profile: {e}", exc_info=True)
            self.app.notify(f"Error loading profile: {e}", severity="error")
            self.dismiss()

    def render_profile(self):
        """Render the profile."""
        profile = self.profile
        if not profile:
            return

        container = self.query_one("#profile-dialog")

        display_name = escape_markup(profile.get("display_name", ""))
        acct = escape_markup(profile.get("acct", ""))
        header = f"[bold]{display_name}[/bold] (@{acct})"
        container.border_title = f"Profile: {display_name}"

        # Add relationship statuses to header
        if profile.get("following"):
            header += " [green](Following)[/green]"
        if profile.get("muting"):
            header += " [yellow](Muted)[/yellow]"
        if profile.get("blocking"):
            header += " [red](Blocked)[/red]"

        note_html = profile.get("note", "")
        note_renderable = Markdown(to_markdown(note_html)) if note_html else "No bio."

        stats_text = (
            f"Following: {profile['following_count']} | "
            f"Followers: {profile['followers_count']} | "
            f"Posts: {profile['statuses_count']}"
        )

        fields_text = ""
        if profile.get("fields"):
            for field in profile["fields"]:
                field_name = escape_markup(field.get("name", ""))
                fields_text += (
                    f"**{field_name}:** {to_markdown(field.get('value', ''))}\n"
                )

        if not self._bio_widget:
            container.query("*").remove()
            if self.app.config.image_support:
                self._avatar_url = profile.get("avatar")
                if self._avatar_url:
                    self._avatar_widget = ImageWidget(
                        self._avatar_url, self.app.config, id="profile-avatar"
                    )
                    container.mount(self._avatar_widget)
            self._status_widget = Static(id="profile-status")
            self._bio_widget = Static(id="profile-bio")
            self._links_widget = Static(id="profile-links")
            self._stats_widget = Static(id="profile-stats")
            container.mount(
                self._status_widget,
                self._bio_widget,
                self._links_widget,
                self._stats_widget,
            )
        else:
            if self.app.config.image_support:
                avatar_url = profile.get("avatar")
                if avatar_url != self._avatar_url:
                    if self._avatar_widget:
                        self._avatar_widget.remove()
                    if avatar_url:
                        self._avatar_widget = ImageWidget(
                            avatar_url, self.app.config, id="profile-avatar"
                        )
                        container.mount(self._avatar_widget, before=self._bio_widget)
                    else:
                        self._avatar_widget = None
                    self._avatar_url = avatar_url

        if self._status_widget:
            self._status_widget.update(self._format_relationship_status())

        if self._bio_widget:
            self._bio_widget.update(Panel(note_renderable, title="Bio"))
        links_panel = Panel(
            Markdown(fields_text) if fields_text else Markdown("No links."),
            title="Links",
        )
        if self._links_widget:
            self._links_widget.update(links_panel)
        if self._stats_widget:
            self._stats_widget.update(stats_text)

        self._refresh_status_widget()
        self._rendered_profile_id = profile.get("id")

    def action_follow(self):
        """Follow or unfollow the user."""
        if not self.profile:
            return

        try:
            if self.profile.get("following"):
                self.api.account_unfollow(self.account_id)
                self.profile["following"] = False
                self.app.notify(f"Unfollowed @{self.profile['acct']}")
            else:
                self.api.account_follow(self.account_id)
                self.profile["following"] = True
                self.profile.pop("follow_forbidden", None)
                self.app.notify(f"Followed @{self.profile['acct']}")

            self.run_worker(self.load_profile, thread=True)
            self._refresh_status_widget()

        except MastodonAPIError as error:
            self._handle_api_error("follow", error)

    def action_mute(self):
        """Mute or unmute the user."""
        if not self.profile:
            return

        try:
            if self.profile.get("muting"):
                self.api.account_unmute(self.account_id)
                self.profile["muting"] = False
                self.app.notify(f"Unmuted @{self.profile['acct']}")
            else:
                self.api.account_mute(self.account_id)
                self.profile["muting"] = True
                self.app.notify(f"Muted @{self.profile['acct']}")

            self.run_worker(self.load_profile, thread=True)
            self._refresh_status_widget()

        except MastodonAPIError as error:
            self._handle_api_error("mute", error)

    def action_block(self):
        """Block or unblock the user."""
        if not self.profile:
            return

        try:
            if self.profile.get("blocking"):
                self.api.account_unblock(self.account_id)
                self.profile["blocking"] = False
                self.app.notify(f"Unblocked @{self.profile['acct']}")
            else:
                self.api.account_block(self.account_id)
                self.profile["blocking"] = True
                self.app.notify(f"Blocked @{self.profile['acct']}")

            self.run_worker(self.load_profile, thread=True)
            self._refresh_status_widget()

        except MastodonAPIError as error:
            self._handle_api_error("block", error)

    def _handle_api_error(self, action: str, error: MastodonAPIError) -> None:
        details = ""
        if error.args:
            details = error.args[-1]
        message = details or str(error)
        log.error(f"Error attempting to {action}: {message}", exc_info=True)
        self.app.notify(f"Unable to {action}: {message}", severity="error")
        if action == "follow":
            self.profile["follow_forbidden"] = True
            self._refresh_status_widget(message)

    def _format_relationship_status(self, error_message: str | None = None) -> str:
        profile = self.profile or {}
        tokens: list[str] = []
        if error_message and "not allowed" in error_message.lower():
            tokens.append("Follow forbidden")
        elif profile.get("follow_forbidden"):
            tokens.append("Follow forbidden")
        elif profile.get("requested"):
            tokens.append("Follow requested")
        elif profile.get("following"):
            tokens.append("Following")

        if profile.get("muting"):
            tokens.append("Muted")
        if profile.get("blocking"):
            tokens.append("Blocked")
        if profile.get("domain_blocking"):
            tokens.append("Domain blocked")

        if not tokens:
            tokens.append("No relationship")

        return "Status: " + " • ".join(tokens)

    def _refresh_status_widget(self, error_message: str | None = None) -> None:
        if self._status_widget:
            self._status_widget.update(self._format_relationship_status(error_message))

    def _apply_relationship(self, relationship: dict) -> None:
        if not self.profile:
            return
        keys = [
            "following",
            "followed_by",
            "blocking",
            "blocked_by",
            "muting",
            "requested",
            "domain_blocking",
            "showing_reblogs",
            "notifying",
        ]
        for key in keys:
            self.profile[key] = relationship.get(key)
        if relationship.get("blocked_by") or relationship.get("domain_blocking"):
            self.profile["follow_forbidden"] = True
        else:
            self.profile.pop("follow_forbidden", None)
