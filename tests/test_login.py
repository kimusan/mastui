from unittest.mock import MagicMock, patch
import pytest
from textual.app import App
from textual.widgets import ContentSwitcher, Markdown
from mastui.login import LoginScreen


class MockLoginApp(App):
    """Test app fixture providing context for LoginScreen."""

    ssl_verify = True

    def __init__(self, login_screen: LoginScreen):
        super().__init__()
        self.login_screen = login_screen

    def on_mount(self):
        self.push_screen(self.login_screen)


def _get_static_text(widget) -> str:
    """Extract string content from Static widget across Textual versions."""
    return str(
        getattr(widget, "content", getattr(widget, "renderable", widget.render()))
    )


def test_clean_host():
    screen = LoginScreen()
    assert screen.clean_host("floss.social") == "floss.social"
    assert screen.clean_host("  floss.social  ") == "floss.social"
    assert screen.clean_host("https://floss.social") == "floss.social"
    assert screen.clean_host("https://floss.social/path") == "floss.social"
    assert screen.clean_host("http://floss.social:8080") == "floss.social:8080"
    assert screen.clean_host("@alice@floss.social") == "floss.social"
    assert screen.clean_host("") == ""
    assert screen.clean_host("   ") == ""
    assert screen.clean_host("invalid host with space") == ""


@pytest.mark.asyncio
async def test_login_screen_mount_and_elements():
    screen = LoginScreen()
    app = MockLoginApp(screen)
    async with app.run_test():
        # Verify essential elements are composed
        status = screen.query_one("#login-status")
        assert status is not None
        host_input = screen.query_one("#host")
        assert host_input is not None
        assert host_input.has_focus

        # Verify on_mount behavior when host is pre-filled
        screen_prefilled = LoginScreen(host="mastodon.social")
        app_prefilled = MockLoginApp(screen_prefilled)
        async with app_prefilled.run_test():
            prefilled_host = screen_prefilled.query_one("#host")
            assert prefilled_host.disabled is True
            assert screen_prefilled.query_one("#get_auth").has_focus


@pytest.mark.asyncio
async def test_login_screen_empty_and_invalid_host_validation():
    screen = LoginScreen()
    app = MockLoginApp(screen)
    async with app.run_test() as pilot:
        status = screen.query_one("#login-status")

        # 1. Click get_auth with empty host
        await pilot.click("#get_auth")
        await pilot.pause()
        assert "Please enter a Mastodon instance" in _get_static_text(status)

        # 2. Click get_auth with whitespace/invalid host
        host_input = screen.query_one("#host")
        host_input.value = "   "
        await pilot.pause()
        await pilot.click("#get_auth")
        await pilot.pause()
        assert "Please enter a Mastodon instance" in _get_static_text(status)

        host_input.value = "invalid domain space"
        await pilot.pause()
        await pilot.click("#get_auth")
        await pilot.pause()
        assert "Invalid instance name" in _get_static_text(status)


@pytest.mark.asyncio
async def test_login_screen_get_auth_and_auth_callbacks():
    screen = LoginScreen()
    app = MockLoginApp(screen)

    with patch("mastui.login.create_app") as mock_create_app, patch(
        "mastui.login.clipman"
    ) as mock_clipman:
        mock_create_app.return_value = (
            "https://floss.social/oauth/authorize?client_id=dummy",
            "dummy_client_id",
            "dummy_client_secret",
            None,
        )
        mock_clipman.set = MagicMock()

        async with app.run_test() as pilot:
            status = screen.query_one("#login-status")
            switcher = screen.query_one(ContentSwitcher)

            host_input = screen.query_one("#host")
            host_input.value = "floss.social"
            await pilot.pause()

            # Trigger get_auth
            await pilot.click("#get_auth")
            await pilot.pause()

            # Wait for worker to finish create_app
            for _ in range(20):
                if switcher.current == "login-auth-view":
                    break
                await pilot.pause(0.05)

            assert switcher.current == "login-auth-view"
            assert screen.query_one("#auth_code").has_focus
            auth_link = screen.query_one("#auth_link", Markdown)
            assert "floss.social" in auth_link.source

            # Test login click with empty auth_code
            await pilot.click("#login")
            await pilot.pause()
            assert "Please enter the authorization code" in _get_static_text(status)

            # Test login failure callback
            screen.on_login_complete((None, None, "Invalid authorization code"))
            await pilot.pause()
            assert switcher.current == "login-auth-view"
            assert "Login failed: Invalid authorization code" in _get_static_text(
                status
            )

            # Test login error during auth link creation
            screen.on_auth_link_created((None, None, None, "Instance unreachable"))
            await pilot.pause()
            assert switcher.current == "login-initial-view"
            assert "Error: Instance unreachable" in _get_static_text(status)


@pytest.mark.asyncio
async def test_login_screen_cancel():
    screen = LoginScreen()
    app = MockLoginApp(screen)
    async with app.run_test() as pilot:
        dismiss_result = []
        screen.dismiss = lambda result=None: dismiss_result.append(result)

        await pilot.click("#cancel")
        await pilot.pause()
        assert dismiss_result == [None]


@pytest.mark.asyncio
async def test_login_screen_input_submitted():
    screen = LoginScreen()
    app = MockLoginApp(screen)
    async with app.run_test() as pilot:
        status = screen.query_one("#login-status")

        # Enter on empty host triggers validation
        host_input = screen.query_one("#host")
        host_input.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert "Please enter a Mastodon instance" in _get_static_text(status)
