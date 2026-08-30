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


def test_modal_actions_guarded_before_timelines_ready():
    from textual.screen import Screen
    from mastui.help_screen import HelpScreen
    from mastui.splash import SplashScreen

    app = Mastui()
    app.push_screen = MagicMock()
    app.pause_timers = MagicMock()

    # Setup base screen on stack
    base_screen = Screen()
    app._screen_stack.append(base_screen)

    # When timelines are not ready, action_show_help should do nothing
    assert not app._timelines_ready
    app.action_show_help()
    app.push_screen.assert_not_called()

    # When screen is SplashScreen, action_show_help should do nothing
    app._timelines_ready = True
    splash = SplashScreen()
    app._screen_stack.append(splash)
    app.action_show_help()
    app.push_screen.assert_not_called()

    # When timelines are ready and splash is dismissed, action_show_help pushes HelpScreen
    app._screen_stack.remove(splash)
    app.action_show_help()
    assert app.push_screen.call_count == 1
    screen_arg = app.push_screen.call_args[0][0]
    assert isinstance(screen_arg, HelpScreen)

    # When HelpScreen is already on the stack, it should not be pushed again
    app._screen_stack.append(screen_arg)
    app.action_show_help()
    assert app.push_screen.call_count == 1

