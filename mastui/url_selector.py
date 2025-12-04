from textual.screen import ModalScreen
from textual.widgets import Static, ListView, ListItem, Label
from textual.containers import Container, VerticalScroll
from textual.binding import Binding
from textual import on
import clipman
from urllib.parse import urlparse
import re
import logging
from html import unescape

log = logging.getLogger(__name__)


class URLSelectorScreen(ModalScreen):
    """A modal screen to display and select URLs from a post."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        Binding("1", "select_url(0)", "Select URL 1", show=False),
        Binding("2", "select_url(1)", "Select URL 2", show=False),
        Binding("3", "select_url(2)", "Select URL 3", show=False),
        Binding("4", "select_url(3)", "Select URL 4", show=False),
        Binding("5", "select_url(4)", "Select URL 5", show=False),
        Binding("6", "select_url(5)", "Select URL 6", show=False),
        Binding("7", "select_url(6)", "Select URL 7", show=False),
        Binding("8", "select_url(7)", "Select URL 8", show=False),
        Binding("9", "select_url(8)", "Select URL 9", show=False),
    ]

    def __init__(self, post_data: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self.post_data = post_data
        self.urls = []

    def compose(self):
        with Container(id="url-selector-dialog") as dialog:
            dialog.border_title = "Select URL to Copy"
            yield VerticalScroll(ListView(id="url-list"), id="url-container")

    def on_mount(self):
        self.extract_urls()
        self.render_urls()

    def extract_urls(self):
        """Extract all URLs from the post content and media."""
        urls = []

        # Get the actual status (handle reblogs)
        status = self.post_data.get("reblog") or self.post_data

        # Extract from content (HTML)
        content = status.get("content", "")
        if content:
            # Remove HTML tags but keep URLs
            # Look for href attributes in anchor tags
            href_pattern = r'href=["\']([^"\']+)["\']'
            hrefs = re.findall(href_pattern, content)
            urls.extend(hrefs)

            # Also look for plain URLs in text
            url_pattern = r'https?://[^\s< >"{}|\\^`\[\]]+'
            plain_urls = []
            for url in re.findall(url_pattern, unescape(content)):
                # Skip obviously truncated URLs (e.g., "..."/"…") that won't open correctly
                if url.endswith("...") or "…" in url:
                    log.debug(f"Skipping truncated URL candidate: {url}")
                    continue
                plain_urls.append(url)
            urls.extend(plain_urls)

        # Extract from media attachments
        media = status.get("media_attachments", [])
        for attachment in media:
            if attachment.get("url"):
                urls.append(attachment["url"])
            if attachment.get("remote_url"):
                urls.append(attachment["remote_url"])

        # Extract card URL if present
        card = status.get("card")
        if card and card.get("url"):
            urls.append(card["url"])

        # Extract poll URLs if present (less common but possible)
        poll = status.get("poll")
        if poll and poll.get("url"):
            urls.append(poll["url"])

        # Deduplicate while preserving order
        seen = set()
        self.urls = []
        for url in urls:
            # Clean up the URL
            url = url.strip()
            if not url:
                continue

            # Skip truncated or incomplete URLs like "https://www."
            parsed = urlparse(url)
            if (
                not parsed.scheme
                or not parsed.netloc
                or parsed.netloc == "www."
                or url.endswith("...")
                or "…" in url
            ):
                log.debug(f"Skipping invalid URL candidate: {url}")
                continue

            if url not in seen:
                seen.add(url)
                self.urls.append(url)

    def render_urls(self):
        """Render the list of URLs."""
        list_view = self.query_one("#url-list", ListView)

        if not self.urls:
            list_view.mount(ListItem(Label("No URLs found in this post.")))
            return

        for idx, url in enumerate(self.urls, 1):
            # Truncate very long URLs for display
            display_url = url if len(url) <= 80 else url[:77] + "..."
            list_view.mount(
                ListItem(Label(f"{idx}. {display_url}"), id=f"url-item-{idx - 1}")
            )

        # Focus the list
        list_view.focus()

    # Use the on decorator to intercept ListView's Selected message
    @on(ListView.Selected)
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle when a list item is selected (via ENTER or click)."""
        log.info(f"ListView.Selected event received: index={event.list_view.index}")
        list_view = event.list_view
        if list_view.index is not None and list_view.index < len(self.urls):
            self.copy_url(self.urls[list_view.index])
        else:
            log.warning(
                f"Invalid selection: index={list_view.index}, urls count={len(self.urls)}"
            )
            self.app.notify("No URL selected", severity="warning")

    def action_select_url(self, index: int):
        """Select a URL by its number (0-indexed)."""
        log.info(f"action_select_url called with index={index}")
        if 0 <= index < len(self.urls):
            self.copy_url(self.urls[index])
        else:
            log.warning(f"Invalid URL index: {index}")
            self.app.notify(f"No URL at position {index + 1}", severity="warning")

    def copy_url(self, url: str):
        """Copy the URL to clipboard and dismiss the screen."""
        log.info(f"Copying URL to clipboard: {url}")
        try:
            try:
                clipman.init()
            except clipman.exceptions.ClipmanBaseException as e:
                log.debug(f"Clipboard init issue (continuing): {e}", exc_info=True)

            clipman.set(url)
        except Exception as e:
            log.error(f"Failed to copy URL to clipboard: {e}", exc_info=True)
            self.app.notify(
                "Failed to copy to clipboard. "
                "Wayland users may need wl-clipboard (e.g., `sudo apt install wl-clipboard`).",
                severity="error",
            )
            return

        self.app.notify(f"Copied to clipboard: {url[:50]}...", severity="information")
        self.dismiss()
