from textual.screen import ModalScreen
from textual.widgets import Header, Log
from textual.containers import Vertical
import logging

log = logging.getLogger(__name__)

class LogViewerScreen(ModalScreen):
    """A modal screen to display the application's log file."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Close Log Viewer"),
    ]

    def __init__(self, log_file_path: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.log_file_path = log_file_path

    def compose(self):
        with Vertical(id="log-viewer-dialog") as d:
            d.border_title = "Mastui Log Viewer"
            yield Log(highlight=True, id="log-viewer")

    def on_mount(self):
        """Load the log file content when the screen is mounted."""
        log_widget = self.query_one(Log)
        try:
            with open(self.log_file_path, "r") as f:
                log_widget.write(f.read())
            log_widget.scroll_end(animate=False)
        except FileNotFoundError:
            log_widget.write(f"ERROR: Log file not found at {self.log_file_path}")
        except Exception as e:
            log.error(f"Failed to read log file: {e}", exc_info=True)
            log_widget.write(f"ERROR: Failed to read log file: {e}")
