import logging
from textual import events, on
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Input, LoadingIndicator, Static, TabbedContent, TabPane
from mastui.conversation_screen import ConversationScreen
from mastui.hashtag_timeline import HashtagTimeline
from mastui.messages import ViewProfile
from mastui.thread import ThreadScreen
from mastui.widgets import (
    AccountResult,
    ConversationSummary,
    HashtagResult,
    SearchResult,
    StatusResult,
)

log = logging.getLogger(__name__)


class SearchScreen(ModalScreen):
    """A modal screen for searching."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Close Search"),
        ("up", "cursor_up", "Cursor Up"),
        ("down", "cursor_down", "Cursor Down"),
        ("enter", "select_result", "Select"),
        ("p", "view_profile", "View Profile"),
    ]

    def __init__(self, api, **kwargs):
        super().__init__(**kwargs)
        self.api = api

    def compose(self):
        with Vertical(id="search-dialog") as sd:
            sd.border_title = "Search"
            yield Input(
                placeholder="Search for users, hashtags, posts, or messages...",
                id="search-input",
            )
            yield LoadingIndicator(classes="hidden")
            with TabbedContent(id="search-results"):
                with TabPane("Accounts", id="search-accounts"):
                    with VerticalScroll():
                        yield Static("Press Enter to search.", classes="search-status")
                with TabPane("Hashtags", id="search-hashtags"):
                    with VerticalScroll():
                        yield Static("Press Enter to search.", classes="search-status")
                with TabPane("Statuses", id="search-statuses"):
                    with VerticalScroll():
                        yield Static("Press Enter to search.", classes="search-status")
                with TabPane("Messages", id="search-dms"):
                    with VerticalScroll():
                        yield Static("Press Enter to search.", classes="search-status")

    def on_mount(self):
        """Focus the search input when the screen is mounted."""
        self.query_one("#search-input").focus()

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle the search input being submitted."""
        query = event.value.strip()
        if not query:
            return

        # Add a hashtag if we're on the hashtag tab
        active_tab = self.query_one(TabbedContent).active
        if active_tab == "search-hashtags" and not query.startswith("#"):
            query = f"#{query}"

        self.query_one(LoadingIndicator).remove_class("hidden")
        self.run_worker(lambda: self.do_search(query), exclusive=True, thread=True)

    def do_search(self, query: str):
        """Worker method to perform the search."""
        try:
            results = self.api.search_v2(query)
            # Search conversations if cached
            conv_results = []
            try:
                if hasattr(self.app, "cache") and self.app.cache:
                    cached_convs = self.app.cache.get_conversations()
                    q_lower = query.lower().lstrip("@")
                    for c in cached_convs:
                        accs = c.get("accounts", [])
                        last_st = c.get("last_status", {})
                        content = last_st.get("content", "") if last_st else ""
                        if (
                            any(
                                q_lower in a.get("acct", "").lower()
                                or q_lower in a.get("display_name", "").lower()
                                for a in accs
                            )
                            or q_lower in content.lower()
                        ):
                            conv_results.append(c)
            except Exception as e:
                log.debug(f"Could not search cached conversations: {e}")

            results["conversations"] = conv_results
            self.app.call_from_thread(self.render_results, results)
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Error searching: {e}", severity="error"
            )
            self.app.call_from_thread(
                self.query_one(LoadingIndicator).add_class, "hidden"
            )

    def render_results(self, results: dict):
        """Render the search results."""
        self.query_one(LoadingIndicator).add_class("hidden")
        accounts_pane = self.query_one("#search-accounts VerticalScroll")
        hashtags_pane = self.query_one("#search-hashtags VerticalScroll")
        statuses_pane = self.query_one("#search-statuses VerticalScroll")
        dms_pane = self.query_one("#search-dms VerticalScroll")

        accounts_pane.query("*").remove()
        hashtags_pane.query("*").remove()
        statuses_pane.query("*").remove()
        dms_pane.query("*").remove()

        if results.get("accounts"):
            for account in results["accounts"]:
                accounts_pane.mount(AccountResult(account))
        else:
            accounts_pane.mount(Static("No account results.", classes="search-status"))

        if results.get("hashtags"):
            for hashtag in results["hashtags"]:
                hashtags_pane.mount(HashtagResult(hashtag))
        else:
            hashtags_pane.mount(Static("No hashtag results.", classes="search-status"))

        if results.get("statuses"):
            for status in results["statuses"]:
                statuses_pane.mount(StatusResult(status))
        else:
            statuses_pane.mount(Static("No status results.", classes="search-status"))

        if results.get("conversations"):
            for conv in results["conversations"]:
                dms_pane.mount(ConversationSummary(conv))
        else:
            dms_pane.mount(Static("No direct message results.", classes="search-status"))

    @on(events.Click, ".search-result")
    def on_search_result_click(self, event: events.Click) -> None:
        """Handle a click on a search result."""
        self.select_result(event.widget)

    def action_cursor_up(self) -> None:
        """Move the cursor up."""
        self.focus_previous(SearchResult)

    def action_cursor_down(self) -> None:
        """Move the cursor down."""
        self.focus_next(SearchResult)

    def action_select_result(self) -> None:
        """Select the currently focused result."""
        focused = self.query_one("*:focus")
        if isinstance(focused, (SearchResult, ConversationSummary)):
            self.select_result(focused)

    def action_view_profile(self) -> None:
        """View the profile of the author of the focused post."""
        focused = self.query_one("*:focus")
        if isinstance(focused, AccountResult):
            self.select_result(focused)
        elif isinstance(focused, StatusResult):
            self.dismiss()
            self.post_message(ViewProfile(focused.status["account"]["id"]))

    def select_result(self, result_widget: Widget):
        """Handle a search result being selected."""
        if isinstance(result_widget, AccountResult):
            self.dismiss()
            self.post_message(ViewProfile(result_widget.account["id"]))
        elif isinstance(result_widget, StatusResult):
            self.dismiss()
            self.app.push_screen(ThreadScreen(result_widget.status["id"], self.app.api))
        elif isinstance(result_widget, HashtagResult):
            self.dismiss()
            self.app.push_screen(HashtagTimeline(result_widget.hashtag["name"], self.app.api))
        elif isinstance(result_widget, ConversationSummary):
            self.dismiss()
            conv = result_widget.conversation
            last_status_id = (
                conv.get("last_status", {}).get("id") if conv.get("last_status") else None
            )
            self.app.push_screen(ConversationScreen(conv["id"], last_status_id))
