from collections import deque
import logging
from textual import on
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Log

log = logging.getLogger(__name__)

MAX_LOG_LINES = 1000


class LogViewerScreen(ModalScreen):
    """A modal screen to display and filter the application's log file."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Close Log Viewer"),
        ("ctrl+f", "focus_filter", "Focus Filter"),
    ]

    def __init__(self, log_file_path: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.log_file_path = log_file_path
        self._raw_lines: list[str] = []

    def compose(self):
        with Vertical(id="log-viewer-dialog") as d:
            d.border_title = "Mastui Log Viewer"
            yield Input(
                placeholder="🔍 Type to filter logs (Ctrl+F to focus, Esc to close)...",
                id="log-filter-input",
            )
            yield Log(highlight=True, id="log-viewer")

    def on_mount(self):
        """Load the log file content when the screen is mounted."""
        try:
            with open(self.log_file_path, "r", encoding="utf-8", errors="replace") as f:
                self._raw_lines = list(deque(f, maxlen=MAX_LOG_LINES))
            self._apply_filter("")
        except FileNotFoundError:
            self._raw_lines = [f"ERROR: Log file not found at {self.log_file_path}\n"]
            self._apply_filter("")
        except Exception as e:
            log.error(f"Failed to read log file: {e}", exc_info=True)
            self._raw_lines = [f"ERROR: Failed to read log file: {e}\n"]
            self._apply_filter("")

    @on(Input.Changed, "#log-filter-input")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self._apply_filter(event.value)

    def _apply_filter(self, query: str) -> None:
        try:
            log_widget = self.query_one(Log)
        except Exception:
            return
        log_widget.clear()
        query_lower = query.strip().lower()
        if not query_lower:
            matching = self._raw_lines
        else:
            matching = [line for line in self._raw_lines if query_lower in line.lower()]

        if matching:
            log_widget.write("".join(matching))
        else:
            log_widget.write(f"--- No log entries matching '{query}' ---")
        log_widget.scroll_end(animate=False)

    def action_focus_filter(self) -> None:
        """Focus the search filter input."""
        try:
            self.query_one("#log-filter-input", Input).focus()
        except Exception:  # nosec B110 - input widget may not be mounted yet
            pass
