import html2text
import pprint
from datetime import datetime, timezone
from dateutil.parser import parse

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


def to_markdown(html):
    """Converts HTML to markdown."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    return h.handle(html)

def get_full_content_md(status):
    """Gets the full markdown content for a status, including media."""
    if not status:
        return ""
        
    html_content = status.get('content') or status.get('note') or ''
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

    if not content_md.strip():
        pretty_status = pprint.pformat(status)
        return f"**Empty Post Detected! Raw data:**\n```json\n{pretty_status}\n```"

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
