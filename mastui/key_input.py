from textual.widgets import Input
from textual.events import Key

class KeyInput(Input):
    """A special input widget that captures a single key press."""

    def on_key(self, event: Key) -> None:
        """Capture a key press and use it as the value, allowing navigation."""
        # Allow navigation keys to perform their default actions
        if event.key in ("tab", "shift+tab"):
            return

        # For all other keys, prevent the default input action and set the value
        event.prevent_default()
        self.value = event.key

