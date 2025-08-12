from textual.screen import Screen
from textual.widgets import Static


class SplashScreen(Screen):
    """A splash screen with the app name, version, and logo."""

    def compose(self) -> None:
        yield Static(
            r"""
            [bold cyan]
            
 888b     d888                   888             d8b 
 8888b   d8888                   888             Y8P 
 88888b.d88888                   888                 
 888Y88888P888  8888b.  .d8888b  888888 888  888 888 
 888 Y888P 888     "88b 88K      888    888  888 888 
 888  Y8P  888 .d888888 "Y8888b. 888    888  888 888 
 888   "   888 888  888      X88 Y88b.  Y88b 888 888 
 888       888 "Y888888  88888P'  "Y888  "Y88888 888 
            [/bold cyan]
            """,
            id="logo",
        )
        yield Static("Mastui v0.1.0", id="version")
        yield Static("Loading...", id="splash-status")

    def update_status(self, message: str) -> None:
        """Update the status message on the splash screen."""
        try:
            self.query_one("#splash-status").update(message)
        except Exception:
            # The screen might be gone, which is fine.
            pass
