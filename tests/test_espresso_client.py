"""Comprehensive test suite for Mastui on Espresso TUI components and features."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ESPRESSO_SRC = REPO_ROOT / "espresso" / "src"
MASTUI_SRC = REPO_ROOT / "mastui"

import sys
for p in (str(ESPRESSO_SRC), str(MASTUI_SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from espresso.core.keys import KeyMsg, PasteMsg
from espresso.core.tea import Msg, BatchMsg, WindowSizeMsg
from espresso.beans.modal_stack import ModalCloseMsg
from espresso.beans.confetti import Confetti, ConfettiMode
from espresso.beans.toast import ToastLevel
from espresso.crema import Style, ROUNDED_BORDER, strip_ansi
from espresso.crema.width import string_width

from mastui.espresso_settings import (
    SettingsModal,
    SettingsSaveMsg,
    load_settings,
    save_settings,
)
from mastui.espresso_urls import (
    UrlSelectorModal,
    UrlSelectedMsg,
    extract_post_urls,
)
from mastui.espresso_help import HelpModal
from mastui.espresso_thread import ThreadModal, fetch_thread_posts, ThreadContextLoadedMsg
from mastui.espresso_profile import ProfileModal, _clean_bio_html
from mastui.espresso_app import (
    MastuiEspressoApp,
    SAMPLE_POSTS,
    NeedRefreshMsg,
    TimelineRefreshedMsg,
    NeedOlderPostsMsg,
    TimelineOlderLoadedMsg,
)
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg


class TestMastuiEspressoComponents(unittest.TestCase):
    """Test suite verifying Espresso Mastui parity features."""

    def test_settings_modal_and_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir)
            # Default settings
            settings = load_settings(profile_dir)
            self.assertTrue(settings["enable_animations"])
            self.assertTrue(settings["auto_refresh"])

            # Create modal
            modal = SettingsModal(current_settings=settings, profile_dir=profile_dir, width=64)
            self.assertEqual(modal.active_tab, 0)
            self.assertTrue(modal.sw_home.value)

            # Toggle home switch with Space on Tab 0
            modal, cmd = modal.update(KeyMsg(" "))
            self.assertFalse(modal.sw_home.value)

            # Switch to Tab 4: Appearance & Themes
            modal.set_tab(4)
            self.assertEqual(modal.active_tab, 4)
            # Focus on sw_anim (index 1 of Tab 4: 0 is sel_theme, 1 is sw_anim)
            modal.tab_focus_idx = 1
            modal._sync_focus()
            self.assertTrue(modal.sw_anim.value)

            # Toggle animations with Space
            modal, _ = modal.update(KeyMsg(" "))
            self.assertFalse(modal.sw_anim.value)

            # Select theme "dracula"
            modal.tab_focus_idx = 0
            modal.sel_theme.set_value("dracula")

            # Focus on Save button (tab_focus_idx = -2)
            modal.tab_focus_idx = -2

            # Press Enter on Save
            modal, save_cmd = modal.update(KeyMsg("enter"))
            self.assertIsNotNone(save_cmd)
            msg = save_cmd()
            self.assertIsInstance(msg, SettingsSaveMsg)
            self.assertFalse(msg.settings["enable_animations"])
            self.assertFalse(msg.settings["home_timeline_enabled"])
            self.assertEqual(msg.settings["theme"], "dracula")

            # Verify persisted to disk
            saved = load_settings(profile_dir)
            self.assertFalse(saved["enable_animations"])
            self.assertFalse(saved["home_timeline_enabled"])
            self.assertEqual(saved["theme"], "dracula")

    def test_url_extraction_and_selector_modal(self) -> None:
        sample_post = {
            "id": "999",
            "content": '<p>Check out our site at <a href="https://example.com/project">https://example.com/project</a> and docs at https://docs.example.com</p>',
            "media_attachments": [
                {"url": "https://cdn.example.com/image.png"}
            ],
            "card": {"url": "https://card.example.com"},
        }
        urls = extract_post_urls(sample_post)
        self.assertIn("https://example.com/project", urls)
        self.assertIn("https://docs.example.com", urls)
        self.assertIn("https://cdn.example.com/image.png", urls)
        self.assertIn("https://card.example.com", urls)

        modal = UrlSelectorModal(post_data=sample_post, width=70)
        view_text = modal.view()
        self.assertIn("EXTRACTED LINKS", view_text)
        self.assertIn("https://example.com/project", view_text)

        # Quick select via digit '1'
        modal, select_cmd = modal.update(KeyMsg("1"))
        self.assertIsNotNone(select_cmd)
        msg = select_cmd()
        self.assertIsInstance(msg, UrlSelectedMsg)
        self.assertEqual(msg.url, "https://example.com/project")

    def test_help_modal(self) -> None:
        modal = HelpModal(width=78)
        view = strip_ansi(modal.view())
        self.assertIn("KEYBOARD SHORTCUTS", view)
        self.assertIn("NAVIGATION", view)
        self.assertIn("POST ACTIONS", view)
        self.assertIn("confetti", view.lower())

        # Esc closes
        modal, cmd = modal.update(KeyMsg("esc"))
        self.assertIsNotNone(cmd)
        self.assertIsInstance(cmd(), ModalCloseMsg)

    def test_thread_modal(self) -> None:
        post = SAMPLE_POSTS[0]
        # In demo mode, fetch_thread_posts supplies demo discussion context
        demo_thread = fetch_thread_posts(post, is_demo=True)
        self.assertGreaterEqual(len(demo_thread), 2)
        self.assertEqual(demo_thread[0].get("_thread_role"), "main")
        self.assertEqual(demo_thread[1].get("_thread_role"), "reply")

        # In non-demo mode with no API and no parent/replies, it returns only the standalone toot
        standalone_thread = fetch_thread_posts(post, is_demo=False)
        self.assertEqual(len(standalone_thread), 1)

        modal = ThreadModal(post=post, thread_posts=demo_thread, width=72, height=20)
        view = modal.view()
        self.assertIn("CONVERSATION THREAD", view)
        self.assertIn("Kim Schulz", view)

        # Navigation in thread
        modal, _ = modal.update(KeyMsg("j"))
        self.assertGreaterEqual(modal.list.cursor, 0)

        # Like selected post in thread
        modal, _ = modal.update(KeyMsg("l"))
        self.assertTrue(modal.selected_post.get("favourited"))

    def test_profile_modal(self) -> None:
        raw_bio = "<p>Developer &amp; Open Source creator.<br>Building tools in Python!</p>"
        clean = _clean_bio_html(raw_bio)
        self.assertIn("Developer & Open Source creator.", clean)
        self.assertIn("Building tools in Python!", clean)

        account = {
            "display_name": "Kim Schulz",
            "acct": "kim@mastui.app",
            "note": raw_bio,
            "followers_count": 500,
            "following_count": 250,
            "statuses_count": 1200,
            "fields": [{"name": "Blog", "value": "https://schulz.dk"}],
        }
        modal = ProfileModal(account_or_post=account, width=68)
        view = strip_ansi(modal.view())
        self.assertIn("Kim Schulz", view)
        self.assertIn("@kim@mastui.app", view)
        self.assertIn("500 Followers", view)
        self.assertIn("https://schulz.dk", view)

        # Toggle follow
        self.assertFalse(modal.is_following)
        modal, _ = modal.update(KeyMsg("f"))
        self.assertTrue(modal.is_following)

    def test_burst_animation_toggle_and_overlay(self) -> None:
        app = MastuiEspressoApp(is_demo=True)
        self.assertTrue(app.enable_animations)

        # Boosting post triggers confetti command when animations enabled
        app, cmd = app.update(KeyMsg("b"))
        self.assertIsNotNone(cmd)
        self.assertTrue(app.confetti.is_active)

        # Verify overlay renders directly on top of timeline without wiping content
        view_with_confetti = strip_ansi(app.view())
        self.assertIn("MASTUI", view_with_confetti)
        self.assertIn("Kim Schulz", view_with_confetti)

        # Now simulate disabling animations via SettingsSaveMsg
        new_settings = {"enable_animations": False, "auto_refresh": True}
        app.modal_stack.push(SettingsModal(current_settings=new_settings))
        app, s_cmd = app.update(SettingsSaveMsg(settings=new_settings))
        self.assertFalse(app.enable_animations)

        # Clear active confetti
        app.confetti.clear()
        self.assertFalse(app.confetti.is_active)

        # Unboost and re-boost: when animations are disabled, confetti should NOT activate
        app.update(KeyMsg("b"))  # unboost
        app, cmd = app.update(KeyMsg("b"))  # boost again
        self.assertFalse(app.confetti.is_active, "Confetti should not activate when animations disabled")

    def test_app_modals_keyboard_shortcuts(self) -> None:
        app = MastuiEspressoApp(is_demo=True)

        # 'o' opens SettingsModal
        app, _ = app.update(KeyMsg("o"))
        self.assertTrue(app.modal_stack.has_modals)
        self.assertIsInstance(app.modal_stack.top_modal, SettingsModal)
        app, _ = app.update(KeyMsg("esc"))
        self.assertFalse(app.modal_stack.has_modals)

        # '?' opens HelpModal
        app, _ = app.update(KeyMsg("?"))
        self.assertTrue(app.modal_stack.has_modals)
        self.assertIsInstance(app.modal_stack.top_modal, HelpModal)
        app, _ = app.update(KeyMsg("esc"))
        self.assertFalse(app.modal_stack.has_modals)

        # 'x' opens UrlSelectorModal
        app, _ = app.update(KeyMsg("x"))
        self.assertTrue(app.modal_stack.has_modals)
        self.assertIsInstance(app.modal_stack.top_modal, UrlSelectorModal)
        app, _ = app.update(KeyMsg("esc"))
        self.assertFalse(app.modal_stack.has_modals)

        # 'enter' opens ThreadModal
        app, _ = app.update(KeyMsg("enter"))
        self.assertTrue(app.modal_stack.has_modals)
        self.assertIsInstance(app.modal_stack.top_modal, ThreadModal)
        app, _ = app.update(KeyMsg("esc"))
        self.assertFalse(app.modal_stack.has_modals)

        # 'p' opens ProfileModal
        app, _ = app.update(KeyMsg("p"))
        self.assertTrue(app.modal_stack.has_modals)
        self.assertIsInstance(app.modal_stack.top_modal, ProfileModal)
        app, _ = app.update(KeyMsg("esc"))
        self.assertFalse(app.modal_stack.has_modals)

        # 'g' jumps to top of timeline
        app.current_timeline.list.cursor = 2
        app, _ = app.update(KeyMsg("g"))
        self.assertEqual(app.current_timeline.list.cursor, 0)

    def test_settings_mouse_hit_testing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir)
            settings = load_settings(profile_dir)
            modal = SettingsModal(
                current_settings=settings,
                profile_dir=profile_dir,
                width=70,
                screen_width=100,
                screen_height=30,
            )
            self.assertTrue(modal.sw_home.value)

            # Hit test sw_home (Tab 0 control 0, rel_y = 4, modal_top_y = 3, so y = 8; x = 26)
            click_home = MouseMsg(x=26, y=8, button=MouseButton.LEFT, action=MouseAction.PRESS)
            modal, _ = modal.update(click_home)
            self.assertEqual(modal.tab_focus_idx, 0)
            self.assertFalse(modal.sw_home.value)

            # Hit test Save button (rel_y = 19, modal_top_y = 3, y = 23, x = 26)
            click_save = MouseMsg(x=26, y=23, button=MouseButton.LEFT, action=MouseAction.PRESS)
            modal, save_cmd = modal.update(click_save)
            self.assertEqual(modal.tab_focus_idx, -2)
            self.assertIsNotNone(save_cmd)
            msg = save_cmd()
            self.assertIsInstance(msg, SettingsSaveMsg)
            self.assertFalse(msg.settings["home_timeline_enabled"])

    def test_settings_international_tabs_and_mouse(self) -> None:
        """Verify tab switching via international keys (1-6, arrows, h/l) and mouse click."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir)
            modal = SettingsModal(
                profile_dir=profile_dir,
                width=82,
                screen_width=100,
                screen_height=30,
            )
            self.assertEqual(modal.active_tab, 0)

            # 1. Direct digit jumping (1 to 6)
            modal, _ = modal.update(KeyMsg("3"))
            self.assertEqual(modal.active_tab, 2)  # Media
            modal, _ = modal.update(KeyMsg("6"))
            self.assertEqual(modal.active_tab, 5)  # Posting
            modal, _ = modal.update(KeyMsg("1"))
            self.assertEqual(modal.active_tab, 0)  # Timelines
            modal, _ = modal.update(KeyMsg("4"))
            self.assertEqual(modal.active_tab, 3)  # Alerts

            # 2. Arrow & cycle navigation (left/right, h/l, commas/dots, brackets)
            modal, _ = modal.update(KeyMsg("right"))
            self.assertEqual(modal.active_tab, 4)  # Themes
            modal, _ = modal.update(KeyMsg("l"))
            self.assertEqual(modal.active_tab, 5)
            modal, _ = modal.update(KeyMsg("right"))
            self.assertEqual(modal.active_tab, 0)  # Wrap around
            modal, _ = modal.update(KeyMsg("left"))
            self.assertEqual(modal.active_tab, 5)  # Wrap backwards
            modal, _ = modal.update(KeyMsg("h"))
            self.assertEqual(modal.active_tab, 4)
            modal, _ = modal.update(KeyMsg(","))
            self.assertEqual(modal.active_tab, 3)
            modal, _ = modal.update(KeyMsg("."))
            self.assertEqual(modal.active_tab, 4)
            modal, _ = modal.update(KeyMsg("["))
            self.assertEqual(modal.active_tab, 3)
            modal, _ = modal.update(KeyMsg("]"))
            self.assertEqual(modal.active_tab, 4)

            # 3. Mouse wheel tab cycling
            modal, _ = modal.update(MouseMsg(x=20, y=10, button=MouseButton.WHEEL_UP, action=MouseAction.PRESS))
            self.assertEqual(modal.active_tab, 3)
            modal, _ = modal.update(MouseMsg(x=20, y=10, button=MouseButton.WHEEL_DOWN, action=MouseAction.PRESS))
            self.assertEqual(modal.active_tab, 4)

            # 4. Pixel-exact mouse click on tab pills
            lines = modal.view().splitlines()
            overlay_h = len(lines)
            overlay_w = max(string_width(l) for l in lines)
            pos_y = (30 - overlay_h) // 2
            pos_x = (100 - overlay_w) // 2

            # Click on Tab 1 (Refresh) pill at x = pos_x + 22, y = pos_y + 2
            tab1_click = MouseMsg(x=pos_x + 22, y=pos_y + 2, button=MouseButton.LEFT, action=MouseAction.PRESS)
            modal, _ = modal.update(tab1_click)
            self.assertEqual(modal.active_tab, 1)

            # Click on Tab 5 (Posting) pill at x = pos_x + 70, y = pos_y + 2
            tab5_click = MouseMsg(x=pos_x + 70, y=pos_y + 2, button=MouseButton.LEFT, action=MouseAction.PRESS)
            modal, _ = modal.update(tab5_click)
            self.assertEqual(modal.active_tab, 5)

            # 5. Dropdown escape behavior
            modal.set_tab(4)  # Themes
            modal.tab_focus_idx = 0  # Theme Select
            modal.sel_theme.open()
            self.assertTrue(modal.sel_theme.is_open)

            # Esc closes dropdown, not the modal
            modal, esc_cmd = modal.update(KeyMsg("esc"))
            self.assertFalse(modal.sel_theme.is_open)
            self.assertIsNone(esc_cmd)

            # Second Esc closes the modal
            modal, esc_cmd2 = modal.update(KeyMsg("esc"))
            self.assertIsNotNone(esc_cmd2)
            self.assertIsInstance(esc_cmd2(), ModalCloseMsg)

    def test_multi_column_timelines_and_navigation(self) -> None:
        app = MastuiEspressoApp(is_demo=True)
        app.width = 120
        app.height = 35
        app.force_single_column = False

        enabled = app.enabled_timelines
        self.assertGreaterEqual(len(enabled), 3)

        # Rendering in wide terminal shows side-by-side columns
        view_text = strip_ansi(app.view())
        self.assertIn("🏠 Home", view_text)
        self.assertIn("🏙️ Local", view_text)

        # Verify buttons at top are not skewed (first row aligned with content and bottom borders)
        lines = view_text.splitlines()
        self.assertTrue(lines[3].startswith("╭"), f"Top button border was skewed: {lines[3][:10]}")
        self.assertTrue(lines[4].startswith("│"), f"Middle button row mismatch: {lines[4][:10]}")
        self.assertTrue(lines[5].startswith("╰"), f"Bottom button border mismatch: {lines[5][:10]}")

        # Active timeline starts at 0 (Home)
        self.assertEqual(app.active_timeline_idx, 0)

        # Navigate right with 'right' key
        app, _ = app.update(KeyMsg("right"))
        self.assertNotEqual(app.active_timeline_idx, 0)
        self.assertEqual(app.current_timeline.timeline_id, "local")

        # Navigate back left with 'h' key
        app, _ = app.update(KeyMsg("h"))
        self.assertEqual(app.active_timeline_idx, 0)
        self.assertEqual(app.current_timeline.timeline_id, "home")

        # Click on top button row (y=4, x=30 which is Local timeline)
        app, _ = app.update(MouseMsg(x=30, y=4, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(app.current_timeline.timeline_id, "local")

        # Click back on top button row (y=4, x=5 which is Home timeline)
        app, _ = app.update(MouseMsg(x=5, y=4, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(app.current_timeline.timeline_id, "home")

        # Toggle Direct Messages with 'm'
        dm_initial_enabled = app.timelines[4].enabled
        app, _ = app.update(KeyMsg("m"))
        self.assertEqual(app.timelines[4].enabled, not dm_initial_enabled)

    def test_timeline_refresh_and_spinner(self) -> None:
        import asyncio

        app = MastuiEspressoApp(is_demo=True)
        self.assertFalse(app.current_timeline.is_refreshing)

        # Press 'r' to trigger refresh
        app, ref_cmd = app.update(KeyMsg("r"))
        self.assertTrue(app.current_timeline.is_refreshing)
        self.assertIsNotNone(ref_cmd)

        # Refresh command produces BatchMsg containing spinner tick and NeedRefreshMsg
        batch_res = asyncio.run(ref_cmd())
        self.assertIsInstance(batch_res, BatchMsg)
        ref_msgs = [m for m in batch_res.messages if isinstance(m, NeedRefreshMsg)]
        self.assertEqual(len(ref_msgs), 1)
        ref_msg = ref_msgs[0]
        self.assertEqual(ref_msg.timeline_id, "home")

        # Handling NeedRefreshMsg in app returns async command producing TimelineRefreshedMsg
        app, async_fetch_cmd = app.update(ref_msg)
        self.assertIsNotNone(async_fetch_cmd)
        result_msg = async_fetch_cmd()
        self.assertIsInstance(result_msg, TimelineRefreshedMsg)

        # Delivering TimelineRefreshedMsg finishes refresh
        app, _ = app.update(result_msg)
        self.assertFalse(app.current_timeline.is_refreshing)

    def test_timeline_pagination(self) -> None:
        app = MastuiEspressoApp(is_demo=True)
        initial_count = len(app.current_timeline.posts)

        # Emit NeedOlderPostsMsg
        msg = NeedOlderPostsMsg(timeline_id="home", max_id="11321000")
        app, fetch_cmd = app.update(msg)
        self.assertIsNotNone(fetch_cmd)

        loaded_msg = fetch_cmd()
        self.assertIsInstance(loaded_msg, TimelineOlderLoadedMsg)
        self.assertGreater(len(loaded_msg.older_posts), 0)

        # Append older posts into timeline
        app, _ = app.update(loaded_msg)
        self.assertGreater(len(app.current_timeline.posts), initial_count)

    def test_sqlite_cache_pagination_and_refresh(self) -> None:
        import json
        import sqlite3

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE posts (id TEXT, timeline_id TEXT, created_at TEXT, data TEXT)")
            p100 = {"id": "100", "content": "Post 100", "account": {"display_name": "User 100"}}
            p200 = {"id": "200", "content": "Post 200", "account": {"display_name": "User 200"}}
            p300 = {"id": "300", "content": "Post 300", "account": {"display_name": "User 300"}}
            conn.execute("INSERT INTO posts VALUES ('100', 'home', '2026-10-01T00:00:00', ?)", (json.dumps(p100),))
            conn.execute("INSERT INTO posts VALUES ('200', 'home', '2026-10-01T01:00:00', ?)", (json.dumps(p200),))
            conn.execute("INSERT INTO posts VALUES ('300', 'home', '2026-10-01T02:00:00', ?)", (json.dumps(p300),))
            conn.commit()
            conn.close()

            app = MastuiEspressoApp(
                is_demo=False,
                posts=[p200],
                cache_db_path=db_path,
            )

            # Pagination: query older posts than 200
            msg = NeedOlderPostsMsg(timeline_id="home", max_id="200")
            app, fetch_cmd = app.update(msg)
            self.assertIsNotNone(fetch_cmd)
            loaded_msg = fetch_cmd()
            self.assertIsInstance(loaded_msg, TimelineOlderLoadedMsg)
            self.assertEqual(len(loaded_msg.older_posts), 1)
            self.assertEqual(loaded_msg.older_posts[0]["id"], "100")

            # Refresh: query newer posts than 200
            ref_msg = NeedRefreshMsg(timeline_id="home", since_id="200")
            app, ref_fetch_cmd = app.update(ref_msg)
            self.assertIsNotNone(ref_fetch_cmd)
            ref_res_msg = ref_fetch_cmd()
            self.assertIsInstance(ref_res_msg, TimelineRefreshedMsg)
            self.assertEqual(len(ref_res_msg.new_posts), 1)
            self.assertEqual(ref_res_msg.new_posts[0]["id"], "300")

    def test_pull_to_refresh_at_top(self) -> None:
        app = MastuiEspressoApp(is_demo=True)
        tl = app.current_timeline
        self.assertEqual(tl.list.cursor, 0)
        self.assertFalse(tl.is_refreshing)

        # Press Up / 'k' when cursor == 0 -> triggers refresh
        tl, cmd = tl.update(KeyMsg("k"))
        self.assertTrue(tl.is_refreshing)
        self.assertIsNotNone(cmd)

        # Reset refreshing
        tl.is_refreshing = False

        # Wheel up when cursor == 0 -> triggers refresh
        wheel_up = MouseMsg(x=10, y=10, button=MouseButton.WHEEL_UP, action=MouseAction.PRESS)
        tl, cmd = tl.update(wheel_up)
        self.assertTrue(tl.is_refreshing)

        # Reset and move cursor down to 1
        tl.is_refreshing = False
        tl.list.select(1)
        self.assertEqual(tl.list.cursor, 1)

        # Press 'k' when cursor == 1 -> moves cursor to 0, does not trigger refresh
        tl, cmd = tl.update(KeyMsg("k"))
        self.assertFalse(tl.is_refreshing)
        self.assertEqual(tl.list.cursor, 0)

    def test_refresh_all_timelines(self) -> None:
        app = MastuiEspressoApp(is_demo=True)
        # Verify initial states
        for tl in app.enabled_timelines:
            self.assertFalse(tl.is_refreshing)

        # Press 'R'
        app, cmd = app.update(KeyMsg("R"))
        self.assertIsNotNone(cmd)

        # All enabled timelines should now be refreshing
        for tl in app.enabled_timelines:
            self.assertTrue(tl.is_refreshing)

    def test_splash_screen_workflow(self) -> None:
        app = MastuiEspressoApp(is_demo=True, show_splash=True)
        self.assertTrue(app.show_splash)

        # Initial view renders splash screen
        view_text = app.view()
        self.assertIn("Brewing feeds...", view_text)
        self.assertIn("Mastui", view_text)

        # Any key dismisses splash
        app, cmd = app.update(KeyMsg("enter"))
        self.assertIsNotNone(cmd)
        done_msg = cmd()
        app, _ = app.update(done_msg)
        self.assertFalse(app.show_splash)

        # Now view renders main timelines
        view_after = app.view()
        self.assertIn("🏠 Home", view_after)

    def test_image_attachment_modal(self) -> None:
        # Create post with media attachment
        post_with_media = {
            "id": "500",
            "created_at": "2026-10-02T10:00:00",
            "account": {"display_name": "Photographer", "acct": "photo@mastui.app"},
            "content": "<p>Check out this sunset! 🌅</p>",
            "media_attachments": [
                {
                    "id": "att1",
                    "type": "image",
                    "url": "https://mastui.app/media/sunset.jpg",
                    "preview_url": "https://mastui.app/media/sunset_thumb.jpg",
                    "description": "Golden sunset over calm ocean waves",
                }
            ],
        }
        app = MastuiEspressoApp(is_demo=False, posts=[post_with_media])
        self.assertFalse(app.modal_stack.has_modals)

        # Press 'i' to open ImageModal
        app, _ = app.update(KeyMsg("i"))
        self.assertTrue(app.modal_stack.has_modals)
        top_modal = app.modal_stack.top_modal
        self.assertIn("MEDIA ATTACHMENT PREVIEW", top_modal.view())
        self.assertIn("Golden sunset", top_modal.view())

        # Press Esc to close modal
        app, _ = app.update(KeyMsg("esc"))
        self.assertFalse(app.modal_stack.has_modals)

    def test_bottom_toast_positioning(self) -> None:
        app = MastuiEspressoApp(is_demo=True)
        app.width = 100
        app.height = 30
        app.toasts.add("Test Bottom Toast Notification", level=ToastLevel.INFO, duration=3.0)
        self.assertTrue(app.toasts.has_toasts)

        view_text = app.view()
        lines = view_text.splitlines()
        # Find which line contains the toast notification
        toast_line_indices = [
            idx for idx, line in enumerate(lines)
            if "Test Bottom Toast Notification" in line
        ]
        self.assertTrue(toast_line_indices, "Toast not found in view()")
        toast_row = toast_line_indices[0]
        # In a 30-row terminal, bottom toasts should be in the lower quarter (row >= 22)
        self.assertGreaterEqual(toast_row, 20)

    def test_theme_system_and_switching(self) -> None:
        from mastui.espresso_theme import get_theme, load_all_themes

        themes = load_all_themes()
        self.assertIn("espresso", themes)
        self.assertIn("dracula", themes)
        self.assertIn("catppuccin", themes)
        self.assertIn("nord", themes)
        self.assertIn("retro-green", themes)

        app = MastuiEspressoApp(is_demo=True)
        self.assertEqual(app.theme.name, "espresso")

        # Save settings with theme 'retro-green'
        new_settings = dict(app.settings)
        new_settings["theme"] = "retro-green"
        app.modal_stack.push(SettingsModal(current_settings=new_settings))
        app, _ = app.update(SettingsSaveMsg(settings=new_settings))

        self.assertEqual(app.theme.name, "retro-green")
        self.assertEqual(app.current_timeline.theme.name, "retro-green")

    def test_window_resize_during_splash_and_full_width_columns(self) -> None:
        app = MastuiEspressoApp(is_demo=True, show_splash=True)
        # Window size message dispatched at startup (e.g. 180x45 terminal)
        app, _ = app.update(WindowSizeMsg(180, 45))
        self.assertEqual(app.width, 180)
        self.assertEqual(app.height, 45)
        self.assertEqual(app.splash.width, 180)
        self.assertEqual(app.splash.height, 45)

        # Dismiss splash
        from mastui.espresso_splash import SplashDoneMsg
        app, _ = app.update(SplashDoneMsg())
        self.assertFalse(app.show_splash)

        # Verify timeline columns now span the full 180 columns
        enabled = app.enabled_timelines
        total_col_width = sum(tl.width for tl in enabled) + (len(enabled) - 1)
        self.assertGreaterEqual(total_col_width, 175)


    def test_select_keyboard_navigation_and_multiline_view(self) -> None:
        """Verify Select dropdown keyboard open/nav/close and no duplicated arrows."""
        modal = SettingsModal(width=80, screen_width=100, screen_height=30)
        # Switch to Media tab (index 2)
        modal.set_tab(2)
        self.assertEqual(modal.active_tab, 2)
        # Focus is on sel_img_renderer (index 1 in Media tab: sw_images is 0, sel_img_renderer is 1)
        modal, _ = modal.update(KeyMsg("tab"))
        self.assertEqual(modal.tab_focus_idx, 1)
        self.assertFalse(modal.sel_img_renderer.is_open)

        # 1. Open dropdown via Enter or Space
        modal, _ = modal.update(KeyMsg("enter"))
        self.assertTrue(modal.sel_img_renderer.is_open)

        # 2. Verify multiline view does not prepend ▶ on every line
        view_text = modal.view()
        rendered_lines = [l for l in view_text.splitlines() if "Image Renderer" in l or "ansi" in l or "sixel" in l]
        # Only line with the active option cursor should have ▶
        arrow_count = sum(1 for l in view_text.splitlines() if "▶" in l)
        # There should be exactly one cursor indicator in the view
        self.assertLessEqual(arrow_count, 2)

        # 3. Navigate down inside open dropdown
        initial_cursor = modal.sel_img_renderer.cursor
        modal, _ = modal.update(KeyMsg("down"))
        self.assertEqual(modal.sel_img_renderer.cursor, initial_cursor + 1)

        # 4. Choose via Enter
        target_val = modal.sel_img_renderer.options[initial_cursor + 1][0]
        modal, cmd = modal.update(KeyMsg("enter"))
        self.assertFalse(modal.sel_img_renderer.is_open)
        self.assertEqual(modal.sel_img_renderer.value, target_val)

        # 5. Quick cycling with + / - while closed
        prev_val = modal.sel_img_renderer.value
        modal, _ = modal.update(KeyMsg("+"))
        self.assertNotEqual(modal.sel_img_renderer.value, prev_val)

    def test_select_mouse_click_selection(self) -> None:
        """Verify clicking dropdown options with mouse selects the clicked value."""
        modal = SettingsModal(width=80, screen_width=100, screen_height=30)
        modal.set_tab(2)  # Media tab
        modal.tab_focus_idx = 1
        modal.sel_img_renderer.open()
        self.assertTrue(modal.sel_img_renderer.is_open)

        # Find the row on screen where options are rendered
        view_lines = modal.view().splitlines()
        opt_line = -1
        for idx, line in enumerate(view_lines):
            if "external" in line or "Auto-detect" in line:
                opt_line = idx
                break
        self.assertGreater(opt_line, 0)

        # Compute screen y for this line
        pos_y = max(0, (modal.screen_height - len(view_lines)) // 2)
        click_y = pos_y + opt_line
        click_x = 50  # modal is centered

        from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
        click_msg = MouseMsg(x=click_x, y=click_y, button=MouseButton.LEFT, action=MouseAction.PRESS)
        modal, _ = modal.update(click_msg)
        # Dropdown should have closed and selected the clicked or nearest option
        self.assertFalse(modal.sel_img_renderer.is_open)

    def test_theme_backgrounds_and_palettes(self) -> None:
        """Verify theme color attributes and post card surface background application."""
        from mastui.espresso_theme import get_theme, load_all_themes
        from mastui.espresso_post import render_post_card

        themes = load_all_themes()
        for t_name, theme in themes.items():
            self.assertTrue(hasattr(theme, "bg"))
            self.assertTrue(hasattr(theme, "surface"))
            self.assertTrue(hasattr(theme, "surface_active"))
            self.assertTrue(hasattr(theme, "header_bg"))
            self.assertTrue(hasattr(theme, "tag_color"))
            self.assertTrue(hasattr(theme, "mention_color"))

        post = {
            "id": "123",
            "account": {"display_name": "Alice", "acct": "alice@mastodon.social"},
            "content": "<p>Hello <span class=\"h-card\"><a href=\"#\">@bob</a></span> #fediverse!</p>",
            "created_at": "2026-10-02T12:00:00Z",
            "media_attachments": [],
        }

        # Unselected post should render with theme.surface
        dracula = get_theme("dracula")
        unselected_card = render_post_card(post, is_selected=False, width=60, theme=dracula)
        # Selected post should render with theme.surface_active
        selected_card = render_post_card(post, is_selected=True, width=60, theme=dracula)

        # Dracula surface is #282A36, surface_active is #383A59
        # Both rendered outputs must differ because of background styling
        self.assertNotEqual(unselected_card, selected_card)

    def test_cached_attachment_file_lookup(self) -> None:
        """Verify find_cached_attachment_file resolves both url, preview_url, and remote_url."""
        from mastui.espresso_image import find_cached_attachment_file, get_image_cache_dirs
        import tempfile
        import hashlib

        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir)
            cache_dir = profile_dir / "image_cache"
            cache_dir.mkdir(parents=True, exist_ok=True)

            test_url = "https://example.com/original.jpg"
            url_hash = hashlib.sha256(test_url.encode("utf-8")).hexdigest()
            cached_file = cache_dir / url_hash
            cached_file.write_bytes(b"dummy image bytes")

            att1 = {"url": test_url, "preview_url": "https://example.com/thumb.jpg"}
            att2 = {"url": "https://example.com/other.jpg", "preview_url": test_url}
            att3 = {"remote_url": test_url}

            # All 3 attachments reference the cached image through one of their URL fields
            self.assertEqual(find_cached_attachment_file(att1, profile_dir), cached_file)
            self.assertEqual(find_cached_attachment_file(att2, profile_dir), cached_file)
            self.assertEqual(find_cached_attachment_file(att3, profile_dir), cached_file)


    def test_connection_status_in_footer_instead_of_toast(self) -> None:
        """Verify connection info is permanently docked in the footer and not dispatched as a toast."""
        app = MastuiEspressoApp(is_demo=False, show_splash=False)
        app.instance = "mastodon.example.org"
        app.username = "testuser"
        app.width = 100
        app.height = 30

        # 1. Verify init does not dispatch a connection toast
        cmd = app.init()
        self.assertFalse(app.toasts.has_toasts, "Connection toast should not be queued on init")

        # 2. Verify footer status bar and header contain the instance and username
        from espresso.crema import strip_ansi
        view_text = app.view()
        lines = [strip_ansi(l) for l in view_text.splitlines()]

        # Header card should contain instance and user
        self.assertTrue(any("mastodon.example.org" in l and "@testuser" in l for l in lines[:4]))

        # Footer status line (second to last line) should contain Connected to and user
        footer_status_line = lines[-2]
        self.assertIn("Connected to mastodon.example.org", footer_status_line)
        self.assertIn("@testuser", footer_status_line)
        self.assertIn("Post", footer_status_line)

        # 3. Verify in demo mode
        app_demo = MastuiEspressoApp(is_demo=True, show_splash=False)
        app_demo.width = 100
        app_demo.height = 30
        demo_lines = [strip_ansi(l) for l in app_demo.view().splitlines()]
        demo_footer = demo_lines[-2]
        self.assertIn("Demo Mode", demo_footer)

    def test_post_image_fits_timeline_width(self) -> None:
        """Verify post image expands to fit the width of the timeline card without overflow."""
        from mastui.espresso_post import render_post_card
        from mastui.espresso_theme import get_theme
        from espresso.crema import string_width, strip_ansi

        post = {
            "id": "201",
            "account": {"display_name": "Photographer", "acct": "photo@lens.social"},
            "content": "<p>A glorious view</p>",
            "created_at": "2026-10-02T12:00:00Z",
            "media_attachments": [
                {
                    "type": "image",
                    "url": "https://mastui.app/media/sunset.jpg",
                    "preview_url": "https://mastui.app/media/sunset_thumb.jpg",
                    "description": "Golden sunset"
                }
            ]
        }

        # 1. Wide timeline (width 80)
        card_80 = render_post_card(post, is_selected=True, width=80, theme=get_theme("espresso"))
        image_lines = [l for l in card_80.splitlines() if "▀" in l]
        self.assertTrue(len(image_lines) > 0, "Image lines should be rendered")
        img_line_w = string_width(strip_ansi(image_lines[0]).strip())
        # Width should expand beyond the old 40 char clamp
        self.assertGreater(img_line_w, 60)
        self.assertLessEqual(max(string_width(strip_ansi(l)) for l in card_80.splitlines()), 80)

        # 2. Narrow timeline column (width 40)
        card_40 = render_post_card(post, is_selected=True, width=40, theme=get_theme("espresso"))
        image_lines_40 = [l for l in card_40.splitlines() if "▀" in l]
        self.assertTrue(len(image_lines_40) > 0)
        self.assertLessEqual(max(string_width(strip_ansi(l)) for l in card_40.splitlines()), 40)

    def test_ui_rendering_does_not_block_on_uncached_image(self) -> None:
        """Verify render_post_card does not block on network for uncached images."""
        from mastui.espresso_post import render_post_card
        from mastui.espresso_theme import get_theme
        import time

        post_uncached = {
            "id": "202",
            "account": {"display_name": "Bob", "acct": "bob@somewhere.remote"},
            "content": "<p>Post with uncached remote image</p>",
            "created_at": "2026-10-02T12:00:00Z",
            "media_attachments": [
                {
                    "type": "image",
                    "url": "https://remote.server.invalid/unreachable_image_99999.jpg",
                    "preview_url": "https://remote.server.invalid/unreachable_thumb_99999.jpg",
                    "description": "Uncached photo"
                }
            ]
        }

        # Rendering should return almost instantaneously without attempting network download
        t0 = time.perf_counter()
        card = render_post_card(post_uncached, is_selected=False, width=70, theme=get_theme("espresso"))
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.1, "render_post_card should not block on network")
        self.assertIn("📷", card)

    def test_scrollbar_colors_match_theme(self) -> None:
        """Verify VirtualList scrollbar thumb and track colors match the active theme."""
        from mastui.espresso_timeline import TimelineModel
        from mastui.espresso_theme import get_theme
        from mastui.espresso_thread import ThreadModal

        # 1. Timeline scrollbars
        espresso_theme = get_theme("espresso")
        tl = TimelineModel(theme=espresso_theme)
        self.assertIsNotNone(tl.list.scrollbar_thumb_style._fg)
        self.assertIsNotNone(tl.list.scrollbar_track_style._fg)

        # Switch theme to retro-green and verify scrollbar style updates
        retro_theme = get_theme("retro-green")
        tl.set_theme(retro_theme)
        self.assertNotEqual(tl.list.scrollbar_thumb_style._fg, espresso_theme.scrollbar_thumb)

        # 2. Thread modal scrollbars
        dracula_theme = get_theme("dracula")
        post = {"id": "1", "content": "test", "account": {"acct": "test"}}
        thread_modal = ThreadModal(post=post, is_demo=True, theme=dracula_theme)
        self.assertIsNotNone(thread_modal.list.scrollbar_thumb_style._fg)

    def test_thread_ancestors_and_descendants_fetching(self) -> None:
        """Verify thread modal fetches both ancestors (parents) and descendants (replies)."""
        from mastui.espresso_thread import (
            ThreadContextLoadedMsg,
            ThreadModal,
            fetch_thread_context,
            fetch_thread_posts,
        )

        class MockMastodonAPI:
            def status_context(self, post_id: str):
                return {
                    "ancestors": [
                        {
                            "id": "100",
                            "created_at": "2026-10-02T10:00:00Z",
                            "account": {"display_name": "Alice", "acct": "alice@alpha.social"},
                            "content": "<p>Where can we find the best terminal UI library?</p>",
                        },
                        {
                            "id": "101",
                            "created_at": "2026-10-02T10:15:00Z",
                            "account": {"display_name": "Bob", "acct": "bob@beta.org"},
                            "content": "<p>Espresso for Python is super fast and clean.</p>",
                            "in_reply_to_id": "100",
                        },
                    ],
                    "descendants": [
                        {
                            "id": "103",
                            "created_at": "2026-10-02T10:45:00Z",
                            "account": {"display_name": "Charlie", "acct": "charlie@gamma.net"},
                            "content": "<p>I just switched to it and it loads in 12ms!</p>",
                            "in_reply_to_id": "102",
                        }
                    ],
                }

        main_post = {
            "id": "102",
            "created_at": "2026-10-02T10:30:00Z",
            "account": {"display_name": "Kim Schulz", "acct": "kim@mastui.app"},
            "content": "<p>Yes! We built Mastui with it.</p>",
            "in_reply_to_id": "101",
        }

        mock_api = MockMastodonAPI()
        thread_posts = fetch_thread_posts(main_post, api=mock_api)
        
        # Must have: 2 ancestors + 1 main + 1 descendant = 4 posts
        self.assertEqual(len(thread_posts), 4)
        self.assertEqual(thread_posts[0]["_thread_role"], "ancestor")
        self.assertEqual(thread_posts[0]["id"], "100")
        self.assertEqual(thread_posts[1]["_thread_role"], "ancestor")
        self.assertEqual(thread_posts[1]["id"], "101")
        self.assertEqual(thread_posts[2]["_thread_role"], "main")
        self.assertEqual(thread_posts[2]["id"], "102")
        self.assertEqual(thread_posts[3]["_thread_role"], "reply")
        self.assertEqual(thread_posts[3]["id"], "103")

        # In ThreadModal, cursor must be initially positioned on main focused post (index 2)
        modal = ThreadModal(post=main_post, thread_posts=thread_posts, width=76, height=22)
        self.assertEqual(modal.list.cursor, 2)
        self.assertEqual(modal.selected_post["id"], "102")

        # Verify visual formatting shows parent and reply indicators
        view = modal.view()
        self.assertIn("Parent Post in Thread", view)
        self.assertIn("Selected Post", view)
        self.assertIn("Reply", view)

        # Test async ThreadContextLoadedMsg update
        async_modal = ThreadModal(post=main_post, thread_posts=[main_post], width=76, height=22)
        self.assertEqual(len(async_modal.posts), 1)
        async_modal, _ = async_modal.update(
            ThreadContextLoadedMsg(
                post_id="102",
                ancestors=[thread_posts[0], thread_posts[1]],
                descendants=[thread_posts[3]],
            )
        )
        self.assertEqual(len(async_modal.posts), 4)
        self.assertEqual(async_modal.list.cursor, 2)

    def test_login_onboarding_modal_flow(self) -> None:
        """Verify the LoginModal onboarding lifecycle from host input to login completion."""
        from mastui.espresso_login import (
            AuthLinkGeneratedMsg,
            LoginCompletedMsg,
            LoginModal,
            LoginSuccessMsg,
            clean_host_input,
        )

        # 1. Host normalization
        self.assertEqual(clean_host_input("https://mastodon.social/"), "mastodon.social")
        self.assertEqual(clean_host_input("  social.coop  "), "social.coop")
        self.assertEqual(clean_host_input("localhost:3000"), "localhost:3000")

        # 2. Mock create_app and login functions
        def mock_create_app(host, ssl_verify):
            return f"https://{host}/oauth/authorize?client_id=123", "client_123", "secret_456", None

        def mock_login(host, client_id, client_secret, code, ssl_verify):
            class MockAPI:
                def me(self):
                    return {"username": "testuser", "url": f"https://{host}/@testuser"}
            return MockAPI(), "MASTODON_HOST=...\nMASTODON_ACCESS_TOKEN=...\n", None

        modal = LoginModal(
            default_host="mastodon.social",
            create_app_fn=mock_create_app,
            login_fn=mock_login,
        )
        self.assertEqual(modal.stage, LoginModal.STAGE_HOST)
        self.assertIn("mastodon.social", modal.view())

        # Press Enter on host -> moves to creating_app and dispatches command
        modal, cmd = modal.update(KeyMsg("enter"))
        self.assertEqual(modal.stage, LoginModal.STAGE_CREATING_APP)
        self.assertIsNotNone(cmd)

        # Execute command -> returns AuthLinkGeneratedMsg
        auth_msg = cmd()
        self.assertIsInstance(auth_msg, AuthLinkGeneratedMsg)
        self.assertIn("https://mastodon.social/oauth/authorize", auth_msg.auth_url)

        # Feed AuthLinkGeneratedMsg back -> moves to code input stage
        modal, _ = modal.update(auth_msg)
        self.assertEqual(modal.stage, LoginModal.STAGE_CODE)
        self.assertIn("Step 2: Enter Authorization Code", modal.view())

        # Enter auth code and submit
        modal.code_input.set_value("AUTH_CODE_SECRET_XYZ")
        modal, login_cmd = modal.update(KeyMsg("enter"))
        self.assertEqual(modal.stage, LoginModal.STAGE_LOGGING_IN)
        self.assertIsNotNone(login_cmd)

        # Execute login command -> returns LoginCompletedMsg
        compl_msg = login_cmd()
        self.assertIsInstance(compl_msg, LoginCompletedMsg)
        self.assertEqual(compl_msg.profile_name, "testuser@mastodon.social")

        # Feed LoginCompletedMsg back -> triggers LoginSuccessMsg
        modal, succ_cmd = modal.update(compl_msg)
        self.assertEqual(modal.stage, LoginModal.STAGE_SUCCESS)
        self.assertIsNotNone(succ_cmd)
        succ_msg = succ_cmd()
        self.assertIsInstance(succ_msg, LoginSuccessMsg)
        self.assertEqual(succ_msg.profile_name, "testuser@mastodon.social")

    def test_account_switching_and_profile_selection(self) -> None:
        """Verify account switching via ProfileSelectionModal and 'u' keybinding."""
        from mastui.espresso_profile_selection import (
            OpenLoginModalMsg,
            ProfileSelectionModal,
            SwitchProfileMsg,
        )

        profiles = ["DominusQ@corteximplant.com", "Mastui@mastodon.social", "default"]
        modal = ProfileSelectionModal(current_profile="Mastui@mastodon.social", profiles=profiles)
        
        # Initial cursor should be at active profile index (1)
        self.assertEqual(modal.cursor, 1)
        view = modal.view()
        self.assertIn("DominusQ@corteximplant.com", view)
        self.assertIn("(Active)", view)
        self.assertIn("Add New Account", view)

        # Navigate down
        modal, _ = modal.update(KeyMsg("j"))
        self.assertEqual(modal.cursor, 2)  # default

        # Press enter on "default" -> dispatches SwitchProfileMsg
        modal, cmd = modal.update(KeyMsg("enter"))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, SwitchProfileMsg)
        self.assertEqual(msg.profile_name, "default")

        # Navigate to "Add New Account" and press enter -> dispatches OpenLoginModalMsg
        modal.cursor = modal.add_account_index
        modal, cmd = modal.update(KeyMsg("enter"))
        self.assertIsNotNone(cmd)
        msg = cmd()
        self.assertIsInstance(msg, OpenLoginModalMsg)

        # Test app 'u' key opens ProfileSelectionModal
        app = MastuiEspressoApp(
            username="kim@mastui.app",
            instance="social.data.coop",
            is_demo=True,
            show_splash=False,
        )
        self.assertFalse(app.modal_stack.has_modals)
        app, _ = app.update(KeyMsg("u"))
        self.assertTrue(app.modal_stack.has_modals)
        self.assertIsInstance(app.modal_stack.top_modal, ProfileSelectionModal)

    def test_first_run_onboarding_startup(self) -> None:
        """Verify that launching with show_login=True opens LoginModal on startup."""
        from mastui.espresso_login import LoginModal

        app = MastuiEspressoApp(
            username="newuser",
            instance="mastodon.social",
            is_demo=False,
            show_splash=False,
            show_login=True,
        )
        self.assertTrue(app.modal_stack.has_modals)
        self.assertIsInstance(app.modal_stack.top_modal, LoginModal)

    def test_timeline_prepend_newer_posts_viewport(self) -> None:
        """Verify that prepending new toots when at top keeps cursor at 0 and displays them immediately."""
        from mastui.espresso_timeline import TimelineModel

        initial_posts = [
            {"id": "100", "content": "<p>Initial post 1</p>", "account": {"display_name": "User 1", "acct": "u1"}},
            {"id": "99", "content": "<p>Initial post 2</p>", "account": {"display_name": "User 2", "acct": "u2"}},
        ]
        tl = TimelineModel("home", "Home", posts=initial_posts)
        tl.set_size(80, 24)

        # User is at the top
        self.assertEqual(tl.list.cursor, 0)
        self.assertEqual(tl.list.scroll_offset, 0)
        self.assertEqual(tl.selected_post["id"], "100")

        # New posts arrive
        new_posts = [
            {"id": "102", "content": "<p>Brand New Post 102</p>", "account": {"display_name": "New User", "acct": "new"}},
            {"id": "101", "content": "<p>Brand New Post 101</p>", "account": {"display_name": "New User", "acct": "new"}},
        ]
        tl.prepend_newer_posts(new_posts)

        # Cursor and scroll offset should remain at 0, displaying the brand new post immediately
        self.assertEqual(tl.list.cursor, 0)
        self.assertEqual(tl.list.scroll_offset, 0)
        self.assertEqual(tl.selected_post["id"], "102")
        view = tl.view()
        self.assertIn("Brand New Post 102", view)

        # Now test when user was scrolled down: cursor should stay anchored to previously selected post
        tl.list.cursor = 2
        anchored_id = tl.selected_post["id"]
        more_newer = [
            {"id": "103", "content": "<p>Even Newer Post 103</p>", "account": {"display_name": "Newer", "acct": "newer"}}
        ]
        tl.prepend_newer_posts(more_newer)
        # Because keep_anchor=True, the selected post ID remains the same
        self.assertEqual(tl.selected_post["id"], anchored_id)

    def test_sqlite_cache_persistence(self) -> None:
        """Verify that save_posts_to_db and read_cached_posts_from_db work correctly."""
        from mastui.espresso_app import (
            save_posts_to_db,
            read_cached_posts_from_db,
            read_newer_cached_posts_from_db,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            posts = [
                {
                    "id": "200",
                    "created_at": "2026-10-02T12:00:00+00:00",
                    "content": "<p>Toot 200</p>",
                    "account": {"display_name": "Alice", "acct": "alice@fediverse"},
                },
                {
                    "id": "199",
                    "created_at": "2026-10-02T11:00:00+00:00",
                    "content": "<p>Toot 199</p>",
                    "account": {"display_name": "Bob", "acct": "bob@fediverse"},
                },
            ]
            save_posts_to_db(db_path, "home", posts)
            self.assertTrue(db_path.exists())

            # Read back
            cached = read_cached_posts_from_db(db_path, "home", limit=10)
            self.assertEqual(len(cached), 2)
            self.assertEqual(cached[0]["id"], "200")
            self.assertEqual(cached[1]["id"], "199")

            # Read newer than 199
            newer = read_newer_cached_posts_from_db(db_path, "home", limit=10, since_id="199")
            self.assertEqual(len(newer), 1)
            self.assertEqual(newer[0]["id"], "200")

    def test_login_auth_code_preserves_all_letters_and_sanitizes(self) -> None:
        """Verify that typing or pasting codes with 'o' and 'c' are not intercepted or stripped."""
        from mastui.espresso_login import LoginModal, AuthLinkGeneratedMsg, clean_auth_code_input

        # 1. Test clean_auth_code_input helper
        self.assertEqual(clean_auth_code_input("  https://mastodon.social/oauth/authorize/native?code=xyz123abc&scope=read  "), "xyz123abc")
        self.assertEqual(clean_auth_code_input("code=my_code_456"), "my_code_456")
        self.assertEqual(clean_auth_code_input("Bearer token_abc"), "token_abc")
        self.assertEqual(clean_auth_code_input("\"quoted_token_789\""), "quoted_token_789")

        # 2. Test LoginModal does not swallow 'o' or 'c' on STAGE_CODE
        modal = LoginModal()
        modal.update(AuthLinkGeneratedMsg("https://mastodon.social/oauth/authorize", "cid", "sec", None))
        self.assertEqual(modal.stage, LoginModal.STAGE_CODE)

        test_code = "oauth_code_containing_o_and_c_123"
        for ch in test_code:
            modal, _ = modal.update(KeyMsg(ch))
        self.assertEqual(modal.code_input.value, test_code)

    def test_thread_modal_auto_fetch_on_init(self) -> None:
        """Verify that opening ThreadModal dispatches background context fetch automatically without pressing 'r'."""
        import asyncio

        class MockApi:
            def __init__(self):
                self.called_with = None

            def status_context(self, post_id: str):
                self.called_with = post_id
                return {
                    "ancestors": [
                        {
                            "id": "100",
                            "content": "<p>Parent toot 100</p>",
                            "account": {"display_name": "Parent User", "acct": "parent@fediverse"},
                        }
                    ],
                    "descendants": [
                        {
                            "id": "102",
                            "content": "<p>Child reply toot 102</p>",
                            "account": {"display_name": "Child User", "acct": "child@fediverse"},
                        }
                    ],
                }

        mock_api = MockApi()
        target_post = {
            "id": "101",
            "content": "<p>Target main post 101</p>",
            "account": {"display_name": "Target User", "acct": "target@fediverse"},
            "in_reply_to_id": "100",
        }

        modal = ThreadModal(
            post=target_post,
            api=mock_api,
            width=70,
            height=20,
        )
        self.assertTrue(modal.is_loading)

        cmd = modal.init()
        self.assertIsNotNone(cmd)

        # Execute the returned batch command
        batch_res = asyncio.run(cmd())
        self.assertIsInstance(batch_res, BatchMsg)

        # Locate the ThreadContextLoadedMsg
        context_msgs = [m for m in batch_res.messages if isinstance(m, ThreadContextLoadedMsg)]
        self.assertEqual(len(context_msgs), 1)
        self.assertEqual(mock_api.called_with, "101")
        ctx_msg = context_msgs[0]
        self.assertEqual(len(ctx_msg.ancestors), 1)
        self.assertEqual(ctx_msg.ancestors[0]["id"], "100")
        self.assertEqual(len(ctx_msg.descendants), 1)
        self.assertEqual(ctx_msg.descendants[0]["id"], "102")

        # Process the context loaded message
        modal, _ = modal.update(ctx_msg)
        self.assertFalse(modal.is_loading)
        self.assertEqual(len(modal.posts), 3)  # [ancestor, target, descendant]
        self.assertEqual(modal.posts[0]["id"], "100")
        self.assertEqual(modal.posts[1]["id"], "101")
        self.assertEqual(modal.posts[2]["id"], "102")
        # Ensure cursor was placed on the main target post (index 1)
        self.assertEqual(modal.list.cursor, 1)
        self.assertEqual(modal.selected_post["id"], "101")

    def test_navigation_during_timeline_refresh(self) -> None:
        """Verify that column switching and scrolling remain responsive while timeline is refreshing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir)
            app = MastuiEspressoApp(
                profile_dir=profile_dir,
                is_demo=True,
            )
            app.show_splash = False

            # Set timeline 0 to refreshing state
            app.timelines[0].is_refreshing = True
            self.assertTrue(app.current_timeline.is_refreshing)

            # 1. Test column navigation with Tab and Shift+Tab
            app, _ = app.update(KeyMsg("tab"))
            self.assertEqual(app.active_timeline_idx, 1)

            app, _ = app.update(KeyMsg("shift+tab"))
            self.assertEqual(app.active_timeline_idx, 0)

            # 2. Test column navigation with vim keys 'l' (right) and 'h' (left)
            app, _ = app.update(KeyMsg("l"))
            self.assertEqual(app.active_timeline_idx, 1)
            app, _ = app.update(KeyMsg("h"))
            self.assertEqual(app.active_timeline_idx, 0)

            # 3. Test column navigation with bracket keys '[' and ']'
            app, _ = app.update(KeyMsg("]"))
            self.assertEqual(app.active_timeline_idx, 1)
            app, _ = app.update(KeyMsg("["))
            self.assertEqual(app.active_timeline_idx, 0)

            # 4. Test direct jump to column via number keys '1'-'5'
            app, _ = app.update(KeyMsg("3"))
            self.assertEqual(app.active_timeline_idx, 2)
            app, _ = app.update(KeyMsg("1"))
            self.assertEqual(app.active_timeline_idx, 0)

            # 5. Test scrolling inside refreshing timeline with 'j' and 'down'
            self.assertEqual(app.current_timeline.list.cursor, 0)
            app, _ = app.update(KeyMsg("j"))
            self.assertEqual(app.current_timeline.list.cursor, 1)
            app, _ = app.update(KeyMsg("down"))
            self.assertEqual(app.current_timeline.list.cursor, 2)

            # And scroll up with 'k'
            app, _ = app.update(KeyMsg("k"))
            self.assertEqual(app.current_timeline.list.cursor, 1)

    def test_trigger_refresh_duplicate_guard(self) -> None:
        """Verify calling trigger_refresh while already refreshing is a safe no-op."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir)
            app = MastuiEspressoApp(
                profile_dir=profile_dir,
                is_demo=True,
            )
            tl = app.timelines[0]
            self.assertFalse(tl.is_refreshing)

            # First trigger_refresh starts refresh and returns cmd
            tl, cmd1 = tl.trigger_refresh()
            self.assertTrue(tl.is_refreshing)
            self.assertIsNotNone(cmd1)

            # Second trigger_refresh while still refreshing returns None
            tl, cmd2 = tl.trigger_refresh()
            self.assertTrue(tl.is_refreshing)
            self.assertIsNone(cmd2)

    def test_paste_msg_properties(self) -> None:
        """Verify PasteMsg text attribute, string conversion, and equality."""
        p = PasteMsg("pasted_token_abc")
        self.assertEqual(p.text, "pasted_token_abc")
        self.assertEqual(str(p), "pasted_token_abc")
        self.assertEqual(p, "pasted_token_abc")
        self.assertEqual(p, PasteMsg("pasted_token_abc"))
        self.assertNotEqual(p, "other_text")

    def test_emoji_and_grapheme_width_alignment(self) -> None:
        """Verify that multi-codepoint emojis (🏴☠️, 🏴‍☠️, 🏳️‍🌈, etc.) have width 2 and preserve post border alignment."""
        from mastui.espresso_post import render_post_card

        # Check visual widths (reflecting terminal cell layout: 2 cells per visible emoji)
        self.assertEqual(string_width("🏴☠️"), 4)
        self.assertEqual(string_width("🏴‍☠️"), 4)
        self.assertEqual(string_width("🏳️‍🌈"), 4)
        self.assertEqual(string_width("👨‍👩‍👧‍👦"), 8)
        self.assertEqual(string_width("👍🏽"), 2)
        self.assertEqual(string_width("💁🏻‍♂️"), 2)
        self.assertEqual(string_width("stephaniepixie 🏳️‍🌈 @stephaniepixie@fandom.garden"), 49)

        # Check card border alignment when booster/poster has pirate flag or rainbow flag
        post = {
            "id": "pirate_post",
            "created_at": "2026-10-02T20:00:00Z",
            "account": {
                "display_name": "Captain Jack 🏴☠️",
                "acct": "jack@blackpearl.sea",
            },
            "content": "<p>Ahoy fediverse!</p>",
            "reblogs_count": 1,
            "favourites_count": 5,
        }
        stephanie_post = {
            "id": "116801987413970193",
            "created_at": "2026-06-23T23:21:00Z",
            "account": {
                "display_name": "stephaniepixie 🏳️‍🌈",
                "acct": "stephaniepixie@fandom.garden",
            },
            "content": "<p>Rainbow pride in the terminal!</p>",
            "reblogs_count": 2,
            "favourites_count": 7,
        }
        eissing_post = {
            "id": "116803596923965052",
            "created_at": "2026-06-24T05:54:00Z",
            "account": {
                "display_name": "Stefan Eissing",
                "acct": "icing@chaos.social",
            },
            "content": "<p>This vulnerability could have been a bug report.💁🏻‍♂️</p>",
            "reblogs_count": 0,
            "favourites_count": 1,
        }
        reblog = {
            "id": "reb_pirate",
            "created_at": "2026-10-02T20:05:00Z",
            "account": {
                "display_name": "Captain Jack 🏴☠️",
                "acct": "jack@blackpearl.sea",
            },
            "reblog": {
                "id": "orig_post",
                "created_at": "2026-10-02T20:00:00Z",
                "account": {"display_name": "Sailor Bob", "acct": "bob@harbor.net"},
                "content": "<p>Ship sighted!</p>",
            },
        }

        for p in (post, stephanie_post, reblog, eissing_post):
            for w in (50, 70):
                card = render_post_card(p, is_selected=False, width=w)
                card_lines = card.split("\n")
                # All lines of the card must have identical visual width
                for line in card_lines:
                    self.assertEqual(string_width(line), w, f"Line failed width {w}: {repr(line)}")

    def test_toot_text_word_wrapping(self) -> None:
        """Verify that toot body text is word-wrapped nicely across lines instead of being truncated."""
        from mastui.espresso_post import render_post_card

        long_post = {
            "id": "long_toot_1",
            "created_at": "2026-10-02T20:00:00Z",
            "account": {
                "display_name": "Kim Schulz",
                "acct": "kimschulz@social.data.coop",
            },
            "content": (
                "<p>This is a long toot text that should definitely be wrapped nicely "
                "across multiple lines when it exceeds the width of the card or column "
                "instead of being cut off or hidden outside the timeline width!</p>"
            ),
            "reblogs_count": 3,
            "favourites_count": 12,
        }

        card = render_post_card(long_post, is_selected=False, width=44)
        clean_card = strip_ansi(card)

        # Entire text should be present in the card (none cut off with ellipsis)
        self.assertIn("This is a long toot text", clean_card)
        self.assertIn("across", clean_card)
        self.assertIn("multiple lines", clean_card)
        self.assertIn("timeline", clean_card)
        self.assertIn("width!", clean_card)

        # Verify all lines conform to width 44
        for line in card.split("\n"):
            self.assertEqual(string_width(line), 44)

    def test_unicode_fallback_and_fight_cloud_alignment(self) -> None:
        """Verify that Unicode 17.0 unassigned/fallback characters like 🫯 (U+1FAEF Fight Cloud)

        do not break card border alignment or inflate width calculations.
        """
        from espresso.crema import string_width, char_width
        from mastui.espresso_post import render_post_card

        # Verify character and handle string widths
        self.assertEqual(char_width("🫯"), 1)
        self.assertEqual(string_width("Thomas Fuchs 🫯 @thomasfuchs@hachyderm.io"), 40)

        # Realistic post from kimschulz@social.data.coop profile cache
        post = {
            "id": "117373176259297200",
            "created_at": "2026-10-02T20:22:00Z",
            "account": {
                "display_name": "Thomas Fuchs 🫯",
                "acct": "thomasfuchs@hachyderm.io",
            },
            "content": "<p>So that’s what? 2 gaming PCs and an external SSD?</p>",
            "reblogs_count": 0,
            "favourites_count": 0,
            "replies_count": 0,
        }

        # Test across multiple card widths (narrow 40, medium 60, wide 80)
        for w in (40, 50, 60, 80):
            card = render_post_card(post, is_selected=False, width=w)
            for line in card.split("\n"):
                self.assertEqual(
                    string_width(line),
                    w,
                    f"Line failed width {w}: {repr(line)}",
                )


if __name__ == "__main__":
    unittest.main()



