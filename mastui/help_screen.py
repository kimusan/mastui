from textual.screen import ModalScreen
from textual.widgets import DataTable, Static
from textual.containers import Vertical

class HelpScreen(ModalScreen):
    """A modal screen to display help information."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Close Help"),
    ]

    def compose(self):
        with Vertical(id="help-dialog"):
            yield Static("Key Bindings", classes="title")
            table = DataTable()
            table.add_columns("Key", "Action", "Context")
            
            # General App Bindings
            table.add_row("[bold]Global[/bold]")
            table.add_row("d", "Toggle dark/light mode", "Anywhere")
            table.add_row("r", "Refresh all timelines", "Anywhere")
            table.add_row("c", "Compose new post", "Anywhere")
            table.add_row("o", "Open options screen", "Anywhere")
            table.add_row("?", "Show this help screen", "Anywhere")
            table.add_row("q", "Quit the application", "Anywhere")

            # Timeline Bindings
            table.add_row("")
            table.add_row("[bold]Timeline / Thread View[/bold]")
            table.add_row("up/down", "Navigate posts", "Timeline/Thread")
            table.add_row("left/right", "Switch between timelines", "Timeline")
            table.add_row("enter", "View post thread", "Timeline")
            table.add_row("a", "Reply to selected post", "Timeline/Thread")
            table.add_row("l", "Like selected post", "Timeline/Thread")
            table.add_row("b", "Boost selected post", "Timeline/Thread")
            table.add_row("p", "View profile of post author", "Timeline/Thread")

            # Profile Screen Bindings
            table.add_row("")
            table.add_row("[bold]Profile View[/bold]")
            table.add_row("f", "Follow/Unfollow user", "Profile")

            # Modal Screen Bindings
            table.add_row("")
            table.add_row("[bold]Modals[/bold]")
            table.add_row("escape", "Close the current modal/dialog", "Any Modal")

            yield table
