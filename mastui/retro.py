# A retro green-on-black theme for Textual.
# Based on the original Textual retro theme.

from textual.theme import Theme

retro_theme_builtin = Theme(
    name="retro-green-builtin",
    primary="#00FF00",
    secondary="#008000",
    accent="#00C000",
    foreground="#A0A0A0",
    background="#0F0F0F",
    surface="#1A1A1A",
    panel="#1A1A1A",
    success="#00FF00",
    warning="#FFFF00",
    error="#FF0000",
    dark=True,
)

retro_theme_builtin.styles = {
    "app": "bg: #0F0F0F text: #A0A0A0",
    "header": "bg: #1A1A1A text: #E0E0E0",
    "footer": "bg: #1A1A1A text: #A0A0A0",
    "timeline_title": "text: #00FF00 bold",
    "timeline-item.selected": "bg: #1A1A1A",
    "Timeline:focus .timeline-item.selected": "bg: #00FF00 40%",
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
}
