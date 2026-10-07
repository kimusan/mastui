"""Post card renderer for Espresso-based Mastui."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi
from espresso.crema.wrap import wrap_ansi
from mastui.espresso_image import (
    download_and_cache_image,
    find_cached_attachment_file,
    find_cached_image_file,
    render_halfblock_ansi,
)
from mastui.espresso_theme import get_theme

try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    PILImage = None

# ANSI & Crema Styles
REBLOG_STYLE = Style().bold(True).foreground("#00E5FF")
AUTHOR_STYLE = Style().bold(True).foreground("#FFFFFF")
ACCT_STYLE = Style().foreground("#8888AA")
TIME_STYLE = Style().faint(True)
CW_STYLE = Style().bold(True).foreground("#FFD54F").background("#332200").padding(0, 1)
TAG_STYLE = Style().bold(True).foreground("#00E5FF")
MENTION_STYLE = Style().bold(True).foreground("#BB86FC")
STATS_STYLE = Style().foreground("#AAAAAA")
FAVOURITED_STYLE = Style().bold(True).foreground("#FF4081")
REBLOGGED_STYLE = Style().bold(True).foreground("#00E676")

SELECTED_CARD_STYLE = (
    Style()
    .border(ROUNDED_BORDER)
    .border_foreground("#00E5FF")
    .padding(0, 1)
)

UNSELECTED_CARD_STYLE = (
    Style()
    .border(ROUNDED_BORDER)
    .border_foreground("#33334A")
    .padding(0, 1)
)

VISIBILITY_ICONS = {
    "public": "🌐",
    "unlisted": "🔑",
    "private": "👥",
    "direct": "🔒",
}


def clean_html(html_str: str) -> str:
    """Convert HTML snippet to clean terminal text with preserved line breaks."""
    if not html_str:
        return ""
    # Try importing html2text if available
    try:
        from mastui.utils import to_markdown
        return to_markdown(html_str).strip()
    except Exception:
        pass

    # Fallback regex strip
    text = re.sub(r"<br\s*/?>", "\n", html_str)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def highlight_social_tokens(
    text: str,
    tag_style: Style | None = None,
    mention_style: Style | None = None,
) -> str:
    """Highlight @mentions and #hashtags in post text with theme styles."""
    t_style = tag_style or TAG_STYLE
    m_style = mention_style or MENTION_STYLE

    # Mentions
    def _sub_mention(m: re.Match) -> str:
        return m_style.render(m.group(0))

    # Hashtags
    def _sub_tag(m: re.Match) -> str:
        return t_style.render(m.group(0))

    text = re.sub(r"@[a-zA-Z0-9_]+(@[a-zA-Z0-9_.-]+)?", _sub_mention, text)
    text = re.sub(r"#[a-zA-Z0-9_]+", _sub_tag, text)
    return text


def format_post_timestamp(ts: Any) -> str:
    """Format timestamp into relative or concise date/time."""
    if not ts:
        return ""
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return ts[:16]
    elif isinstance(ts, datetime):
        dt = ts
    else:
        return str(ts)
    return dt.strftime("%b %d %H:%M")


_POST_CARD_CACHE: dict[tuple, str] = {}


def render_post_card(
    post: dict,
    is_selected: bool = False,
    width: int = 70,
    show_spoiler_revealed: bool = False,
    profile_dir: Any = None,
    show_images: bool = True,
    theme: Any = None,
) -> str:
    """Render a Mastodon status dict into an Espresso Crema post card."""
    t = theme or get_theme("espresso")

    raw_status = post.get("status") or post.get("last_status") or post
    status_dict = raw_status.get("reblog") or raw_status
    post_id = str(post.get("id") or raw_status.get("id") or id(post))
    theme_name = getattr(t, "name", "espresso")
    cache_key = (
        post_id,
        is_selected,
        width,
        show_spoiler_revealed,
        show_images,
        status_dict.get("favourites_count", 0),
        status_dict.get("reblogs_count", 0),
        bool(status_dict.get("favourited")),
        bool(status_dict.get("reblogged")),
        theme_name,
    )
    if cache_key in _POST_CARD_CACHE:
        return _POST_CARD_CACHE[cache_key]

    author_style = Style().bold(True).foreground(t.text_primary)
    acct_style = Style().foreground(t.text_muted)
    time_style = Style().foreground(t.text_muted)
    reblog_style = Style().bold(True).foreground(t.primary)
    tag_style = Style().bold(True).foreground(getattr(t, "tag_color", t.primary))
    mention_style = Style().bold(True).foreground(getattr(t, "mention_color", t.secondary))
    cw_style = Style().bold(True).foreground(t.warning).background("#332200").padding(0, 1)

    bg_c = getattr(t, "surface_active", "#2A2A40") if is_selected else getattr(t, "surface", None)
    border_c = t.border_active if is_selected else t.border_dim

    # Inner content width accounts for card border (2) + padding (2)
    inner_w = max(20, width - 4)
    lines: list[str] = []

    # Handle notifications (Mentions/Favourites/Boosts/Follows)
    if "type" in post:
        notif_type = post.get("type", "")
        actor = post.get("account", {})
        actor_name = actor.get("display_name") or actor.get("username") or actor.get("acct") or "Someone"
        actor_acct = f"@{actor.get('acct', '')}"

        if notif_type == "favourite":
            lines.append(Style().bold(True).foreground("#FF4081").render(f"💖 {actor_name} {actor_acct} favourited your post"))
        elif notif_type == "reblog":
            lines.append(Style().bold(True).foreground("#00E676").render(f"🚀 {actor_name} {actor_acct} boosted your post"))
        elif notif_type == "mention":
            lines.append(Style().bold(True).foreground(mention_style).render(f"🔔 Mention from {actor_name} {actor_acct}"))
        elif notif_type == "follow":
            lines.append(Style().bold(True).foreground(t.primary).render(f"👤 {actor_name} {actor_acct} followed you"))
            note = clean_html(actor.get("note", ""))
            if note:
                lines.append(Style().italic(True).foreground(t.text_muted).render(truncate_ansi(note, inner_w)))
            content_str = "\n".join(lines)
            card_st = Style().border(ROUNDED_BORDER).border_foreground(border_c).padding(0, 1).width(inner_w)
            if bg_c:
                card_st = card_st.background(bg_c)
            return card_st.render(content_str)
        elif notif_type == "poll":
            lines.append(Style().bold(True).foreground("#FFD54F").render("📊 A poll has ended"))

    # Handle conversations (Direct Messages)
    if "last_status" in post:
        accounts = post.get("accounts", [])
        other_names = ", ".join(f"@{a.get('acct', a.get('username', ''))}" for a in accounts)
        lines.append(Style().bold(True).foreground(t.primary).render(f"✉️ Direct Conversation with {other_names}"))

    # Resolve target status (handling reblogs and wrapped notifications/conversations)
    raw_status = post.get("status") or post.get("last_status") or post
    is_reblog = bool(raw_status.get("reblog"))
    reblog_author = (
        raw_status.get("account", {}).get("display_name")
        or raw_status.get("account", {}).get("acct")
        if is_reblog
        else None
    )
    status = raw_status.get("reblog") or raw_status

    # 1. Boost indicator header
    if is_reblog and reblog_author:
        boost_header = f"🔁 Boosted by {reblog_author}"
        if string_width(boost_header) > inner_w:
            lines.append(truncate_ansi(reblog_style.render(boost_header), inner_w))
        else:
            lines.append(reblog_style.render(boost_header))

    # 2. Author & Metadata Row
    account = status.get("account", {})
    display_name = account.get("display_name") or account.get("username") or "Unknown"
    acct = f"@{account.get('acct', '')}"
    time_str = format_post_timestamp(status.get("created_at"))
    vis = status.get("visibility", "public")
    vis_icon = VISIBILITY_ICONS.get(vis, "🌐")

    author_full = f"{author_style.render(display_name)} {acct_style.render(acct)}"
    meta_part = f"{time_style.render(time_str)} {vis_icon}"
    if string_width(display_name) + string_width(acct) + string_width(meta_part) + 2 <= inner_w:
        pad_len = max(1, inner_w - string_width(author_full) - string_width(meta_part))
        lines.append(f"{author_full}{' ' * pad_len}{meta_part}")
    elif string_width(display_name) + string_width(meta_part) + 1 <= inner_w:
        pad_len = max(1, inner_w - string_width(display_name) - string_width(meta_part))
        lines.append(f"{author_style.render(display_name)}{' ' * pad_len}{meta_part}")
        lines.append(truncate_ansi(acct_style.render(acct), inner_w))
    else:
        lines.append(truncate_ansi(author_style.render(display_name), inner_w))
        sub_meta = f"{acct_style.render(acct)}  {meta_part}" if acct else meta_part
        lines.append(truncate_ansi(sub_meta, inner_w))

    # 3. Content Warning / Spoiler
    spoiler_text = status.get("spoiler_text", "")
    if spoiler_text and not show_spoiler_revealed:
        cw_full = f"⚠ CW: {spoiler_text}"
        if string_width(cw_full) > inner_w:
            for wcw in wrap_ansi(cw_full, inner_w).split("\n"):
                lines.append(cw_style.render(wcw))
        else:
            lines.append(cw_style.render(cw_full))
        lines.append(time_style.render("  [Press 's' to reveal spoiler content]"))
    else:
        if spoiler_text and show_spoiler_revealed:
            cw_full = f"⚠ CW: {spoiler_text} (Revealed)"
            if string_width(cw_full) > inner_w:
                for wcw in wrap_ansi(cw_full, inner_w).split("\n"):
                    lines.append(cw_style.render(wcw))
            else:
                lines.append(cw_style.render(cw_full))

        # 4. Body Content (word-wrapped across lines)
        body_raw = status.get("content") or status.get("text") or ""
        body_text = clean_html(body_raw)
        if body_text:
            styled_body = highlight_social_tokens(body_text, tag_style=tag_style, mention_style=mention_style)
            for paragraph in styled_body.split("\n"):
                if paragraph.strip():
                    wrapped_para = wrap_ansi(paragraph, inner_w)
                    for wrapped_line in wrapped_para.split("\n"):
                        lines.append(wrapped_line)
                else:
                    lines.append("")

    # 5. Media attachments indicator & inline thumbnail
    attachments = status.get("media_attachments", [])
    if attachments:
        for att in attachments:
            att_type = att.get("type", "media").upper()
            desc = att.get("description") or "Image attachment"
            url = str(att.get("preview_url") or att.get("url") or "")
            lines.append(Style().italic(True).foreground(getattr(t, "accent", "#80D8FF")).render(f"  📷 [{att_type}: {desc}]"))
            if show_images and PIL_AVAILABLE:
                cached_img = (
                    find_cached_attachment_file(att, profile_dir)
                    or find_cached_image_file(url, profile_dir)
                    or download_and_cache_image(url, profile_dir, allow_network=False)
                )
                if cached_img:
                    try:
                        im = PILImage.open(cached_img)
                        avail_w = max(16, inner_w - 4)
                        thumb_w = avail_w
                        thumb_h = min(18, max(8, int(thumb_w * 0.45)))
                        halfblock_str = render_halfblock_ansi(im, max_width=thumb_w, max_height=thumb_h)
                        if halfblock_str:
                            for hl in halfblock_str.splitlines():
                                pad = max(1, (inner_w - string_width(hl)) // 2)
                                lines.append(f"{' ' * pad}{hl}")
                            lines.append(Style().faint(True).foreground(t.text_muted).render("  (Press 'i' to view full resolution)"))
                    except Exception:
                        pass
                else:
                    lines.append(Style().faint(True).foreground(t.text_muted).render("  (Press 'i' to download & view attachment)"))

    # 6. Interaction Metrics Footer
    reblogs_count = status.get("reblogs_count", 0)
    favourites_count = status.get("favourites_count", 0)
    replies_count = status.get("replies_count", 0)

    is_favourited = bool(status.get("favourited"))
    is_reblogged = bool(status.get("reblogged"))

    fav_style = FAVOURITED_STYLE if is_favourited else STATS_STYLE
    reb_style = REBLOGGED_STYLE if is_reblogged else STATS_STYLE

    fav_str = fav_style.render(f"💖 {favourites_count}")
    reb_str = reb_style.render(f"🚀 {reblogs_count}")
    rep_str = STATS_STYLE.render(f"💬 {replies_count}")

    stats_line = f"{rep_str}   {reb_str}   {fav_str}"
    lines.append("")
    lines.append(stats_line)

    # Wrap inside Card Style
    clamped_lines = [truncate_ansi(l, inner_w) for l in lines]
    content_str = "\n".join(clamped_lines)
    card_style = Style().border(ROUNDED_BORDER).border_foreground(border_c).padding(0, 1)
    if bg_c:
        card_style = card_style.background(bg_c)
    rendered_card = card_style.width(inner_w).render(content_str)
    if len(_POST_CARD_CACHE) > 500:
        _POST_CARD_CACHE.clear()
    _POST_CARD_CACHE[cache_key] = rendered_card
    return rendered_card
