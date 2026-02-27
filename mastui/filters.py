from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable


FILTER_CONTEXT_OPTIONS: list[tuple[str, str]] = [
    ("Home and lists", "home"),
    ("Notifications", "notifications"),
    ("Public timelines", "public"),
    ("Conversations", "thread"),
    ("Profiles", "account"),
]

FILTER_CONTEXT_LABELS = {value: label for label, value in FILTER_CONTEXT_OPTIONS}

FILTER_ACTION_OPTIONS: list[tuple[str, str]] = [
    ("Hide with a warning", "warn"),
    ("Hide completely", "hide"),
]

FILTER_ACTION_LABELS = {value: label for label, value in FILTER_ACTION_OPTIONS}

FILTER_EXPIRE_OPTIONS: list[tuple[str, str]] = [
    ("Never", "never"),
    ("30 minutes", "1800"),
    ("1 hour", "3600"),
    ("6 hours", "21600"),
    ("12 hours", "43200"),
    ("1 day", "86400"),
    ("1 week", "604800"),
    ("1 month", "2592000"),
]

KEEP_CURRENT_EXPIRY_VALUE = "__keep_current__"


def _as_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _seconds_until(expires_at: Any) -> int | None:
    expires_dt = _as_datetime(expires_at)
    if not expires_dt:
        return None
    if not expires_dt.tzinfo:
        expires_dt = expires_dt.replace(tzinfo=timezone.utc)
    delta = expires_dt - datetime.now(tz=expires_dt.tzinfo)
    return max(int(delta.total_seconds()), 0)


def format_filter_contexts(contexts: Iterable[str]) -> str:
    labels = [FILTER_CONTEXT_LABELS.get(ctx, ctx) for ctx in contexts]
    return ", ".join(labels)


def format_filter_action(action: str | None) -> str:
    if not action:
        return "-"
    return FILTER_ACTION_LABELS.get(action, action)


def format_filter_expiry(expires_at: Any) -> str:
    expires_dt = _as_datetime(expires_at)
    if not expires_dt:
        return "Never"
    return expires_dt.astimezone().strftime("%Y-%m-%d %H:%M")


def build_expire_select_options(expires_at: Any) -> tuple[list[tuple[str, str]], str]:
    options = list(FILTER_EXPIRE_OPTIONS)
    if not expires_at:
        return options, "never"

    remaining_seconds = _seconds_until(expires_at)
    if remaining_seconds is None:
        return options, "never"

    target = str(remaining_seconds)
    available_values = {value for _, value in FILTER_EXPIRE_OPTIONS}
    if target in available_values:
        return options, target

    options.insert(
        0,
        (
            f"Keep current ({format_filter_expiry(expires_at)})",
            KEEP_CURRENT_EXPIRY_VALUE,
        ),
    )
    return options, KEEP_CURRENT_EXPIRY_VALUE


def parse_expire_select_value(value: str) -> int | None:
    if value == "never":
        return None
    return int(value)


def get_status_filter_entries(status: dict | None) -> list[dict]:
    if not status:
        return []
    entries = status.get("filtered") or []
    return list(entries)


def get_status_filter_action(status: dict | None) -> str | None:
    action = None
    for entry in get_status_filter_entries(status):
        filter_data = entry.get("filter") or {}
        filter_action = str(filter_data.get("filter_action", "")).lower()
        if filter_action == "hide":
            return "hide"
        if filter_action == "warn":
            action = "warn"
    return action


def get_status_filter_titles(status: dict | None) -> list[str]:
    titles: list[str] = []
    seen = set()
    for entry in get_status_filter_entries(status):
        filter_data = entry.get("filter") or {}
        title = str(filter_data.get("title", "")).strip()
        if title and title not in seen:
            seen.add(title)
            titles.append(title)
    return titles


def get_status_filter_warning(status: dict | None) -> str | None:
    if get_status_filter_action(status) != "warn":
        return None
    titles = get_status_filter_titles(status)
    if titles:
        return f"Filtered with warning: {', '.join(titles)}"
    return "Filtered with warning."


def is_status_hidden_by_filter(status: dict | None) -> bool:
    return get_status_filter_action(status) == "hide"


def is_notification_hidden_by_filter(notification: dict | None) -> bool:
    if not notification:
        return False
    return is_status_hidden_by_filter(notification.get("status"))
