from textual.screen import Screen
from textual.widgets import Static
from textual.containers import Vertical
from rich.panel import Panel


class SplashScreen(Screen):
    """A splash screen with the app name, version, and logo."""

    def compose(self) -> None:
        logo = r"""
            [bold cyan]
            
 888b     d888                   888             d8b 
 8888b   d8888                   888             Y8P 
 88888b.d88888                   888                 
 888Y88888P888  8888b.  .d8888b  888888 888  888 888 
 888 Y888P 888     "88b 88K      888    888  888 8K8 
 888  Y8P  888 .d888888 "Y8888b. 888    888  888 8I8 
 888   "   888 888  888      X88 Y88b.  Y88b 888 8M8 
 888       888 "Y888888  88888P'  "Y888  "Y88888 888 
            [/bold cyan]
            """
        yield Vertical(
            Static(Panel(logo, border_style="dim"), id="logo"),
            Static("Mastui v0.2.0", id="version"),
            Static("Loading...", id="splash-status"),
            id="splash-container",
        )

    def on_mount(self) -> None:
        self.set_interval(0.3, self.update_loading_text)

    def update_loading_text(self) -> None:
        status = self.query_one("#splash-status")
        text = status.renderable
        if text.endswith("..."):
            status.update(text[:-3])
        else:
            status.update(text + ".")

    def update_status(self, message: str) -> None:
        """Update the status message on the splash screen."""
        try:
            self.query_one("#splash-status").update(message)
        except Exception:
            # The screen might be gone, which is fine.
            pass

