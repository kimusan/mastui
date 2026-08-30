import pytest
from unittest.mock import MagicMock
from mastodon import MastodonAPIError
from mastui.app import Mastui
from mastui.widgets import BoostPost, LikePost


def test_like_and_boost_throttling_and_error_handling():
    app = Mastui()
    app.api = MagicMock()
    app.notify = MagicMock()
    app.post_message = MagicMock()
    app.call_from_thread = lambda fn, *args, **kwargs: fn(*args, **kwargs)

    # 1. Throttling in-flight actions
    app._pending_post_actions.add(("boost", "123"))
    app.handle_boost_post(BoostPost("123", False))
    app.notify.assert_called_with(
        "You're pressing boost too fast! Action is still processing...",
        severity="warning",
    )
    app._pending_post_actions.clear()

    app._pending_post_actions.add(("like", "123"))
    app.handle_like_post(LikePost("123", False))
    app.notify.assert_called_with(
        "You're pressing like too fast! Action is still processing...",
        severity="warning",
    )
    app._pending_post_actions.clear()

    # 2. Catching MastodonAPIError "already reblogged" gracefully
    app.api.status_reblog.side_effect = MastodonAPIError(422, "You have already reblogged this status")
    app.api.status.return_value = {"id": "123", "reblogged": True}

    app._pending_post_actions.add(("boost", "123"))
    app.do_boost_post("123", False)

    assert ("boost", "123") not in app._pending_post_actions
    app.notify.assert_called_with(
        "You're pressing boost too fast! Status was already updated.",
        severity="warning",
    )

    # 3. Catching MastodonAPIError "already favourited" gracefully
    app.api.status_favourite.side_effect = MastodonAPIError(422, "You have already favourited this status")
    app.api.status.return_value = {"id": "123", "favourited": True}

    app._pending_post_actions.add(("like", "123"))
    app.do_like_post("123", False)

    assert ("like", "123") not in app._pending_post_actions
    app.notify.assert_called_with(
        "You're pressing like too fast! Status was already updated.",
        severity="warning",
    )
