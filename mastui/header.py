from textual.widgets import Header, Static

class CustomHeader(Header):
    """A custom header with a DM notification icon."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tall = False

    def compose(self):
        yield from super().compose()
        yield Static("📩", id="dm_notification_icon", classes="hidden")

    def show_dm_notification(self):
        """Show the DM notification icon."""
        self.query_one("#dm_notification_icon").remove_class("hidden")

    def hide_dm_notification(self):
        """Hide the DM notification icon."""
        self.query_one("#dm_notification_icon").add_class("hidden")
