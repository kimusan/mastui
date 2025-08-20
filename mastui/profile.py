from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import Vertical
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from mastui.utils import to_markdown
import logging

log = logging.getLogger(__name__)

class ProfileScreen(ModalScreen):
    """A modal screen to display a user profile."""

    BINDINGS = [
        ("f", "follow", "Follow/Unfollow"),
        ("escape", "dismiss", "Dismiss")
    ]

    def __init__(self, account_id: str, api, **kwargs) -> None:
        super().__init__(**kwargs)
        self.account_id = account_id
        self.api = api
        self.profile = None

    def compose(self):
        with Vertical(id="profile-dialog"):
            yield Static("Loading profile...", classes="status-message")

    def on_mount(self):
        self.run_worker(self.load_profile, thread=True)

    def load_profile(self):
        """Load the user profile."""
        try:
            self.profile = self.api.account(self.account_id)
            # Check relationship
            relationships = self.api.account_relationships([self.account_id])
            if relationships:
                self.profile['following'] = relationships[0]['following']
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
        container.query("*").remove()

        header = f"[bold]{profile['display_name']}[/bold] (@{profile['acct']})"
        
        # Add following status to header
        if profile.get('following'):
            header += " [green](Following)[/green]"

        note_html = profile.get('note', '')
        note = Markdown(to_markdown(note_html)) if note_html else "No bio."
        
        stats = f"Following: {profile['following_count']} | Followers: {profile['followers_count']} | Posts: {profile['statuses_count']}"

        fields_text = ""
        if profile.get('fields'):
            for field in profile['fields']:
                fields_text += f"**{field['name']}:** {to_markdown(field['value'])}\n"

        container.mount(
            Static(Panel(header, border_style="dim")),
            Static(Panel(note, title="Bio"), id="profile-bio"),
            Static(Panel(Markdown(fields_text), title="Links"), id="profile-links"),
            Static(stats, id="profile-stats")
        )

    def action_follow(self):
        """Follow or unfollow the user."""
        if not self.profile:
            return

        try:
            if self.profile.get('following'):
                self.api.account_unfollow(self.account_id)
                self.app.notify(f"Unfollowed @{self.profile['acct']}")
            else:
                self.api.account_follow(self.account_id)
                self.app.notify(f"Followed @{self.profile['acct']}")
            
            # Reload profile to update status
            self.run_worker(self.load_profile, thread=True)

        except Exception as e:
            log.error(f"Error following/unfollowing: {e}", exc_info=True)
            self.app.notify(f"Error: {e}", severity="error")
