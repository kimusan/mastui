from textual.message import Message

class PostStatusUpdate(Message):
    """A message to update a post's status."""
    def __init__(self, post_data: dict) -> None:
        self.post_data = post_data
        super().__init__()


class ActionFailed(Message):
    """A message to indicate that an action failed."""
    def __init__(self, post_id: str) -> None:
        self.post_id = post_id
        super().__init__()


class TimelineData(Message):
    """A message to send timeline data."""
    def __init__(self, timeline_id: str, posts: list) -> None:
        self.timeline_id = timeline_id
        self.posts = posts
        super().__init__()


class FocusNextTimeline(Message):
    """A message to focus the next timeline."""
    pass


class FocusPreviousTimeline(Message):
    """A message to focus the previous timeline."""
    pass


class TimelineUpdate(Message):
    """A message to update the timeline with new posts."""
    def __init__(self, posts: list, since_id: str = None, max_id: str = None) -> None:
        self.posts = posts
        self.since_id = since_id
        self.max_id = max_id
        super().__init__()


class ViewProfile(Message):
    """A message to view a user's profile."""
    def __init__(self, account_id: str) -> None:
        self.account_id = account_id
        super().__init__()
