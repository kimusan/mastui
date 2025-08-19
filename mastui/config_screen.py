from textual.screen import ModalScreen
from textual.widgets import Button, Label, Input, Switch, Static, Select
from textual.containers import Grid
from mastui.config import config
from mastui.cache import cache

class ConfigScreen(ModalScreen):
    """A modal screen for changing settings."""

    DEFAULT_CSS = """
    ConfigScreen {
        align: center middle;
    }
    #config-dialog {
        grid-size: 3;
        grid-gutter: 1;
        padding: 0 1;
        width: 80;
        height: auto;
        border: thick $primary 80%;
        background: $surface;
    }
    .config-label {
        text-align: right;
        width: 100%;
    }
    """

    def compose(self):
        with Grid(id="config-dialog"):
            yield Label("Auto-refresh home?", classes="config-label")
            yield Switch(value=config.home_auto_refresh, id="home_auto_refresh")
            yield Input(str(config.home_auto_refresh_interval), id="home_auto_refresh_interval")

            yield Label("Auto-refresh notifications?", classes="config-label")
            yield Switch(value=config.notifications_auto_refresh, id="notifications_auto_refresh")
            yield Input(str(config.notifications_auto_refresh_interval), id="notifications_auto_refresh_interval")

            yield Label("Auto-refresh federated?", classes="config-label")
            yield Switch(value=config.federated_auto_refresh, id="federated_auto_refresh")
            yield Input(str(config.federated_auto_refresh_interval), id="federated_auto_refresh_interval")

            yield Label("Show images?", classes="config-label")
            yield Switch(value=config.image_support, id="image_support")
            yield Select([("Auto", "auto"), ("ANSI", "ansi"), ("Sixel", "sixel"), ("TGP (iTerm2)", "tgp")], value=config.image_renderer, id="image_renderer")

            yield Label("Auto-prune cache (older than 30 days)?", classes="config-label")
            yield Switch(value=config.auto_prune_cache, id="auto_prune_cache")
            yield Static() # Spacer

            yield Static() # Spacer
            yield Button("Save", variant="primary", id="save")
            yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save_settings()
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "auto_prune_cache" and event.value:
            self.app.prune_cache()

    def save_settings(self):
        """Saves the current settings to the config object."""
        config.home_auto_refresh = self.query_one("#home_auto_refresh").value
        config.home_auto_refresh_interval = int(self.query_one("#home_auto_refresh_interval").value)
        config.notifications_auto_refresh = self.query_one("#notifications_auto_refresh").value
        config.notifications_auto_refresh_interval = int(self.query_one("#notifications_auto_refresh_interval").value)
        config.federated_auto_refresh = self.query_one("#federated_auto_refresh").value
        config.federated_auto_refresh_interval = int(self.query_one("#federated_auto_refresh_interval").value)
        config.image_support = self.query_one("#image_support").value
        config.image_renderer = self.query_one("#image_renderer").value
        config.auto_prune_cache = self.query_one("#auto_prune_cache").value
        config.save_config()
