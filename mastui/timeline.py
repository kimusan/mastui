from textual.widgets import Static, LoadingIndicator
from textual.containers import VerticalScroll, Horizontal
from textual import on, events
from textual.screen import ModalScreen
from mastui.widgets import Post, Notification, GapIndicator, LikePost, BoostPost
from mastui.reply import ReplyScreen
from mastui.thread import ThreadScreen
from mastui.profile import ProfileScreen
from mastui.messages import TimelineUpdate, FocusNextTimeline, FocusPreviousTimeline, ViewProfile, SelectPost
from mastui.config import config
from mastui.cache import cache
import logging
from datetime import datetime, timezone, timedelta

log = logging.getLogger(__name__)

MAX_POSTS_IN_UI = 70


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
        self.loading_more = False

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
        if self.loading_more:
            return
        self.loading_more = True
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
        log.info(f"Worker thread started for {self.id} with since_id={since_id}, max_id={max_id}")
        try:
            # Case 1: Refreshing for newer posts (always hits the server)
            if since_id:
                posts = self.fetch_posts(since_id=since_id)
                if posts:
                    cache.bulk_insert_posts(self.id, posts)
                self.post_message(TimelineUpdate(posts, since_id=since_id))
                return

            # Case 2: Scrolling down for older posts
            if max_id:
                cached_posts = cache.get_posts(self.id, limit=20, max_id=max_id)
                if cached_posts:
                    log.info(f"Loaded {len(cached_posts)} older posts from cache for {self.id}")
                    self.post_message(TimelineUpdate(cached_posts, max_id=max_id))
                    return # We're done for now, wait for next scroll

                # If cache is exhausted for this scroll, fetch from server
                log.info(f"Cache exhausted for {self.id}, fetching older from server.")
                server_posts = self.fetch_posts(max_id=max_id)
                if server_posts:
                    cache.bulk_insert_posts(self.id, server_posts)
                self.post_message(TimelineUpdate(server_posts, max_id=max_id))
                return

            # Case 3: Initial load (no since_id or max_id)
            latest_cached_ts = cache.get_latest_post_timestamp(self.id)
            if latest_cached_ts and (datetime.now(timezone.utc) - latest_cached_ts) < timedelta(hours=2):
                log.info(f"Gap is small for {self.id}, filling it.")
                latest_cached_id = self.get_latest_post_id_from_cache()
                gap_posts = self.fetch_posts(since_id=latest_cached_id)
                if gap_posts:
                    cache.bulk_insert_posts(self.id, gap_posts)
                
                all_posts = cache.get_posts(self.id, limit=20)
                self.post_message(TimelineUpdate(all_posts))
            else:
                log.info(f"Gap is large or cache is empty for {self.id}, fetching latest.")
                posts = self.fetch_posts(limit=10)
                if posts:
                    cache.bulk_insert_posts(self.id, posts)
                self.post_message(TimelineUpdate(posts))

        except Exception as e:
            log.error(f"Worker for {self.id} failed in do_fetch_posts: {e}", exc_info=True)
            self.post_message(TimelineUpdate([]))

    def get_latest_post_id_from_cache(self):
        """Helper to get the ID of the very latest post in the cache."""
        latest_posts = cache.get_posts(self.id, limit=1)
        if latest_posts:
            return latest_posts[0]['id']
        return None

    def fetch_posts(self, since_id=None, max_id=None, limit=None):
        api = self.app.api
        posts = []
        if api:
            try:
                if limit is None:
                    limit = 20 if since_id or max_id else 10
                log.info(f"Fetching posts for {self.id} since id {since_id} max_id {max_id} limit {limit}")
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
        if self.loading_more:
            return
        self.loading_more = True
        log.info(f"Loading older posts for {self.id} timeline...")
        self.loading_indicator.display = True
        self.run_worker(lambda: self.do_fetch_posts(max_id=self.oldest_post_id), exclusive=True, thread=True)

    def render_posts(self, posts_data, since_id=None, max_id=None):
        """Renders the given posts data in the timeline."""
        log.info(f"render_posts called for {self.id} with {len(posts_data)} posts.")
        self.loading_indicator.display = False
        self.loading_more = False
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
            if max_id: # This was a request for older posts
                self.content_container.mount(Static("End of timeline", classes="end-of-timeline"))
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
            widget_id = ""
            if self.id == "notifications":
                status = post.get("status") or {}
                status_id = status.get("id", "")
                unique_part = f"{post['type']}-{post['account']['id']}-{status_id}"
                widget_id = f"notif-{unique_part}"
            else:
                widget_id = f"post-{post['id']}"

            if widget_id not in self.post_ids:
                self.post_ids.add(widget_id)
                if self.id == "home" or self.id == "federated":
                    new_widgets.append(Post(post, timeline_id=self.id, id=widget_id))
                elif self.id == "notifications":
                    new_widgets.append(Notification(post, id=widget_id))

        if new_widgets:
            log.info(f"Mounting {len(new_widgets)} new posts in {self.id}")
            if max_id:  # older posts
                # Check for gap
                first_new_post_ts = new_widgets[0].get_created_at()
                last_old_post = self.content_container.query("Post, Notification").last()

                if last_old_post and first_new_post_ts:
                    last_old_post_ts = last_old_post.get_created_at()
                    if last_old_post_ts and first_new_post_ts < last_old_post_ts - timedelta(minutes=30):
                        self.content_container.mount(GapIndicator())

                self.content_container.mount_all(new_widgets)
            else:  # newer posts or initial load
                self.content_container.mount_all(new_widgets, before=0)
        
        if new_widgets and is_initial_load:
            self.select_first_item()

        prune_direction = "top" if max_id else "bottom"
        self.prune_posts(direction=prune_direction)

    def prune_posts(self, direction: str = "bottom"):
        """Removes posts from the UI if there are too many."""
        all_posts = self.content_container.query("Post, Notification")
        if len(all_posts) > MAX_POSTS_IN_UI:
            log.info(f"Pruning posts in {self.id} from the {direction}. Have {len(all_posts)}, max {MAX_POSTS_IN_UI}")
            
            num_to_remove = len(all_posts) - MAX_POSTS_IN_UI
            if direction == "bottom":
                posts_to_remove = all_posts[-num_to_remove:]
            else: # direction == "top"
                posts_to_remove = all_posts[:num_to_remove]

            for post in posts_to_remove:
                if self.selected_item is not post:
                    self.post_ids.discard(post.id)
                    post.remove()

    def on_focus(self):
        if not self.selected_item:
            self.select_first_item()

    def on_blur(self):
        if self.selected_item:
            self.selected_item.remove_class("selected")

    @on(SelectPost)
    def on_select_post(self, message: SelectPost) -> None:
        if self.selected_item:
            self.selected_item.remove_class("selected")
        self.selected_item = message.post_widget
        self.selected_item.add_class("selected")
        self.focus()

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        if self.content_container.scroll_y >= self.content_container.max_scroll_y - 2:
            if not self.loading_more:
                self.load_older_posts()

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        if self.content_container.scroll_y == 0:
            if not self.loading_more:
                self.refresh_posts()

    def on_key(self, event: events.Key) -> None:
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
            items = self.content_container.query("Post, Notification")
            if items:
                self.selected_item = items.first()
                self.selected_item.add_class("selected")
            else:
                self.selected_item = None
        except Exception as e:
            log.error(f"Could not select first item in timeline: {e}", exc_info=True)
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
            self.post_message(LikePost(status_to_action["id"], status_to_action.get("favourited", False)))

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
            except ValueError as e:
                log.error(f"Could not scroll up in timeline: {e}", exc_info=True)
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
            except ValueError as e:
                log.error(f"Could not scroll down in timeline: {e}", exc_info=True)
                self.select_first_item()

    def compose(self):
        with Horizontal(classes="timeline-header"):
            yield Static(self.title, classes="timeline_title")
            yield LoadingIndicator(classes="timeline-refresh-spinner")
        yield VerticalScroll(classes="timeline-content")


class Timelines(Static):
    """A widget to display the three timelines."""
    def compose(self):
        if config.home_timeline_enabled:
            yield Timeline("Home", id="home")
        if config.notifications_timeline_enabled:
            yield Timeline("Notifications", id="notifications")
        if config.federated_timeline_enabled:
            yield Timeline("Federated", id="federated")

    def on_mount(self) -> None:
        """Focus the first timeline when mounted."""
        try:
            first_timeline = self.query(Timeline).first()
            if first_timeline:
                first_timeline.focus()
        except Exception as e:
            log.error(f"Could not focus first timeline: {e}", exc_info=True)
