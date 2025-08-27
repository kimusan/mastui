import json
from pathlib import Path
import logging
from textual.theme import Theme

log = logging.getLogger(__name__)

# The path to the user's custom themes file
CUSTOM_THEMES_PATH = Path.home() / ".config" / "mastui" / "custom-themes.json"

# The default retro-green theme, to be used as a template
DEFAULT_THEME_DATA = {
    "name": "retro-green",
    "styles": {
        "app": "bg: #0F0F0F text: #A0A0A0",
        "header": "bg: #1A1A1A text: #E0E0E0",
        "footer": "bg: #1A1A1A text: #A0A0A0",
        "timeline_title": "text: #00FF00 bold",
        "timeline-item.selected": "bg: #1A1A1A",
        "timeline-item.favourited": "text: #FFFF00",
        "timeline-item.reblogged": "text: #00FF00",
        "post-footer": "text: #606060",
        "boost-header": "text: #00C000",
        "poll-header": "text: #00FF00",
        "poll-total-votes": "text: #A0A0A0",
        "poll-expiry": "text: #606060",
        "button": "bg: #2A2A2A text: #E0E0E0",
        "button.primary": "bg: #008000 text: #FFFFFF",
        "input": "bg: #1A1A1A text: #E0E0E0",
        "select": "bg: #1A1A1A text: #E0E0E0",
        "switch": "bg: #2A2A2A",
        "switch--on": "bg: #008000",
    },
    "palettes": {
        "primary": "#00FF00",
        "secondary": "#008000",
        "accent": "#00C000",
        "foreground": "#A0A0A0",
        "background": "#0F0F0F",
        "surface": "#1A1A1A",
        "panel": "#1A1A1A",
        "success": "#00FF00",
        "warning": "#FFFF00",
        "error": "#FF0000",
        "dark": True,
    },
}

def create_default_themes_file_if_not_exists():
    """
    Creates the custom-themes.json file with the default retro-green
    theme if the file does not already exist.
    """
    if CUSTOM_THEMES_PATH.exists():
        return

    log.info(f"Creating default custom themes file at {CUSTOM_THEMES_PATH}")
    try:
        CUSTOM_THEMES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CUSTOM_THEMES_PATH, "w") as f:
            # The file should contain a list of themes
            json.dump([DEFAULT_THEME_DATA], f, indent=4)
    except Exception as e:
        log.error(f"Failed to create custom themes file: {e}", exc_info=True)

def load_custom_themes() -> list[Theme]:
    """
    Loads themes from the custom-themes.json file.
    """
    # Ensure the file exists before trying to read it
    create_default_themes_file_if_not_exists()

    themes = []
    try:
        with open(CUSTOM_THEMES_PATH, "r") as f:
            themes_data = json.load(f)
        
        if not isinstance(themes_data, list):
            log.error("Custom themes file is not a valid list of themes.")
            return []

        for theme_data in themes_data:
            try:
                # Filter the palettes to only include keys the constructor expects
                valid_palette_keys = [
                    "primary", "secondary", "accent", "foreground", "background",
                    "success", "warning", "error", "surface", "panel", "dark"
                ]
                filtered_palette = {
                    key: theme_data["palettes"][key]
                    for key in valid_palette_keys
                    if key in theme_data["palettes"]
                }

                theme = Theme(
                    name=theme_data["name"],
                    **filtered_palette
                )
                theme.styles = theme_data["styles"]
                themes.append(theme)
                log.info(f"Successfully loaded custom theme: '{theme.name}'")
            except KeyError as e:
                log.error(f"Missing key in custom theme '{theme_data.get('name', 'N/A')}': {e}")
    except json.JSONDecodeError as e:
        log.error(f"Error decoding custom themes file: {e}")
    except Exception as e:
        log.error(f"Failed to load custom themes: {e}", exc_info=True)
    
    return themes
