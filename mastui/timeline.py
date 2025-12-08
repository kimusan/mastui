from textual.widgets import Static, LoadingIndicator
from textual.containers import Horizontal
from textual import on, events
from textual._context import NoActiveAppError
from mastui.widgets import Post, Notification, GapIndicator, ConversationSummary
from mastui.messages import TimelineUpdate, ViewConversation
from mastui.timeline_content import TimelineContent
from mastodon import MastodonNetworkError
import logging
from datetime import datetime, timezone, timedelta

log = logging.getLogger(__name__)

MAX_POSTS_IN_UI = 70
INITIAL_RENDER_LIMIT = 20


class Timeline(Static, can_focus=True):
    """A widget to display a single timeline."""

    def __init__(self, title, posts_data=None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.posts_data = posts_data
        self.post_ids = set()
        self.latest_post_id = None
        self.oldest_post_id = None
        self.loading_more = False
        self.scroll_anchor_id = None
        self.initial_render_done = False

    @property
    def content_container(self) -> TimelineContent:
        return self.query_one(TimelineContent)

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
        self.pause_timers()
        self.resume_timers()

    def pause_timers(self):
        """Pauses the auto-refresh timer."""
        if hasattr(self, "refresh_timer"):
            self.refresh_timer.pause()
            log.debug(f"Paused auto-refresh timer for {self.id}")

    def resume_timers(self):
        """Resumes the auto-refresh timer."""
        auto_refresh = getattr(self.app.config, f"{self.id}_auto_refresh", False)
        if auto_refresh:
            if hasattr(self, "refresh_timer"):
                self.refresh_timer.resume()
                log.debug(f"Resumed auto-refresh timer for {self.id}")
            else:
                interval = getattr(
                    self.app.config, f"{self.id}_auto_refresh_interval", 60
                )
                self.refresh_timer = self.set_interval(
                    interval * 60, self.refresh_posts
                )
                log.debug(f"Started auto-refresh timer for {self.id}")

    def on_timeline_update(self, message: TimelineUpdate) -> None:
        """Handle a timeline update message."""
        self.render_posts(
            message.posts, since_id=message.since_id, max_id=message.max_id
        )

    def refresh_posts(self):
        """Refresh the timeline with new posts."""
        if self.loading_more:
            return

        # --- Start of scroll preservation logic ---
        self.scroll_anchor_id = None
        container = self.content_container
        anchor_candidate = getattr(container, "selected_item", None)
        if anchor_candidate and anchor_candidate.id:
            self.scroll_anchor_id = anchor_candidate.id
        else:
            all_items = container.query("Post, Notification, ConversationSummary")
            if not all_items:
                return  # Nothing to anchor to
            scroll_y = container.scroll_y
            for item in all_items:
                widget_region = item.virtual_region
                if widget_region.y + widget_region.height > scroll_y:
                    self.scroll_anchor_id = item.id
                    log.debug(
                        f"Set scroll anchor for {self.id} to {self.scroll_anchor_id}"
                    )
                    break
        # --- End of scroll preservation logic ---

        self.loading_more = True
        log.info(f"Refreshing {self.id} timeline...")
        self.loading_indicator.display = True
        self.run_worker(
            lambda: self.do_fetch_posts(since_id=self.latest_post_id),
            exclusive=True,
            thread=True,
        )

    def load_posts(self):
        if self.post_ids:
            return
        log.info(f"Loading posts for {self.id} timeline...")
        self.loading_indicator.display = True
        self.run_worker(self.do_fetch_posts, thread=True)
        log.info(f"Worker requested for {self.id} timeline.")

    def do_fetch_posts(self, since_id=None, max_id=None):
        """Worker method to fetch posts and post a message with the result."""
        try:
            app = self.app
        except NoActiveAppError:
            log.debug(f"App no longer active while fetching {self.id}; aborting worker.")
            return

        log.info(
            f"Worker thread started for {self.id} with since_id={since_id}, max_id={max_id}"
        )
        try:
            # Special handling for Direct Messages timeline
            if self.id == "direct":
                # Step 1: Load from cache immediately for instant UI
                cached_convos = app.cache.get_conversations()
                if cached_convos:
                    self.post_message(TimelineUpdate(cached_convos))

                # Step 2: Fetch from API in the background
                fresh_convos = self.fetch_posts()
                if fresh_convos:
                    app.cache.bulk_insert_conversations(fresh_convos)
                    self.post_message(TimelineUpdate(fresh_convos))
                return

            # Case 1: Refreshing for newer posts (always hits the server)
            if since_id:
                posts = self.fetch_posts(since_id=since_id)
                if posts:
                    app.cache.bulk_insert_posts(self.id, posts)
                    if self.id == "notifications":
                        self._handle_popups(posts)
                self.post_message(TimelineUpdate(posts, since_id=since_id))
                return

            # Case 2: Scrolling down for older posts
            if max_id:
                cached_posts = app.cache.get_posts(
                    self.id, limit=20, max_id=max_id
                )
                if cached_posts:
                    log.info(
                        f"Loaded {len(cached_posts)} older posts from cache for {self.id}"
                    )
                    self.post_message(TimelineUpdate(cached_posts, max_id=max_id))
                    return  # We're done for now, wait for next scroll

                # If cache is exhausted for this scroll, fetch from server
                log.info(f"Cache exhausted for {self.id}, fetching older from server.")
                server_posts = self.fetch_posts(max_id=max_id)
                if server_posts:
                    app.cache.bulk_insert_posts(self.id, server_posts)
                self.post_message(TimelineUpdate(server_posts, max_id=max_id))
                return

            # Case 3: Initial load (no since_id or max_id)
            latest_cached_ts = app.cache.get_latest_post_timestamp(self.id)
            if latest_cached_ts and (
                datetime.now(timezone.utc) - latest_cached_ts
            ) < timedelta(hours=2):
                log.info(f"Gap is small for {self.id}, filling it.")
                latest_cached_id = self.get_latest_post_id_from_cache(app)
                gap_posts = self.fetch_posts(since_id=latest_cached_id)
                if gap_posts:
                    app.cache.bulk_insert_posts(self.id, gap_posts)

                all_posts = app.cache.get_posts(self.id, limit=20)
                self.post_message(TimelineUpdate(all_posts))
            else:
                log.info(
                    f"Gap is large or cache is empty for {self.id}, fetching latest."
                )
                posts = self.fetch_posts(limit=10)
                if posts:
                    app.cache.bulk_insert_posts(self.id, posts)
                self.post_message(TimelineUpdate(posts))

        except Exception as e:
            log.error(
                f"Worker for {self.id} failed in do_fetch_posts: {e}", exc_info=True
            )
            self.post_message(TimelineUpdate([]))

    def get_latest_post_id_from_cache(self, app):
        """Helper to get the ID of the very latest post in the cache."""
        latest_posts = app.cache.get_posts(self.id, limit=1)
        if latest_posts:
            return latest_posts[0]["id"]
        return None

    def fetch_posts(self, since_id=None, max_id=None, limit=None):
        api = self.app.api
        posts = []
        if api:
            try:
                if limit is None:
                    limit = 20 if since_id or max_id else 10
                log.info(
                    f"Fetching posts for {self.id} since id {since_id} max_id {max_id} limit {limit}"
                )
                if self.id == "home":
                    posts = api.timeline_home(
                        since_id=since_id, max_id=max_id, limit=limit
                    )
                elif self.id == "notifications":
                    posts = api.notifications(
                        since_id=since_id, max_id=max_id, limit=limit
                    )
                elif self.id == "local":
                    posts = api.timeline_local(
                        since_id=since_id, max_id=max_id, limit=limit
                    )
                elif self.id == "federated":
                    posts = api.timeline_public(
                        since_id=since_id, max_id=max_id, limit=limit
                    )
                elif self.id == "direct":
                    posts = api.conversations(
                        since_id=since_id, max_id=max_id, limit=limit
                    )
                log.info(f"Fetched {len(posts)} new posts for {self.id}")
            except MastodonNetworkError as e:
                log.error(
                    f"Network error loading {self.id} timeline: {e}", exc_info=True
                )
                self.app.notify(
                    f"Connection to {self.app.config.mastodon_host} timed out. Will retry.",
                    severity="error",
                    timeout=10,
                )
            except Exception as e:
                log.error(f"Error loading {self.id} timeline: {e}", exc_info=True)
                self.app.notify(
                    f"Error loading {self.id} timeline: {e}", severity="error"
                )
        return posts

    def load_older_posts(self):
        """Load older posts."""
        if self.loading_more:
            return
        self.loading_more = True
        log.info(f"Loading older posts for {self.id} timeline...")
        self.loading_indicator.display = True
        self.run_worker(
            lambda: self.do_fetch_posts(max_id=self.oldest_post_id),
            exclusive=True,
            thread=True,
        )

    def render_posts(self, posts_data, since_id=None, max_id=None):
        """Renders the given posts data in the timeline."""
        log.info(f"render_posts called for {self.id} with {len(posts_data)} posts.")
        self.loading_indicator.display = False
        self.loading_more = False
        is_initial_load = not self.initial_render_done

        if is_initial_load and not posts_data:
            log.info(f"No posts to render for {self.id} on initial load.")
            if self.id == "home" or self.id == "federated":
                self.content_container.mount(
                    Static(f"{self.title} timeline is empty.", classes="status-message")
                )
            elif self.id == "notifications":
                self.content_container.mount(
                    Static("No new notifications.", classes="status-message")
                )
            self._notify_initial_render_complete()
            return

        if not posts_data and not is_initial_load:
            log.info(f"No new posts to render for {self.id}.")
            if max_id:  # This was a request for older posts
                self.content_container.mount(
                    Static("End of timeline", classes="end-of-timeline")
                )
            return

        if is_initial_load and posts_data and len(posts_data) > INITIAL_RENDER_LIMIT:
            log.info(
                f"Initial load for {self.id} returned {len(posts_data)} posts; rendering only {INITIAL_RENDER_LIMIT}"
            )
            posts_data = posts_data[:INITIAL_RENDER_LIMIT]

        if posts_data:
            new_latest_post_id_str = posts_data[0]["id"]
            if self.latest_post_id is None:
                self.latest_post_id = new_latest_post_id_str
            elif int(new_latest_post_id_str) > int(self.latest_post_id):
                self.latest_post_id = new_latest_post_id_str
            log.info(f"New latest post for {self.id} is {self.latest_post_id}")

            new_oldest_post_id_str = posts_data[-1]["id"]
            if self.oldest_post_id is None:
                self.oldest_post_id = new_oldest_post_id_str
            elif int(new_oldest_post_id_str) < int(self.oldest_post_id):
                self.oldest_post_id = new_oldest_post_id_str
            log.info(f"New oldest post for {self.id} is {self.oldest_post_id}")

        if is_initial_load:
            for item in self.content_container.query(".status-message"):
                item.remove()

        new_widgets = []
        for item in posts_data:
            widget_id = ""
            if self.id == "notifications":
                status = item.get("status") or {}
                status_id = status.get("id", "")
                unique_part = f"{item['type']}-{item['account']['id']}-{status_id}"
                widget_id = f"notif-{unique_part}"
            elif self.id == "direct":
                widget_id = f"conv-{item['id']}"
            else:
                widget_id = f"post-{item['id']}"

            if widget_id not in self.post_ids:
                self.post_ids.add(widget_id)
                if self.id == "home" or self.id == "federated" or self.id == "local":
                    new_widgets.append(Post(item, timeline_id=self.id, id=widget_id))
                elif self.id == "notifications":
                    new_widgets.append(Notification(item, id=widget_id))
                elif self.id == "direct":
                    new_widgets.append(ConversationSummary(item, id=widget_id))

        if new_widgets:
            log.info(f"Mounting {len(new_widgets)} new posts in {self.id}")
            if max_id:  # older posts
                # Check for gap
                first_new_post_ts = new_widgets[0].get_created_at()
                last_old_post = self.content_container.query(
                    "Post, Notification"
                ).last()

                if last_old_post and first_new_post_ts:
                    last_old_post_ts = last_old_post.get_created_at()
                    if (
                        last_old_post_ts
                        and first_new_post_ts < last_old_post_ts - timedelta(minutes=30)
                    ):
                        self.content_container.mount(GapIndicator())

                self.content_container.mount_all(new_widgets)
            else:  # newer posts or initial load
                self.content_container.mount_all(new_widgets, before=0)

        if new_widgets and is_initial_load:
            self.content_container.select_first_item()
            self._notify_initial_render_complete()

        prune_direction = "top" if max_id else "bottom"
        self.prune_posts(direction=prune_direction)

        # After adding new items, re-sort the entire conversation timeline
        if self.id == "direct":

            def get_sort_key(widget: ConversationSummary) -> datetime:
                if widget.conversation.get("last_status") and widget.conversation[
                    "last_status"
                ].get("created_at"):
                    return widget.conversation["last_status"]["created_at"]
                return datetime.min.replace(tzinfo=timezone.utc)

            self.content_container.sort_children(key=get_sort_key, reverse=True)

        # --- Start of scroll restoration logic ---
        if self.scroll_anchor_id and since_id:  # Only restore on a refresh
            try:
                anchor_widget = self.content_container.query_one(
                    f"#{self.scroll_anchor_id}"
                )
                self.content_container.scroll_to_widget(
                    anchor_widget, animate=False, top=True
                )
                log.debug(
                    f"Restored scroll position for {self.id} to {self.scroll_anchor_id}"
                )
            except Exception as e:
                log.warning(f"Could not restore scroll position: {e}")
        self.scroll_anchor_id = None
        # --- End of scroll restoration logic ---
        if is_initial_load:
            self._notify_initial_render_complete()

    def _notify_initial_render_complete(self):
        if not self.initial_render_done:
            self.initial_render_done = True
            if hasattr(self.app, "notify_timeline_initialized"):
                self.app.notify_timeline_initialized(self.id)

    def _handle_popups(self, notifications: list):
        """Handle pop-up notifications for new items."""
        if self.id != "notifications" or not notifications:
            return

        config = self.app.config
        for notif in notifications:
            acct = notif["account"]["acct"]
            if notif["type"] == "mention" and config.notifications_popups_mentions:
                self.app.notify(f"New mention from @{acct}", title="New Mention")
            elif notif["type"] == "follow" and config.notifications_popups_follows:
                self.app.notify(f"@{acct} followed you", title="New Follower")
            elif notif["type"] == "reblog" and config.notifications_popups_reblogs:
                self.app.notify(f"@{acct} boosted your post", title="New Boost")
            elif (
                notif["type"] == "favourite" and config.notifications_popups_favourites
            ):
                self.app.notify(f"@{acct} favourited your post", title="New Favourite")

    def prune_posts(self, direction: str = "bottom"):
        """Removes posts from the UI if there are too many."""
        all_posts = self.content_container.query(
            "Post, Notification, ConversationSummary"
        )
        if len(all_posts) > MAX_POSTS_IN_UI:
            log.info(
                f"Pruning posts in {self.id} from the {direction}. Have {len(all_posts)}, max {MAX_POSTS_IN_UI}"
            )

            num_to_remove = len(all_posts) - MAX_POSTS_IN_UI
            if direction == "bottom":
                posts_to_remove = all_posts[-num_to_remove:]
            else:  # direction == "top"
                posts_to_remove = all_posts[:num_to_remove]

            for post in posts_to_remove:
                if self.content_container.selected_item is not post:
                    self.post_ids.discard(post.id)
                    post.remove()

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.stop()
            self.open_thread()

    def scroll_up(self) -> None:
        """Proxy scroll_up to the content container."""
        self.content_container.scroll_up()

    def scroll_down(self) -> None:
        """Proxy scroll_down to the content container."""
        self.content_container.scroll_down()

    def like_post(self) -> None:
        """Proxy like_post to the content container."""
        self.content_container.like_post()

    def boost_post(self) -> None:
        """Proxy boost_post to the content container."""
        self.content_container.boost_post()

    def reply_to_post(self) -> None:
        """Proxy reply_to_post to the content container."""
        self.content_container.reply_to_post()

    def edit_post(self) -> None:
        """Proxy edit_post to the content container."""
        self.content_container.edit_post()

    def delete_post(self) -> None:
        """Proxy delete_post to the content container."""
        self.content_container.delete_post()

    def open_thread(self) -> None:
        """Proxy open_thread to the content container."""
        if self.id == "direct":
            selected = self.content_container.selected_item
            if isinstance(selected, ConversationSummary):
                self.post_message(
                    ViewConversation(
                        selected.conversation["id"],
                        selected.conversation["last_status"]["id"],
                    )
                )
        else:
            self.content_container.open_thread()

    def view_profile(self) -> None:
        """Proxy view_profile to the content container."""
        self.content_container.view_profile()

    def go_to_top(self) -> None:
        """Proxy go_to_top to the content container."""
        self.content_container.go_to_top()

    def show_urls(self) -> None:
        """Proxy show_urls to the content container."""
        self.content_container.show_urls()

    def compose(self):
        with Horizontal(classes="timeline-header"):
            yield Static(self.title, classes="timeline_title")
            yield LoadingIndicator(classes="timeline-refresh-spinner")
        yield TimelineContent(self, classes="timeline-content")


class Timelines(Static):
    """A widget to display the three timelines."""

    def compose(self):
        if self.app.config.home_timeline_enabled:
            yield Timeline("Home", id="home")
        if self.app.config.local_timeline_enabled:
            yield Timeline("Local", id="local")
        if self.app.config.notifications_timeline_enabled:
            yield Timeline("Notifications", id="notifications")
        if self.app.config.federated_timeline_enabled:
            yield Timeline("Federated", id="federated")
        if self.app.config.direct_timeline_enabled:
            yield Timeline("Direct Messages", id="direct")

    def on_mount(self) -> None:
        """Focus the first timeline when mounted."""
        try:
            first_timeline = self.query(Timeline).first()
            if first_timeline:
                first_timeline.focus()
        except Exception as e:
            log.error(f"Could not focus first timeline: {e}", exc_info=True)
