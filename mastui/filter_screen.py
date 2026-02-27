from __future__ import annotations

import logging

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, LoadingIndicator, Static

from mastui.confirm_dialog import ConfirmDeleteScreen
from mastui.filter_editor_screen import FilterEditorScreen
from mastui.filter_service import create_filter, delete_filter, list_filters, update_filter
from mastui.filters import (
    format_filter_action,
    format_filter_contexts,
    format_filter_expiry,
)

log = logging.getLogger(__name__)


class FilterRow(ListItem):
    def __init__(self, filter_data: dict) -> None:
        super().__init__(classes="filter-row-item")
        self.can_focus = False
        self.filter_data = filter_data

    def compose(self):
        filter_id = str(self.filter_data["id"])
        title = self.filter_data.get("title", "")
        action = format_filter_action(self.filter_data.get("filter_action"))
        contexts = format_filter_contexts(self.filter_data.get("context", []))
        expires = format_filter_expiry(self.filter_data.get("expires_at"))
        keyword_count = len(self.filter_data.get("keywords") or [])

        with Horizontal(classes="filter-row"):
            yield Label(
                f"{title} | {action} | {contexts} | Expires: {expires} | Keywords: {keyword_count}",
                classes="filter-row-label",
            )
            with Horizontal(classes="filter-row-actions"):
                yield Button("Edit", id=f"filter-edit-{filter_id}", classes="filter-row-button")
                yield Button("Delete", id=f"filter-delete-{filter_id}", classes="filter-row-button")


class FiltersScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Close Filters")]

    def __init__(self, api, **kwargs) -> None:
        super().__init__(**kwargs)
        self.api = api
        self.filters: list[dict] = []

    def compose(self):
        with Vertical(id="filters-dialog") as dialog:
            dialog.border_title = "Mastodon Filters"
            yield Static(
                "Filters are server-side and apply anywhere you use this account.",
                classes="language-help-text",
            )
            yield LoadingIndicator(id="filters-loading")
            with ListView(id="filters_rows_list"):
                yield Static("Loading filters...", classes="status-message")
            with Horizontal(id="filters-buttons"):
                yield Button("Add", id="filters-add-button")
                yield Button("Refresh", id="filters-refresh-button")
                yield Button("Close", id="filters-close-button")

    def on_mount(self) -> None:
        self._set_loading(False)
        self.load_filters()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "filters-add-button":
            self.app.push_screen(FilterEditorScreen(), self._on_create_filter)
            return
        if button_id == "filters-refresh-button":
            self.load_filters()
            return
        if button_id == "filters-close-button":
            self.dismiss()
            return
        if button_id and button_id.startswith("filter-edit-"):
            filter_id = button_id.split("filter-edit-", 1)[1]
            existing = self._find_filter(filter_id)
            if existing is None:
                self.app.notify("Could not find selected filter.", severity="error")
                return
            self.app.push_screen(
                FilterEditorScreen(existing),
                lambda result, target=existing: self._on_edit_filter(result, target),
            )
            return
        if button_id and button_id.startswith("filter-delete-"):
            filter_id = button_id.split("filter-delete-", 1)[1]
            existing = self._find_filter(filter_id)
            if existing is None:
                self.app.notify("Could not find selected filter.", severity="error")
                return
            self.app.push_screen(
                ConfirmDeleteScreen("Delete this filter?"),
                lambda confirmed, target=existing: self._on_delete_confirmed(
                    confirmed, target
                ),
            )

    def load_filters(self) -> None:
        self._set_loading(True)
        self.run_worker(self._load_filters_worker, thread=True, exclusive=True)

    def _load_filters_worker(self) -> None:
        try:
            filters = list_filters(self.api)
            self.app.call_from_thread(self._set_filters, filters)
        except Exception as exc:
            log.error("Failed to load filters: %s", exc, exc_info=True)
            self.app.call_from_thread(
                self.app.notify, f"Failed to load filters: {exc}", severity="error"
            )
        finally:
            self.app.call_from_thread(self._set_loading, False)

    def _set_loading(self, loading: bool) -> None:
        spinner = self.query_one("#filters-loading", LoadingIndicator)
        spinner.display = loading

    def _set_filters(self, filters: list[dict]) -> None:
        self.filters = filters
        self._render_filter_rows()

    def _render_filter_rows(self) -> None:
        list_view = self.query_one("#filters_rows_list", ListView)
        for child in list(list_view.children):
            child.remove()
        if not self.filters:
            list_view.mount(Static("No filters configured.", classes="language-empty"))
            return
        for filter_data in self.filters:
            list_view.mount(FilterRow(filter_data))

    def _find_filter(self, filter_id: str) -> dict | None:
        for filter_data in self.filters:
            if str(filter_data.get("id")) == str(filter_id):
                return filter_data
        return None

    def _on_create_filter(self, payload: dict | None) -> None:
        if not payload:
            return
        self._set_loading(True)
        self.run_worker(
            lambda: self._create_filter_worker(payload),
            thread=True,
            exclusive=True,
        )

    def _create_filter_worker(self, payload: dict) -> None:
        try:
            create_filter(self.api, payload)
            filters = list_filters(self.api)
            self.app.call_from_thread(self._set_filters, filters)
            self.app.call_from_thread(
                self.app.notify,
                "Filter created.",
                severity="information",
            )
        except Exception as exc:
            log.error("Failed to create filter: %s", exc, exc_info=True)
            self.app.call_from_thread(
                self.app.notify, f"Failed to create filter: {exc}", severity="error"
            )
        finally:
            self.app.call_from_thread(self._set_loading, False)

    def _on_edit_filter(self, payload: dict | None, existing_filter: dict) -> None:
        if not payload:
            return
        self._set_loading(True)
        self.run_worker(
            lambda: self._update_filter_worker(existing_filter, payload),
            thread=True,
            exclusive=True,
        )

    def _update_filter_worker(self, existing_filter: dict, payload: dict) -> None:
        try:
            update_filter(self.api, existing_filter, payload)
            filters = list_filters(self.api)
            self.app.call_from_thread(self._set_filters, filters)
            self.app.call_from_thread(
                self.app.notify,
                "Filter updated.",
                severity="information",
            )
        except Exception as exc:
            log.error("Failed to update filter: %s", exc, exc_info=True)
            self.app.call_from_thread(
                self.app.notify, f"Failed to update filter: {exc}", severity="error"
            )
        finally:
            self.app.call_from_thread(self._set_loading, False)

    def _on_delete_confirmed(self, confirmed: bool | None, filter_data: dict) -> None:
        if not confirmed:
            return
        self._set_loading(True)
        self.run_worker(
            lambda: self._delete_filter_worker(filter_data),
            thread=True,
            exclusive=True,
        )

    def _delete_filter_worker(self, filter_data: dict) -> None:
        try:
            delete_filter(self.api, str(filter_data["id"]))
            filters = list_filters(self.api)
            self.app.call_from_thread(self._set_filters, filters)
            self.app.call_from_thread(
                self.app.notify,
                "Filter deleted.",
                severity="information",
            )
        except Exception as exc:
            log.error("Failed to delete filter: %s", exc, exc_info=True)
            self.app.call_from_thread(
                self.app.notify, f"Failed to delete filter: {exc}", severity="error"
            )
        finally:
            self.app.call_from_thread(self._set_loading, False)
