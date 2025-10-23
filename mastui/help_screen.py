from textual.screen import ModalScreen
from textual.widgets import DataTable, Static, Header
from textual.containers import Vertical

class HelpScreen(ModalScreen):
    """A modal screen to display help information."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Close Help"),
    ]

    def compose(self):
        with Vertical(id="help-dialog") as d:
            d.border_title = "Mastui Help"
            yield Static("[bold]Key Bindings[/bold]", classes="title")
            table = DataTable(zebra_stripes=True)
            table.add_columns("Key(s)", "Action")
            
            # General App Bindings
            table.add_row("[bold]General[/bold]", "")
            table.add_row("q", "Quit the application")
            table.add_row("d", "Toggle dark/light mode")
            table.add_row("u", "Switch user profile")
            table.add_row("o", "Open options screen")
            table.add_row("/", "Open search screen")
            table.add_row("?", "Show this help screen")
            table.add_row("escape", "Close dialog/modal or go back")

            # Timeline Bindings
            table.add_row("", "") # Spacer
            table.add_row("[bold]Timelines[/bold]", "")
            table.add_row("up", "Move selection up")
            table.add_row("down", "Move selection down")
            table.add_row("left", "Focus timeline to the left")
            table.add_row("right", "Focus timeline to the right")
            table.add_row("g", "Jump to top of timeline")
            table.add_row("r", "Refresh all timelines")
            table.add_row("c", "Compose new post")
            table.add_row("m", "Toggle Direct Messages timeline")

            # Post Actions (when a post is selected)
            table.add_row("", "") # Spacer
            table.add_row("[bold]Post Actions[/bold]", "")
            table.add_row("a", "Reply to post")
            table.add_row("l", "Like / Unlike post")
            table.add_row("b", "Boost / Reblog post")
            table.add_row("p", "View author's profile")
            table.add_row("e", "Edit your own post")
            table.add_row("x", "List URLs in post")
            table.add_row("enter", "View post thread")

            # Profile Screen Bindings
            table.add_row("", "") # Spacer
            table.add_row("[bold]Profile View[/bold]", "")
            table.add_row("f", "Follow / Unfollow user")
            table.add_row("m", "Mute / Unmute user")
            table.add_row("x", "Block / Unblock user")

            yield table