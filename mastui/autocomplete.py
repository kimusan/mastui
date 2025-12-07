from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence
import logging
from time import time

from textual.widget import Widget
from textual.widgets import Static, TextArea, LoadingIndicator
from textual.containers import Vertical
from textual import events
from textual.timer import Timer
from rich.markup import escape

log = logging.getLogger(__name__)

AUTOCOMPLETE_MIN_LENGTH = 2
MAX_AUTOCOMPLETE_RESULTS = 8
WHITESPACE_CHARS = set(" \n\t\r")
VALID_TOKEN_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.@")


@dataclass(frozen=True)
class AutocompleteToken:
    kind: Literal["mention", "hashtag"]
    token: str
    query: str
    start: int
    end: int


@dataclass
class AutocompleteSuggestion:
    kind: Literal["mention", "hashtag"]
    value: str
    primary: str
    secondary: str | None = None


class AutocompleteProvider:
    """Fetch account and hashtag suggestions using the Mastodon API."""

    def __init__(self, api, config, me: dict | None = None) -> None:
        self.api = api
        self.config = config
        self.me = me or {}
        self._account_cache: dict[str, tuple[float, list[AutocompleteSuggestion]]] = {}
        self._tag_cache: dict[str, tuple[float, list[AutocompleteSuggestion]]] = {}
        self._cache_ttl = 30.0

    def get_suggestions(self, token: AutocompleteToken) -> list[AutocompleteSuggestion]:
        if token.kind == "mention":
            return self._get_account_suggestions(token)
        return self._get_tag_suggestions(token)

    def _get_account_suggestions(self, token: AutocompleteToken) -> list[AutocompleteSuggestion]:
        query = token.query.strip()
        if len(query) < AUTOCOMPLETE_MIN_LENGTH:
            return []

        cached = self._account_cache.get(query)
        if cached and time() - cached[0] < self._cache_ttl:
            return cached[1]

        suggestions: list[AutocompleteSuggestion] = []
        try:
            is_remote = "@" in query
            if is_remote:
                accounts = self.api.account_search(query, limit=10, resolve=True)
                suggestions.extend(self._map_accounts(accounts))
            else:
                # Show followed accounts first
                following = self.api.account_search(query, limit=10, following=True)
                suggestions.extend(self._map_accounts(following))
                # Then fall back to local directory
                local_candidates = self.api.account_search(query, limit=10, resolve=False)
                for account in local_candidates:
                    if self._is_local_account(account):
                        suggestions.append(self._build_account_suggestion(account))
        except Exception as exc:  # pragma: no cover - Mastodon errors handled at runtime
            log.warning("Account autocomplete failed for '%s': %s", query, exc)
            suggestions = []

        unique = self._deduplicate(suggestions)[:MAX_AUTOCOMPLETE_RESULTS]
        self._account_cache[query] = (time(), unique)
        return unique

    def _get_tag_suggestions(self, token: AutocompleteToken) -> list[AutocompleteSuggestion]:
        query = token.query.strip("#")
        if len(query) < AUTOCOMPLETE_MIN_LENGTH:
            return []

        cached = self._tag_cache.get(query)
        if cached and time() - cached[0] < self._cache_ttl:
            return cached[1]

        suggestions: list[AutocompleteSuggestion] = []
        try:
            if hasattr(self.api, "tag_search"):
                tags = self.api.tag_search(query)
            elif hasattr(self.api, "search_v2"):
                response = self.api.search_v2(
                    q=query,
                    resolve=False,
                    result_type="hashtags",
                    exclude_unreviewed=False,
                )
                if isinstance(response, dict):
                    tags = response.get("hashtags", [])
                else:
                    tags = getattr(response, "hashtags", []) or []
            else:
                tags = []
            for tag in tags or []:
                suggestions.append(self._build_tag_suggestion(tag))
        except Exception as exc:  # pragma: no cover
            log.warning("Tag autocomplete failed for '%s': %s", query, exc)
            suggestions = []

        unique = self._deduplicate(suggestions)[:MAX_AUTOCOMPLETE_RESULTS]
        self._tag_cache[query] = (time(), unique)
        return unique

    def _map_accounts(self, accounts: Sequence[dict] | None) -> list[AutocompleteSuggestion]:
        if not accounts:
            return []
        mapped = []
        for account in accounts:
            mapped.append(self._build_account_suggestion(account))
        return mapped

    def _build_account_suggestion(self, account: dict) -> AutocompleteSuggestion:
        acct = account.get("acct") or ""
        display_name = account.get("display_name") or account.get("username") or acct
        primary = f"@{acct}"
        secondary = display_name if display_name != acct else None
        return AutocompleteSuggestion(
            kind="mention",
            value=f"@{acct}",
            primary=primary,
            secondary=secondary,
        )

    def _build_tag_suggestion(self, tag: dict) -> AutocompleteSuggestion:
        name = tag.get("name") or ""
        usage = self._format_tag_usage(tag.get("history"))
        return AutocompleteSuggestion(
            kind="hashtag",
            value=f"#{name}",
            primary=f"#{name}",
            secondary=usage,
        )

    def _format_tag_usage(self, history: Sequence[dict] | None) -> str | None:
        if not history:
            return None
        try:
            recent = history[0]
            uses = int(recent.get("uses", 0))
            return f"{uses} recent uses"
        except Exception:
            return None

    def _is_local_account(self, account: dict) -> bool:
        acct = account.get("acct") or ""
        if "@" not in acct:
            return True
        return acct.split("@", 1)[-1] == (self.config.mastodon_host or "")

    def _deduplicate(self, suggestions: Sequence[AutocompleteSuggestion]) -> list[AutocompleteSuggestion]:
        seen = set()
        deduped: list[AutocompleteSuggestion] = []
        for suggestion in suggestions:
            if suggestion.value in seen:
                continue
            seen.add(suggestion.value)
            deduped.append(suggestion)
        return deduped


class AutocompletePanel(Widget):
    """Simple vertical list for autocomplete suggestions."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.add_class("autocomplete-panel")
        self.add_class("hidden")
        self.suggestions: list[AutocompleteSuggestion] = []
        self.selected_index = 0
        self._rows_id = f"{self.id}-rows" if self.id else "autocomplete-rows"

    def compose(self):
        yield Vertical(id=self._rows_id)

    def set_suggestions(
        self,
        suggestions: list[AutocompleteSuggestion],
        loading: bool = False,
    ) -> None:
        rows = self._rows_container
        for child in list(rows.children):
            child.remove()

        self.suggestions = suggestions
        if not suggestions and not loading:
            self.hide()
            return
        if loading:
            indicator = LoadingIndicator()
            indicator.can_focus = False
            rows.mount(indicator)
        else:
            for suggestion in suggestions:
                label = escape(suggestion.primary)
                if suggestion.secondary:
                    label = f"{label} [dim]{escape(suggestion.secondary)}[/]"
                row = Static(label, classes="autocomplete-row")
                rows.mount(row)
        self.selected_index = 0
        self._update_selection()
        self.show()

    def move(self, offset: int) -> None:
        if not self.suggestions:
            return
        self.selected_index = (self.selected_index + offset) % len(self.suggestions)
        self._update_selection()

    def get_selected(self) -> AutocompleteSuggestion | None:
        if not self.suggestions:
            return None
        return self.suggestions[self.selected_index]

    def hide(self) -> None:
        self.add_class("hidden")

    def show(self) -> None:
        self.remove_class("hidden")

    @property
    def is_visible(self) -> bool:
        return "hidden" not in self.classes

    @property
    def _rows_container(self) -> Vertical:
        return self.query_one(f"#{self._rows_id}", Vertical)

    def _update_selection(self) -> None:
        rows = list(self._rows_container.children)
        for idx, row in enumerate(rows):
            row.set_class(idx == self.selected_index, "autocomplete-row--selected")


class ComposerAutocompleteController:
    """Attach autocomplete behavior to a compose TextArea."""

    def __init__(self, screen, text_area_id: str, panel_id: str) -> None:
        self.screen = screen
        self.text_area_id = text_area_id
        self.panel_id = panel_id
        self.text_area: TextArea | None = None
        self.panel: AutocompletePanel | None = None
        self.app = None
        self._current_token: AutocompleteToken | None = None
        self._pending_token: AutocompleteToken | None = None
        self._request_serial = 0
        self._debounce_timer: Timer | None = None
        self._debounce_interval = 0.2
        self._ignore_next_change = False

    def attach(self) -> None:
        self.text_area = self.screen.query_one(f"#{self.text_area_id}", TextArea)
        self.panel = self.screen.query_one(f"#{self.panel_id}", AutocompletePanel)
        self.app = self.screen.app

    def detach(self) -> None:
        self.text_area = None
        self.panel = None
        self._current_token = None
        self.app = None
        self._pending_token = None
        if self._debounce_timer:
            self._debounce_timer.stop()
            self._debounce_timer = None

    def on_text_changed(self) -> None:
        if self._ignore_next_change:
            self._ignore_next_change = False
            return
        if not self.text_area or not self.panel or not self.app:
            return
        provider = self.app.get_autocomplete_provider()
        if not provider:
            return
        token = extract_token(self.text_area.text, index_from_location(self.text_area.text, self.text_area.cursor_location))

        if not token:
            self.panel.hide()
            self._current_token = None
            self._pending_token = None
            if self._debounce_timer:
                self._debounce_timer.stop()
                self._debounce_timer = None
            return

        self._pending_token = token
        self._current_token = token
        self._request_serial += 1
        request_id = self._request_serial

        screen = self.screen
        panel = self.panel
        app = self.app

        def fire_request():
            if request_id != self._request_serial or not self._pending_token:
                return

            def worker():
                pending_token = self._pending_token
                suggestions = provider.get_suggestions(pending_token)

                def apply():
                    if request_id != self._request_serial or not panel:
                        return
                    entries = suggestions
                    if suggestions:
                        base = self._base_suggestion(pending_token)
                        if base:
                            entries = [base] + suggestions
                    panel.set_suggestions(entries, loading=False)

                app.call_from_thread(apply)

            app.run_worker(worker, thread=True)

        if self._debounce_timer:
            self._debounce_timer.stop()
        if self.panel and not self.panel.is_visible:
            base = self._base_suggestion(token)
            self.panel.set_suggestions([base] if base else [], loading=True)
        self._debounce_timer = self.screen.set_timer(
            self._debounce_interval, fire_request, pause=False
        )

    def handle_key(self, event: events.Key) -> bool:
        if not self.panel or not self.panel.is_visible:
            if event.key in ("ctrl+space", "tab"):
                self.on_text_changed()
                event.stop()
                return True
            return False

        if event.key == "ctrl+n":
            self.panel.move(1)
            self._update_preview(self.panel.get_selected())
            event.stop()
            return True
        if event.key == "ctrl+p":
            self.panel.move(-1)
            self._update_preview(self.panel.get_selected())
            event.stop()
            return True
        if event.key == "tab":
            self.panel.move(1)
            self._update_preview(self.panel.get_selected())
            event.stop()
            return True
        if event.key in ("ctrl+space",):
            suggestion = self.panel.get_selected()
            if suggestion:
                self._insert_suggestion(suggestion)
            event.stop()
            return True
        if event.key == "enter":
            suggestion = self.panel.get_selected()
            if suggestion:
                self._insert_suggestion(suggestion)
                event.prevent_default()
                event.stop()
                return True
            else:
                self.hide()
                return False
        if event.key == "escape":
            self.panel.hide()
            event.stop()
            return True
        return False

    def hide(self) -> None:
        if self.panel:
            self.panel.hide()

    def _insert_suggestion(self, suggestion: AutocompleteSuggestion) -> None:
        if not self.text_area or not self._current_token:
            return
        token = self._current_token
        text = self.text_area.text
        replacement = suggestion.value
        trailing = ""
        if token.end >= len(text) or text[token.end] not in WHITESPACE_CHARS:
            trailing = " "
        new_text = f"{text[:token.start]}{replacement}{trailing}{text[token.end:]}"
        self._ignore_next_change = True
        self.text_area.text = new_text
        new_index = token.start + len(replacement) + len(trailing)
        self.text_area.cursor_location = location_from_index(new_text, new_index)
        self.panel.hide()
        self._current_token = None
        self._pending_token = None

    def _update_preview(self, suggestion: AutocompleteSuggestion | None) -> None:
        if not suggestion or not self.text_area or not self._current_token:
            return
        token = self._current_token
        text = self.text_area.text
        replacement = suggestion.value
        new_text = f"{text[:token.start]}{replacement}{text[token.end:]}"
        self._ignore_next_change = True
        self.text_area.text = new_text
        new_index = token.start + len(replacement)
        self.text_area.cursor_location = location_from_index(new_text, new_index)
        self._current_token = AutocompleteToken(
            kind=token.kind,
            token=replacement,
            query=replacement[1:] if len(replacement) > 1 else "",
            start=token.start,
            end=token.start + len(replacement),
        )

    def _base_suggestion(self, token: AutocompleteToken | None) -> AutocompleteSuggestion | None:
        if not token:
            return None
        value = token.token
        return AutocompleteSuggestion(
            kind=token.kind,
            value=value,
            primary=value,
            secondary=None,
        )

def extract_token(text: str, cursor_index: int) -> AutocompleteToken | None:
    if cursor_index == 0 or cursor_index > len(text):
        return None

    start = cursor_index
    while start > 0:
        prev_char = text[start - 1]
        if prev_char in WHITESPACE_CHARS:
            break
        start -= 1

    if start == cursor_index:
        return None

    token = text[start:cursor_index]
    prefix = token[0]
    if prefix not in ("@", "#"):
        return None
    if cursor_index - start <= 1:
        return None
    # Ensure characters are valid
    body = token[1:]
    if any(ch not in VALID_TOKEN_CHARS for ch in body):
        return None
    if start > 0 and text[start - 1] not in WHITESPACE_CHARS:
        return None

    return AutocompleteToken(
        kind="mention" if prefix == "@" else "hashtag",
        token=token,
        query=body,
        start=start,
        end=cursor_index,
    )


def index_from_location(text: str, location: tuple[int, int]) -> int:
    """Convert (row, col) to absolute index."""
    lines = text.split("\n")
    row, col = location
    if row >= len(lines):
        lines.extend("" for _ in range(row - len(lines) + 1))
    index = 0
    for i in range(row):
        index += len(lines[i]) + 1
    return index + min(col, len(lines[row]))


def location_from_index(text: str, index: int) -> tuple[int, int]:
    """Convert absolute index back to (row, col)."""
    if index < 0:
        return (0, 0)
    lines = text.split("\n")
    remaining = index
    for row, line in enumerate(lines):
        if remaining <= len(line):
            return (row, remaining)
        remaining -= len(line) + 1
    # If index beyond text, clamp to end
    if lines:
        return (len(lines) - 1, len(lines[-1]))
    return (0, 0)
