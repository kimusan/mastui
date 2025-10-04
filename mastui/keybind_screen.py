from textual.screen import ModalScreen
from textual.widgets import Button, Label, Input, Static, Header
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual import on
from mastui.key_input import KeyInput

class KeybindScreen(ModalScreen):
    """A modal screen for changing key bindings."""

    def __init__(self, keybind_manager, **kwargs):
        super().__init__(**kwargs)
        self.keybind_manager = keybind_manager

    def compose(self):
        with Vertical(id="keybind-dialog") as d:
            d.border_title = "Customize Key Bindings"
            with VerticalScroll(id="keybind-container"):
                    for action, description in sorted(self.keybind_manager.action_descriptions.items()):
                        with Horizontal():
                            yield Label(description, classes="keybind-label")
                            yield KeyInput(value=self.keybind_manager.get_key(action), id=f"key-input-{action}")
            with Horizontal(id="keybind-buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Reset to Defaults", id="reset")
                yield Button("Cancel", id="cancel")

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save_bindings()
        elif event.button.id == "reset":
            self.keybind_manager.reset_to_defaults()
            self.app.notify("Key bindings have been reset to default.")
            self.dismiss(True) # Dismiss and signal a reload
        else:
            self.dismiss(False)

    def save_bindings(self):
        """Validate and save the new keybindings."""
        new_keymap = {}
        seen_keys = {}
        for action in self.keybind_manager.action_descriptions:
            input_widget = self.query_one(f"#key-input-{action}", Input)
            new_key = input_widget.value.strip()
            if not new_key:
                self.app.notify(f"Key for '{self.keybind_manager.action_descriptions[action]}' cannot be empty.", severity="error")
                return

            if new_key in seen_keys:
                self.app.notify(f"Duplicate key '{new_key}' assigned to more than one action.", severity="error")
                return
            
            seen_keys[new_key] = action
            new_keymap[action] = new_key

        self.keybind_manager.keymap = new_keymap
        self.keybind_manager.save_keymap()
        self.app.notify("Key bindings saved.")
        self.dismiss(True) # Dismiss and signal a reload
