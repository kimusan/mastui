from textual.widgets import Static, LoadingIndicator
from textual.containers import VerticalScroll, Horizontal
from textual.events import Key
from textual.screen import ModalScreen
from mastui.widgets import Post, Notification, LikePost, BoostPost
from mastui.reply import ReplyScreen
from mastui.thread import ThreadScreen
from mastui.profile import ProfileScreen
from mastui.messages import TimelineUpdate, FocusNextTimeline, FocusPreviousTimeline, ViewProfile
from mastui.config import config
import logging

log = logging.getLogger(__name__)


class Timeline(Static, can_focus=True):
    """A widget to display a single timeline."""

    def __init__(self, title, posts_data=None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.posts_data = posts_data
        self.selected_item = None
        self.post_ids = set()
        self.latest_post_id = None
        self.oldest_post_id = None

    @property
    def content_container(self) -> VerticalScroll:
        return self.query_one(".timeline-content", VerticalScroll)

    @property
    def loading_indicator(self) -> LoadingIndicator:
        return self.query_one(".timeline-refresh-spinner", LoadingIndicator)

    def on_mount(self):
        if self.posts_data is not None:
            self.render_posts(self.posts_data)
        else:
            self.load_posts()
        self.update_auto_refresh_timer()

    def update_auto_refresh_timer(self):
        """Starts or stops the auto-refresh timer based on the config."""
        if hasattr(self, "refresh_timer"):
            self.refresh_timer.stop()

        auto_refresh = getattr(config, f"{self.id}_auto_refresh", False)
        if auto_refresh:
            interval = getattr(config, f"{self.id}_auto_refresh_interval", 60)
            self.refresh_timer = self.set_interval(interval * 60, self.refresh_posts)

    def on_timeline_update(self, message: TimelineUpdate) -> None:
        """Handle a timeline update message."""
        self.render_posts(message.posts, since_id=message.since_id, max_id=message.max_id)

    def refresh_posts(self):
        """Refresh the timeline with new posts."""
        log.info(f"Refreshing {self.id} timeline...")
        self.loading_indicator.display = True
        self.run_worker(lambda: self.do_fetch_posts(since_id=self.latest_post_id), exclusive=True, thread=True)

    def load_posts(self):
        if self.post_ids:
            return
        log.info(f"Loading posts for {self.id} timeline...")
        self.loading_indicator.display = True
        self.run_worker(self.do_fetch_posts, thread=True)
        log.info(f"Worker requested for {self.id} timeline.")

    def do_fetch_posts(self, since_id=None, max_id=None):
        """Worker method to fetch posts and post a message with the result."""
        log.info(f"Worker thread started for {self.id}")
        try:
            posts = self.fetch_posts(since_id=since_id, max_id=max_id)
            log.info(f"Worker thread finished for {self.id}, got {len(posts)} posts.")
            self.post_message(TimelineUpdate(posts, since_id=since_id, max_id=max_id))
        except Exception as e:
            log.error(f"Worker for {self.id} failed in do_fetch_posts: {e}", exc_info=True)
            self.post_message(TimelineUpdate([]))

    def fetch_posts(self, since_id=None, max_id=None):
        api = self.app.api
        posts = []
        if api:
            try:
                log.info(f"Fetching posts for {self.id} since id {since_id} max_id {max_id}")
                limit = 20 if since_id or max_id else 10  # Fetch more when paginating
                if self.id == "home":
                    posts = api.timeline_home(since_id=since_id, max_id=max_id, limit=limit)
                elif self.id == "notifications":
                    posts = api.notifications(since_id=since_id, max_id=max_id, limit=limit)
                elif self.id == "federated":
                    posts = api.timeline_public(since_id=since_id, max_id=max_id, limit=limit)
                log.info(f"Fetched {len(posts)} new posts for {self.id}")
            except Exception as e:
                log.error(f"Error loading {self.id} timeline: {e}", exc_info=True)
                self.app.notify(f"Error loading {self.id} timeline: {e}", severity="error")
        return posts

    def load_older_posts(self):
        """Load older posts."""
        log.info(f"Loading older posts for {self.id} timeline...")
        self.loading_indicator.display = True
        self.run_worker(lambda: self.do_fetch_posts(max_id=self.oldest_post_id), exclusive=True, thread=True)

    def render_posts(self, posts_data, since_id=None, max_id=None):
        """Renders the given posts data in the timeline."""
        log.info(f"render_posts called for {self.id} with {len(posts_data)} posts.")
        self.loading_indicator.display = False
        is_initial_load = not self.post_ids

        if is_initial_load and not posts_data:
            log.info(f"No posts to render for {self.id} on initial load.")
            if self.id == "home" or self.id == "federated":
                self.content_container.mount(Static(f"{self.title} timeline is empty.", classes="status-message"))
            elif self.id == "notifications":
                self.content_container.mount(Static("No new notifications.", classes="status-message"))
            return

        if not posts_data and not is_initial_load:
            log.info(f"No new posts to render for {self.id}.")
            return

        if posts_data:
            new_latest_post_id = posts_data[0]["id"]
            if self.latest_post_id is None or new_latest_post_id > self.latest_post_id:
                self.latest_post_id = new_latest_post_id
                log.info(f"New latest post for {self.id} is {self.latest_post_id}")
            
            new_oldest_post_id = posts_data[-1]["id"]
            if self.oldest_post_id is None or new_oldest_post_id < self.oldest_post_id:
                self.oldest_post_id = new_oldest_post_id
                log.info(f"New oldest post for {self.id} is {self.oldest_post_id}")

        if is_initial_load:
            for item in self.content_container.query(".status-message"):
                item.remove()

        new_widgets = []
        for post in posts_data:
            # Create a unique ID for each notification
            if self.id == "notifications":
                status = post.get("status") or {}
                status_id = status.get("id", "")
                post_id = f"{post['type']}-{post['account']['id']}-{status_id}"
            else:
                post_id = post["id"]

            if post_id not in self.post_ids:
                self.post_ids.add(post_id)
                if self.id == "home" or self.id == "federated":
                    new_widgets.append(Post(post))
                elif self.id == "notifications":
                    new_widgets.append(Notification(post))

        if new_widgets:
            log.info(f"Mounting {len(new_widgets)} new posts in {self.id}")
            if max_id: # older posts
                self.content_container.mount_all(new_widgets)
            else: # newer posts or initial load
                self.content_container.mount_all(new_widgets, before=0)
        
        if new_widgets and is_initial_load:
            self.select_first_item()

    def on_focus(self):
        self.select_first_item()

    def on_blur(self):
        if self.selected_item:
            self.selected_item.remove_class("selected")

    def on_key(self, event: Key) -> None:
        if event.key == "left":
            self.post_message(FocusPreviousTimeline())
            event.stop()
        elif event.key == "right":
            self.post_message(FocusNextTimeline())
            event.stop()
        elif event.key in ("up", "down", "l", "b", "a", "enter", "p"):
            event.stop()
            if event.key == "up":
                self.scroll_up()
            elif event.key == "down":
                self.scroll_down()
            elif event.key == "l":
                self.like_post()
            elif event.key == "b":
                self.boost_post()
            elif event.key == "a":
                self.reply_to_post()
            elif event.key == "enter":
                self.open_thread()
            elif event.key == "p":
                self.view_profile()
        # Let other keys bubble up to the app

    def select_first_item(self):
        if self.selected_item:
            self.selected_item.remove_class("selected")
        try:
            self.selected_item = self.content_container.query(
                "Post, Notification"
            ).first()
            self.selected_item.add_class("selected")
        except Exception:
            self.selected_item = None

    def get_selected_item(self):
        return self.selected_item

    def open_thread(self):
        if isinstance(self.app.screen, ModalScreen):
            return
        if isinstance(self.selected_item, Post):
            status = self.selected_item.post.get("reblog") or self.selected_item.post
            self.app.push_screen(ThreadScreen(status["id"], self.app.api))
        elif isinstance(self.selected_item, Notification):
            if self.selected_item.notif["type"] in ["mention", "favourite", "reblog"]:
                status = self.selected_item.notif.get("status")
                if status:
                    self.app.push_screen(ThreadScreen(status["id"], self.app.api))

    def view_profile(self):
        if isinstance(self.selected_item, Post):
            status = self.selected_item.post.get("reblog") or self.selected_item.post
            account_id = status["account"]["id"]
            self.post_message(ViewProfile(account_id))
        elif isinstance(self.selected_item, Notification):
            account_id = self.selected_item.notif["account"]["id"]
            self.post_message(ViewProfile(account_id))

    def reply_to_post(self):
        if isinstance(self.app.screen, ModalScreen):
            return
        post_to_reply_to = None
        if isinstance(self.selected_item, Post):
            post_to_reply_to = self.selected_item.post.get("reblog") or self.selected_item.post
        elif isinstance(self.selected_item, Notification):
            if self.selected_item.notif["type"] == "mention":
                post_to_reply_to = self.selected_item.notif.get("status")

        if post_to_reply_to:
            self.app.push_screen(ReplyScreen(post_to_reply_to, max_characters=self.app.max_characters), self.app.on_reply_screen_dismiss)
        else:
            self.app.notify("This item cannot be replied to.", severity="error")

    def like_post(self):
        if isinstance(self.selected_item, Post):
            status_to_action = self.selected_item.post.get("reblog") or self.selected_item.post
            if not status_to_action:
                self.app.notify("Cannot like a post that has been deleted.", severity="error")
                return
            self.selected_item.show_spinner()
            self.post_message(LikePost(status_to_action["id"]))

    def boost_post(self):
        if isinstance(self.selected_item, Post):
            status_to_action = self.selected_item.post.get("reblog") or self.selected_item.post
            if not status_to_action:
                self.app.notify("Cannot boost a post that has been deleted.", severity="error")
                return
            self.selected_item.show_spinner()
            self.post_message(BoostPost(status_to_action["id"]))

    def scroll_up(self):
        items = self.content_container.query("Post, Notification")
        if self.selected_item and items:
            try:
                idx = items.nodes.index(self.selected_item)
                if idx > 0:
                    self.selected_item.remove_class("selected")
                    self.selected_item = items[idx - 1]
                    self.selected_item.add_class("selected")
                    self.selected_item.scroll_visible()
                else:
                    self.refresh_posts()
            except ValueError:
                self.select_first_item()

    def scroll_down(self):
        items = self.content_container.query("Post, Notification")
        if self.selected_item and items:
            try:
                idx = items.nodes.index(self.selected_item)
                if idx < len(items) - 1:
                    self.selected_item.remove_class("selected")
                    self.selected_item = items[idx + 1]
                    self.selected_item.add_class("selected")
                    self.selected_item.scroll_visible()
                else:
                    self.load_older_posts()
            except ValueError:
                self.select_first_item()

    def compose(self):
        with Horizontal(classes="timeline-header"):
            yield Static(self.title, classes="timeline_title")
            yield LoadingIndicator(classes="timeline-refresh-spinner")
        yield VerticalScroll(classes="timeline-content")


class Timelines(Static):
    """A widget to display the three timelines."""
    def compose(self):
        yield Timeline("Home", id="home")
        yield Timeline("Notifications", id="notifications")
        yield Timeline("Federated", id="federated")
