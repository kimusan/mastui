from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Label,
    Input,
    Switch,
    Static,
    Select,
    Collapsible,
    Header,
    ListView,
    ListItem,
)
from textual.containers import Grid, Vertical, Horizontal
from textual import on

from mastui.keybind_screen import KeybindScreen
from mastui.languages import (
    get_available_language_options,
    get_default_language_codes,
    get_language_label,
    normalize_language_code,
)


class LanguageRow(ListItem):
    """Visual row for a configured language."""

    def __init__(self, label: str, code: str, is_first: bool, is_last: bool) -> None:
        super().__init__(classes="language-row-item")
        self.can_focus = False
        self.label_text = label
        self.code = code
        self.is_first = is_first
        self.is_last = is_last

    def compose(self):
        with Horizontal(classes="language-row"):
            yield Label(f"{self.label_text} ({self.code})", classes="language-row-label")
            with Horizontal(classes="language-row-actions"):
                yield Button(
                    "↑",
                    id=f"language-up-{self.code}",
                    disabled=self.is_first,
                    classes="language-row-button",
                )
                yield Button(
                    "↓",
                    id=f"language-down-{self.code}",
                    disabled=self.is_last,
                    classes="language-row-button",
                )
                yield Button(
                    "x",
                    id=f"language-remove-{self.code}",
                    classes="language-row-button",
                )


class ConfigScreen(ModalScreen):
    """A modal screen for changing settings."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.language_codes: list[str] = []

    def compose(self):
        config = self.app.config  # Use the app's config object
        self.language_codes = list(config.post_languages) or get_default_language_codes()
        with Vertical(id="config-dialog") as d:
            d.border_title = "Mastui Options"

            with Collapsible(title="Timeline Visibility"):
                with Grid(classes="config-group-body"):
                    yield Label("Enable Home timeline?", classes="config-label")
                    yield Switch(
                        value=config.home_timeline_enabled, id="home_timeline_enabled"
                    )
                    yield Static()  # Spacer

                    yield Label("Enable Local timeline?", classes="config-label")
                    yield Switch(
                        value=config.local_timeline_enabled, id="local_timeline_enabled"
                    )
                    yield Static()  # Spacer

                    yield Label(
                        "Enable Notifications timeline?", classes="config-label"
                    )
                    yield Switch(
                        value=config.notifications_timeline_enabled,
                        id="notifications_timeline_enabled",
                    )
                    yield Static()  # Spacer

                    yield Label("Enable Federated timeline?", classes="config-label")
                    yield Switch(
                        value=config.federated_timeline_enabled,
                        id="federated_timeline_enabled",
                    )
                    yield Static()  # Spacer

                    yield Label("Enable Direct Messages timeline?", classes="config-label")
                    yield Switch(
                        value=config.direct_timeline_enabled,
                        id="direct_timeline_enabled",
                    )
                    yield Static()  # Spacer

                    yield Label("Force single-column mode?", classes="config-label")
                    yield Switch(
                        value=config.force_single_column, id="force_single_column"
                    )
                    yield Static() # Spacer

            with Collapsible(title="Auto-Refresh (in minutes)"):
                with Grid(classes="config-group-body"):
                    yield Label("Auto-refresh home?", classes="config-label")
                    yield Switch(value=config.home_auto_refresh, id="home_auto_refresh")
                    yield Input(
                        str(config.home_auto_refresh_interval),
                        id="home_auto_refresh_interval",
                    )

                    yield Label("Auto-refresh local?", classes="config-label")
                    yield Switch(value=config.local_auto_refresh, id="local_auto_refresh")
                    yield Input(
                        str(config.local_auto_refresh_interval),
                        id="local_auto_refresh_interval",
                    )

                    yield Label("Auto-refresh notifications?", classes="config-label")
                    yield Switch(
                        value=config.notifications_auto_refresh,
                        id="notifications_auto_refresh",
                    )
                    yield Input(
                        str(config.notifications_auto_refresh_interval),
                        id="notifications_auto_refresh_interval",
                    )

                    yield Label("Auto-refresh federated?", classes="config-label")
                    yield Switch(
                        value=config.federated_auto_refresh, id="federated_auto_refresh"
                    )
                    yield Input(
                        str(config.federated_auto_refresh_interval),
                        id="federated_auto_refresh_interval",
                    )

            with Collapsible(title="Images & Cache"):
                with Grid(classes="config-group-body"):
                    yield Label("Show images?", classes="config-label")
                    yield Switch(value=config.image_support, id="image_support")
                    yield Select(
                        [
                            ("Auto", "auto"),
                            ("ANSI", "ansi"),
                            ("Sixel", "sixel"),
                            ("TGP (iTerm2)", "tgp"),
                        ],
                        value=config.image_renderer,
                        id="image_renderer",
                    )

                    yield Label(
                        "Auto-prune cache (older than 30 days)?", classes="config-label"
                    )
                    yield Switch(value=config.auto_prune_cache, id="auto_prune_cache")
                    yield Static()  # Spacer

            with Collapsible(title="Notifications"):
                with Grid(classes="config-group-body"):
                    yield Label("Pop-up on new mentions?", classes="config-label")
                    yield Switch(value=config.notifications_popups_mentions, id="notifications_popups_mentions")
                    yield Static()

                    yield Label("Pop-up on new follows?", classes="config-label")
                    yield Switch(value=config.notifications_popups_follows, id="notifications_popups_follows")
                    yield Static()

                    yield Label("Pop-up on new reblogs?", classes="config-label")
                    yield Switch(value=config.notifications_popups_reblogs, id="notifications_popups_reblogs")
                    yield Static()

                    yield Label("Pop-up on new favourites?", classes="config-label")
                    yield Switch(value=config.notifications_popups_favourites, id="notifications_popups_favourites")
                    yield Static()

            with Collapsible(title="Posting Languages"):
                with Vertical(classes="language-config-group"):
                    yield Static(
                        "Languages appear in compose/reply screens in the order below.",
                        classes="language-help-text",
                    )
                    with ListView(id="language_rows_list"):
                        for row in self._language_row_widgets():
                            yield row
                    with Horizontal(id="language_add_controls"):
                        yield Select(
                            get_available_language_options(self.language_codes),
                            prompt="Add language...",
                            id="language_add_select",
                        )
                        yield Input(
                            placeholder="or type ISO code",
                            id="language_add_input",
                        )
                        yield Button("Add", id="language_add_button")
                    with Horizontal(id="language_list_actions"):
                        yield Button("Reset to Defaults", id="language_reset_button")

            with Horizontal(id="config-buttons"):
                yield Button("Customize Keys", id="keybinds")
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "save":
            self.save_settings()
            self.dismiss(True)
        elif button_id == "keybinds":
            self.app.push_screen(
                KeybindScreen(self.app.keybind_manager), self.on_keybind_screen_dismiss
            )
        elif button_id == "language_add_button":
            self._add_language_from_controls()
        elif button_id == "language_reset_button":
            self.language_codes = get_default_language_codes()
            self._render_language_rows()
            self._refresh_language_select()
        elif button_id and button_id.startswith("language-"):
            if self._handle_language_action(button_id):
                return
        else:
            self.dismiss(False)

    def on_keybind_screen_dismiss(self, result: bool) -> None:
        if result:
            self.app.bind_keys()


    @on(Collapsible.Toggled)
    def on_collapsible_toggled(self, event: Collapsible.Toggled) -> None:
        """When a collapsible is opened, close the others."""
        if not event.collapsible.collapsed:
            for collapsible in self.query(Collapsible):
                if collapsible is not event.collapsible:
                    collapsible.collapsed = True

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "auto_prune_cache" and event.value:
            self.app.prune_cache()

    def _language_row_widgets(self):
        if not self.language_codes:
            yield Static(
                "No languages configured. Add at least one to enable composing.",
                classes="language-empty",
            )
            return
        last_index = len(self.language_codes) - 1
        for index, code in enumerate(self.language_codes):
            label = get_language_label(code)
            yield LanguageRow(label, code, index == 0, index == last_index)

    def _render_language_rows(self) -> None:
        list_view = self.query_one("#language_rows_list", ListView)
        for child in list(list_view.children):
            child.remove()
        for row in self._language_row_widgets():
            list_view.mount(row)

    def _refresh_language_select(self) -> None:
        select = self.query_one("#language_add_select", Select)
        options = get_available_language_options(self.language_codes)
        select.set_options(options)
        select.clear()

    def _add_language_from_controls(self) -> None:
        select = self.query_one("#language_add_select", Select)
        manual_input = self.query_one("#language_add_input", Input)
        select_value = None if select.value is Select.BLANK else select.value
        candidate = select_value or manual_input.value
        normalized = normalize_language_code(candidate)
        if not normalized:
            self.app.notify("Select or type a language code to add.", severity="warning")
            return
        if normalized in self.language_codes:
            self.app.notify("Language already in the list.", severity="warning")
            return
        self.language_codes.append(normalized)
        manual_input.value = ""
        self._render_language_rows()
        self._refresh_language_select()

    def _move_language(self, code: str, offset: int) -> None:
        try:
            current_index = self.language_codes.index(code)
        except ValueError:
            return
        new_index = current_index + offset
        if not 0 <= new_index < len(self.language_codes):
            return
        self.language_codes[current_index], self.language_codes[new_index] = (
            self.language_codes[new_index],
            self.language_codes[current_index],
        )

    def _handle_language_action(self, button_id: str) -> bool:
        try:
            _, action, code = button_id.split("-", 2)
        except ValueError:
            return False

        if action == "remove":
            self.language_codes = [c for c in self.language_codes if c != code]
        elif action == "up":
            self._move_language(code, -1)
        elif action == "down":
            self._move_language(code, 1)
        else:
            return False

        self._render_language_rows()
        self._refresh_language_select()
        return True

    def save_settings(self):
        """Saves the current settings to the config object."""
        config = self.app.config
        config.home_auto_refresh = self.query_one("#home_auto_refresh").value
        config.home_auto_refresh_interval = round(float(
            self.query_one("#home_auto_refresh_interval").value
        ), 2)
        config.local_auto_refresh = self.query_one("#local_auto_refresh").value
        config.local_auto_refresh_interval = round(float(
            self.query_one("#local_auto_refresh_interval").value
        ), 2)
        config.notifications_auto_refresh = self.query_one(
            "#notifications_auto_refresh"
        ).value
        config.notifications_auto_refresh_interval = round(float(
            self.query_one("#notifications_auto_refresh_interval").value
        ), 2)
        config.federated_auto_refresh = self.query_one("#federated_auto_refresh").value
        config.federated_auto_refresh_interval = round(float(
            self.query_one("#federated_auto_refresh_interval").value
        ), 2)
        config.image_support = self.query_one("#image_support").value
        config.image_renderer = self.query_one("#image_renderer").value
        config.auto_prune_cache = self.query_one("#auto_prune_cache").value
        config.home_timeline_enabled = self.query_one("#home_timeline_enabled").value
        config.local_timeline_enabled = self.query_one("#local_timeline_enabled").value
        config.notifications_timeline_enabled = self.query_one(
            "#notifications_timeline_enabled"
        ).value
        config.federated_timeline_enabled = self.query_one(
            "#federated_timeline_enabled"
        ).value
        config.direct_timeline_enabled = self.query_one(
            "#direct_timeline_enabled"
        ).value
        config.force_single_column = self.query_one("#force_single_column").value

        # Save notification settings
        config.notifications_popups_mentions = self.query_one("#notifications_popups_mentions").value
        config.notifications_popups_follows = self.query_one("#notifications_popups_follows").value
        config.notifications_popups_reblogs = self.query_one("#notifications_popups_reblogs").value
        config.notifications_popups_favourites = self.query_one("#notifications_popups_favourites").value

        if not self.language_codes:
            self.language_codes = get_default_language_codes()
            self._render_language_rows()
            self.app.notify(
                "At least one compose language is required. Restored defaults.",
                severity="warning",
            )
        config.post_languages = list(self.language_codes)
        
        config.save_config()
