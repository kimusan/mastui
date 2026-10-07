"""Theme management for Mastui on Espresso TUI."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CUSTOM_THEMES_PATH = Path.home() / ".config" / "mastui" / "custom-themes.json"


@dataclass(frozen=True)
class Theme:
    """Color palette and styles for the application."""

    name: str
    label: str
    primary: str
    secondary: str
    accent: str
    border: str
    border_active: str
    border_dim: str
    success: str
    warning: str
    error: str
    text_primary: str
    text_muted: str
    bg: str = "#12111A"
    surface: str = "#1E1E2E"
    surface_active: str = "#2A2A40"
    header_bg: str = "#221E30"
    tag_color: str = "#00E5FF"
    mention_color: str = "#BB86FC"
    scrollbar_thumb: str = "#7D56F4"
    scrollbar_track: str = "#2A2A40"


BUILTIN_THEMES: dict[str, Theme] = {
    "espresso": Theme(
        name="espresso",
        label="Espresso (Default)",
        primary="#00E5FF",
        secondary="#7D56F4",
        accent="#FFB300",
        border="#7D56F4",
        border_active="#00E5FF",
        border_dim="#3A3650",
        success="#00E676",
        warning="#FFB300",
        error="#FF5555",
        text_primary="#FFFFFF",
        text_muted="#8888AA",
        bg="#12111A",
        surface="#1B1A26",
        surface_active="#2E2442",
        header_bg="#221E30",
        tag_color="#00E5FF",
        mention_color="#BB86FC",
        scrollbar_thumb="#7D56F4",
        scrollbar_track="#252438",
    ),
    "retro-green": Theme(
        name="retro-green",
        label="Retro Green (Matrix/Amber)",
        primary="#00FF66",
        secondary="#00CC44",
        accent="#33FF33",
        border="#006611",
        border_active="#00FF66",
        border_dim="#003308",
        success="#00FF66",
        warning="#FFEE00",
        error="#FF3333",
        text_primary="#33FF77",
        text_muted="#009933",
        bg="#000D00",
        surface="#001A04",
        surface_active="#003D0C",
        header_bg="#002206",
        tag_color="#00FF66",
        mention_color="#88FF88",
        scrollbar_thumb="#00FF66",
        scrollbar_track="#002800",
    ),
    "dracula": Theme(
        name="dracula",
        label="Dracula",
        primary="#BD93F9",
        secondary="#FF79C6",
        accent="#50FA7B",
        border="#6272A4",
        border_active="#FF79C6",
        border_dim="#383A4C",
        success="#50FA7B",
        warning="#F1FA8C",
        error="#FF5555",
        text_primary="#F8F8F2",
        text_muted="#6272A4",
        bg="#1E1F29",
        surface="#282A36",
        surface_active="#44475A",
        header_bg="#21222C",
        tag_color="#FF79C6",
        mention_color="#BD93F9",
        scrollbar_thumb="#BD93F9",
        scrollbar_track="#282A36",
    ),
    "nord": Theme(
        name="nord",
        label="Nord (Arctic)",
        primary="#88C0D0",
        secondary="#81A1C1",
        accent="#EBCB8B",
        border="#4C566A",
        border_active="#88C0D0",
        border_dim="#3B4252",
        success="#A3BE8C",
        warning="#EBCB8B",
        error="#BF616A",
        text_primary="#ECEFF4",
        text_muted="#9AA5B8",
        bg="#242933",
        surface="#2E3440",
        surface_active="#3B4252",
        header_bg="#2E3440",
        tag_color="#88C0D0",
        mention_color="#81A1C1",
        scrollbar_thumb="#88C0D0",
        scrollbar_track="#2E3440",
    ),
    "catppuccin": Theme(
        name="catppuccin",
        label="Catppuccin Mocha",
        primary="#CBA6F7",
        secondary="#74C7EC",
        accent="#FAB387",
        border="#585B70",
        border_active="#CBA6F7",
        border_dim="#313244",
        success="#A6E3A1",
        warning="#F9E2AF",
        error="#F38BA8",
        text_primary="#CDD6F4",
        text_muted="#A6ADC8",
        bg="#181825",
        surface="#1E1E2E",
        surface_active="#313244",
        header_bg="#181825",
        tag_color="#F5C2E7",
        mention_color="#CBA6F7",
        scrollbar_thumb="#CBA6F7",
        scrollbar_track="#1E1E2E",
    ),
    "cyberpunk": Theme(
        name="cyberpunk",
        label="Cyberpunk 2077",
        primary="#00F0FF",
        secondary="#FF007F",
        accent="#FFE600",
        border="#FF007F",
        border_active="#00F0FF",
        border_dim="#5C0F6E",
        success="#00FF66",
        warning="#FFE600",
        error="#FF003C",
        text_primary="#FFF0F5",
        text_muted="#FF80BF",
        bg="#0D0214",
        surface="#1D0729",
        surface_active="#3B0A52",
        header_bg="#240533",
        tag_color="#FFE600",
        mention_color="#00F0FF",
        scrollbar_thumb="#00F0FF",
        scrollbar_track="#260033",
    ),
}


def load_all_themes() -> dict[str, Theme]:
    """Return all available themes, including custom themes from custom-themes.json."""
    themes = dict(BUILTIN_THEMES)
    if CUSTOM_THEMES_PATH.exists():
        try:
            data = json.loads(CUSTOM_THEMES_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    name = item.get("name")
                    palettes = item.get("palettes", {})
                    if name and palettes:
                        themes[name] = Theme(
                            name=name,
                            label=f"Custom: {name}",
                            primary=palettes.get("primary", "#00FF00"),
                            secondary=palettes.get("secondary", "#008000"),
                            accent=palettes.get("accent", "#00C000"),
                            border=palettes.get("secondary", "#008000"),
                            border_active=palettes.get("primary", "#00FF00"),
                            border_dim="#222222",
                            success=palettes.get("success", "#00FF00"),
                            warning=palettes.get("warning", "#FFFF00"),
                            error=palettes.get("error", "#FF0000"),
                            text_primary=palettes.get("foreground", "#FFFFFF"),
                            text_muted="#777777",
                            scrollbar_thumb=palettes.get("scrollbar_thumb") or palettes.get("secondary", "#7D56F4"),
                            scrollbar_track=palettes.get("scrollbar_track") or palettes.get("surface", "#2A2A40"),
                        )
        except Exception:
            pass
    return themes


def get_theme(theme_name: str | None = None) -> Theme:
    """Retrieve theme by name, falling back to 'espresso'."""
    all_themes = load_all_themes()
    if theme_name and theme_name in all_themes:
        return all_themes[theme_name]
    return all_themes["espresso"]
