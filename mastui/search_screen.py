from textual.screen import ModalScreen
from textual.widgets import Input, TabbedContent, TabPane, Static, LoadingIndicator
from textual.containers import Vertical, VerticalScroll
from textual import on, events
from textual.widget import Widget
from mastui.widgets import AccountResult, HashtagResult, StatusResult, SearchResult
from mastui.messages import ViewProfile
from mastui.thread import ThreadScreen
from mastui.hashtag_timeline import HashtagTimeline

class SearchScreen(ModalScreen):
    """A modal screen for searching."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Close Search"),
        ("up", "cursor_up", "Cursor Up",),
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
            yield Input(placeholder="Search for users, hashtags, or posts...", id="search-input")
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

    def on_mount(self):
        """Focus the search input when the screen is mounted."""
        self.query_one("#search-input").focus()

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle the search input being submitted."""
        query = event.value
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
            self.app.call_from_thread(self.render_results, results)
        except Exception as e:
            self.app.notify(f"Error searching: {e}", severity="error")
            self.query_one(LoadingIndicator).add_class("hidden")

    def render_results(self, results: dict):
        """Render the search results."""
        self.query_one(LoadingIndicator).add_class("hidden")
        accounts_pane = self.query_one("#search-accounts VerticalScroll")
        hashtags_pane = self.query_one("#search-hashtags VerticalScroll")
        statuses_pane = self.query_one("#search-statuses VerticalScroll")

        accounts_pane.query("*").remove()
        hashtags_pane.query("*").remove()
        statuses_pane.query("*").remove()

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
        if isinstance(focused, SearchResult):
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
