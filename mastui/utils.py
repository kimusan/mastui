import html2text
import re
from datetime import datetime, timezone
from dateutil.parser import parse
from bs4 import BeautifulSoup

LANGUAGE_OPTIONS = [
    ("Chinese", "zh"),
    ("Danish", "da"),
    ("English", "en"),
    ("French", "fr"),
    ("German", "de"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Spanish", "es"),
]

MARKDOWN_LINK_REGEX = re.compile(r'\\[^\\]+\\]\(([^)]+)\\\)')

def markdown_links_to_html(text: str) -> str:
    """Converts Markdown-style links in a string to HTML <a> tags."""
    if not text:
        return ""
    return MARKDOWN_LINK_REGEX.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text)

def to_markdown(html: str) -> str:
    """
    Converts mixed HTML/Markdown content to terminal-friendly markdown.
    """
    if not html:
        return ""

    # First, parse with BeautifulSoup to handle HTML and decode entities.
    soup = BeautifulSoup(html, 'html.parser')
    
    # Convert the parsed soup back to a string.
    cleaned_html = str(soup)

    # Now, convert any remaining Markdown-style links to HTML <a> tags.
    html_with_links = markdown_links_to_html(cleaned_html)

    # Finally, convert the fully-HTML content to terminal-friendly text.
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0 # Don't wrap lines
    return h.handle(html_with_links)

def get_full_content_md(status: dict) -> str:
    """Gets the full markdown content for a status, including media."""
    if not status:
        return ""

    html_content = status.get("content") or status.get("note") or ""
    
    content_md = to_markdown(html_content)

    if status.get("media_attachments"):
        media_infos = []
        for media in status["media_attachments"]:
            media_type = media.get("type", "media").capitalize()
            description = media.get("description")

            if description:
                media_infos.append(f"[{media_type} showing: {description}]")
            else:
                media_infos.append(f"[{media_type} attached]")

        if content_md.strip():
            content_md += "\n\n" + "\n".join(media_infos)
        else:
            content_md = "\n".join(media_infos)

    return content_md



def format_datetime(dt_obj):
    """Formats a datetime string or object into YYYY-MM-DD HH:MM."""
    if isinstance(dt_obj, str):
        dt = parse(dt_obj)
    else:
        dt = dt_obj

    # Convert to local timezone for display
    local_dt = dt.astimezone()

    return local_dt.strftime("%Y-%m-%d %H:%M")
