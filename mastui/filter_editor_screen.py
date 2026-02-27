from __future__ import annotations

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    Static,
    Switch,
)

from mastui.filters import (
    FILTER_ACTION_OPTIONS,
    FILTER_CONTEXT_OPTIONS,
    KEEP_CURRENT_EXPIRY_VALUE,
    build_expire_select_options,
    parse_expire_select_value,
)


class KeywordRow(ListItem):
    def __init__(self, row_id: str, keyword: str, whole_word: bool) -> None:
        super().__init__(classes="keyword-row-item")
        self.can_focus = False
        self.row_id = row_id
        self.keyword = keyword
        self.whole_word = whole_word

    def compose(self):
        with Horizontal(classes="keyword-row"):
            whole_word_label = "whole word" if self.whole_word else "partial match"
            yield Label(
                f"{self.keyword} ({whole_word_label})",
                classes="keyword-row-label",
            )
            with Horizontal(classes="keyword-row-actions"):
                yield Button(
                    "x",
                    id=f"keyword-remove-{self.row_id}",
                    classes="keyword-row-button",
                )


class KeywordPlaceholderRow(ListItem):
    def __init__(self, message: str) -> None:
        super().__init__(classes="keyword-row-item")
        self.can_focus = False
        self.message = message

    def compose(self):
        with Horizontal(classes="keyword-row"):
            yield Label(self.message, classes="language-empty keyword-row-label")


class FilterEditorScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Cancel")]

    def __init__(self, filter_data: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.filter_data = filter_data or {}
        self.keyword_rows: list[dict] = []
        self._keyword_counter = 0
        for existing_keyword in self.filter_data.get("keywords", []):
            self._append_keyword(
                keyword=str(existing_keyword.get("keyword", "")),
                whole_word=bool(existing_keyword.get("whole_word", False)),
                keyword_id=existing_keyword.get("id"),
            )

    def compose(self):
        expires_options, expires_value = build_expire_select_options(
            self.filter_data.get("expires_at")
        )
        with Vertical(id="filter-editor-dialog") as dialog:
            dialog.border_title = (
                "Edit Filter" if self.filter_data else "Create Filter"
            )
            yield Label("Title", classes="config-label")
            yield Input(self.filter_data.get("title", ""), id="filter_title")

            yield Label("Expire after", classes="config-label")
            yield Select(expires_options, value=expires_value, id="filter_expires")

            yield Label("Filter Action", classes="config-label")
            yield Select(
                FILTER_ACTION_OPTIONS,
                value=self.filter_data.get("filter_action", "warn"),
                id="filter_action",
            )

            with Vertical(classes="filter-context-group"):
                yield Static("Filter Context", classes="language-help-text")
                for label, value in FILTER_CONTEXT_OPTIONS:
                    with Horizontal(classes="filter-context-row"):
                        yield Label(label, classes="config-label")
                        yield Switch(
                            value=value in set(self.filter_data.get("context", [])),
                            id=f"filter-context-{value}",
                        )

            with Vertical(classes="keyword-config-group"):
                yield Static(
                    "Keywords",
                    classes="language-help-text",
                )
                with ListView(id="keyword_rows_list"):
                    for row in self._keyword_row_widgets():
                        yield row
                with Horizontal(id="keyword_add_controls"):
                    yield Input(placeholder="keyword or phrase", id="keyword_add_input")
                    with Horizontal(classes="keyword-toggle-wrap"):
                        yield Label("Whole word", classes="keyword-toggle-label")
                        yield Switch(id="keyword_add_whole_word")
                    yield Button("Add", id="keyword_add_button")

            with Horizontal(id="filter-editor-buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "save":
            payload = self._build_payload()
            if payload:
                self.dismiss(payload)
            return

        if button_id == "keyword_add_button":
            self._add_keyword_from_controls()
            return

        if button_id and button_id.startswith("keyword-remove-"):
            row_id = button_id.split("keyword-remove-", 1)[1]
            self.keyword_rows = [row for row in self.keyword_rows if row["row_id"] != row_id]
            self._render_keyword_rows()
            return

        self.dismiss(None)

    def _next_keyword_row_id(self) -> str:
        self._keyword_counter += 1
        return f"kw-{self._keyword_counter}"

    def _append_keyword(
        self,
        keyword: str,
        whole_word: bool,
        keyword_id: str | None = None,
    ) -> None:
        self.keyword_rows.append(
            {
                "row_id": self._next_keyword_row_id(),
                "id": keyword_id,
                "keyword": keyword,
                "whole_word": whole_word,
            }
        )

    def _keyword_row_widgets(self):
        if not self.keyword_rows:
            yield KeywordPlaceholderRow("No keywords configured yet.")
            return
        for keyword_entry in self.keyword_rows:
            yield KeywordRow(
                row_id=keyword_entry["row_id"],
                keyword=keyword_entry["keyword"],
                whole_word=keyword_entry["whole_word"],
            )

    def _render_keyword_rows(self) -> None:
        list_view = self.query_one("#keyword_rows_list", ListView)
        for child in list(list_view.children):
            child.remove()
        for row in self._keyword_row_widgets():
            list_view.mount(row)

    def _add_keyword_from_controls(self) -> None:
        keyword_input = self.query_one("#keyword_add_input", Input)
        whole_word_switch = self.query_one("#keyword_add_whole_word", Switch)
        text = keyword_input.value.strip()
        if not text:
            self.app.notify("Type a keyword or phrase first.", severity="warning")
            return

        normalized_key = (text.casefold(), whole_word_switch.value)
        existing_keys = {
            (str(row["keyword"]).casefold(), bool(row["whole_word"]))
            for row in self.keyword_rows
        }
        if normalized_key in existing_keys:
            self.app.notify("That keyword is already in the list.", severity="warning")
            return

        self._append_keyword(text, whole_word_switch.value)
        keyword_input.value = ""
        whole_word_switch.value = False
        self._render_keyword_rows()

    def _collect_contexts(self) -> list[str]:
        selected: list[str] = []
        for _, value in FILTER_CONTEXT_OPTIONS:
            switch = self.query_one(f"#filter-context-{value}", Switch)
            if switch.value:
                selected.append(value)
        return selected

    def _build_payload(self) -> dict | None:
        title = self.query_one("#filter_title", Input).value.strip()
        if not title:
            self.app.notify("Title is required.", severity="warning")
            return None

        contexts = self._collect_contexts()
        if not contexts:
            self.app.notify("Select at least one filter context.", severity="warning")
            return None

        if not self.keyword_rows:
            self.app.notify("Add at least one keyword.", severity="warning")
            return None

        action_select = self.query_one("#filter_action", Select)
        action_value = action_select.value
        if action_value == Select.BLANK:
            self.app.notify("Select a filter action.", severity="warning")
            return None

        expires_select = self.query_one("#filter_expires", Select)
        expires_value = expires_select.value
        if expires_value == Select.BLANK:
            self.app.notify("Select an expiry option.", severity="warning")
            return None

        update_expires = True
        expires_in = None
        if expires_value == KEEP_CURRENT_EXPIRY_VALUE:
            update_expires = False
        else:
            expires_in = parse_expire_select_value(str(expires_value))

        return {
            "title": title,
            "context": contexts,
            "filter_action": str(action_value),
            "expires_in": expires_in,
            "update_expires": update_expires,
            "keywords": [
                {
                    "id": row["id"],
                    "keyword": row["keyword"],
                    "whole_word": row["whole_word"],
                }
                for row in self.keyword_rows
            ],
        }
