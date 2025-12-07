from textual.screen import Screen
from textual.widgets import Static
from textual.containers import Vertical
from rich.panel import Panel
from importlib import metadata
import os
import toml
import logging

log = logging.getLogger(__name__)

class SplashScreen(Screen):
    """A splash screen with the app name, version, and logo."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.base_status = "Loading"
        self.dot_count = 0

    def get_version(self):
        """
        Reads the version from the installed package metadata,
        falling back to pyproject.toml for development.
        """
        try:
            # For installed package
            return metadata.version("mastui")
        except metadata.PackageNotFoundError as e:
            log.error(f"Could not get version from metadata: {e}", exc_info=True)
            # For development environment
            pyproject_path = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
            if os.path.exists(pyproject_path):
                with open(pyproject_path) as f:
                    pyproject_data = toml.load(f)
                return pyproject_data["tool"]["poetry"]["version"]
        return "unknown"

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
        version = self.get_version()
        yield Vertical(
            Static(Panel(logo, border_style="dim"), id="logo"),
            Static(f"Mastui v{version}", id="version"),
            Static(f"{self.base_status}...", id="splash-status"),
            id="splash-container",
        )

    def on_mount(self) -> None:
        self.set_interval(0.4, self.update_loading_text)

    def update_loading_text(self) -> None:
        """Update the loading text with blinking dots."""
        self.dot_count = (self.dot_count + 1) % 4
        status_widget = self.query_one("#splash-status")
        # Add padding to prevent the width from changing
        status_text = f"{self.base_status}{'.' * self.dot_count}"
        status_widget.update(f"{status_text:<{len(self.base_status) + 3}}")


    def update_status(self, message: str) -> None:
        """Update the status message on the splash screen."""
        self.base_status = message
        self.dot_count = 0
        self.update_loading_text() # Update immediately with new base text
