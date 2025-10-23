# Mastui Development Roadmap

This document outlines the architectural design of Mastui and provides a roadmap for future development, including new features, UI enhancements, and support for other platforms.

## 🚀 Project Philosophy

Mastui aims to be a fast, efficient, and feature-rich terminal client for Mastodon and the wider Fediverse. Our development philosophy is guided by:

- **Performance:** The UI should always be responsive. Blocking operations must be handled in background workers.
- **Usability:** Key bindings should be intuitive, and user workflows should be as efficient as possible.
- **Extensibility:** The codebase should be modular and well-documented to encourage community contributions.
- **Stability:** New features should be accompanied by tests to ensure the application remains stable.

---

## 🏛️ Application Architecture

Mastui is built on the [Textual](https://textual.textualize.io/) framework. Understanding its architecture is key to contributing effectively.

### Core Components

- **`app.py` - The Conductor:**
  - This is the main application class, inheriting from `textual.app.App`.
  - It is responsible for orchestrating the entire application lifecycle, including profile loading, managing screens, and handling global actions and key bindings.
  - It holds the primary instances of the Mastodon API, the configuration (`Config`), and the cache (`Cache`).
  - All background workers for fetching data are initiated here.

- **`timeline.py` - The Columns:**
  - Defines the `Timeline` widget, which represents a single column in the main view (e.g., Home, Local, Notifications).
  - Each `Timeline` instance is responsible for its own data fetching, auto-refresh timers, and rendering of posts.
  - It contains a `TimelineContent` widget, which is the scrollable container for the actual posts.

- **`widgets.py` - The Building Blocks:**
  - Contains the widgets for displaying individual items like `Post`, `Notification`, and `ConversationSummary`.
  - These widgets are responsible for their own layout and for displaying data passed to them (e.g., post content, author, timestamps).
  - They also emit messages for user actions like `LikePost` and `BoostPost`.

- **`*_screen.py` - The Modal Views:**
  - Files like `profile_screen.py`, `thread_screen.py`, `config_screen.py`, etc., define modal screens that are pushed on top of the main view.
  - They are self-contained and are responsible for their own layout, data loading, and user interactions.

### Data and State Management

- **`profile_manager.py`:** Handles the multi-profile system. It manages the creation, deletion, and loading of profiles stored in `~/.config/mastui/profiles/`.
- **`config.py`:** The `Config` class loads and saves all profile-specific settings (theme, API keys, timeline visibility, etc.) from the `.env` file within each profile directory.
- **`keybind_manager.py`:** Manages loading, saving, and applying custom key bindings from a `keymap.json` file in the profile directory.
- **`cache.py`:** Implements an SQLite-based cache for posts and conversations. This provides persistence between sessions and improves startup performance.

### Event Flow (Example: Liking a Post)

1.  User presses the 'l' key in a focused `Timeline`.
2.  The `on_key` handler in `timeline.py` calls `self.like_post()`.
3.  This calls `self.content_container.like_post()` in `timeline_content.py`.
4.  `like_post()` identifies the selected `Post` widget and posts a `LikePost` message to the app's message queue.
5.  `app.py` receives the `LikePost` message via its `@on(LikePost)` handler.
6.  The handler starts a background worker (`do_like_post`) to make the API call to the Mastodon server.
7.  The worker, upon completion, posts a `PostStatusUpdate` message with the updated post data.
8.  `app.py` receives the `PostStatusUpdate` message and finds the corresponding `Post` widget to update its display.

---

## 🗺️ Future Features & Ideas

This is a list of potential features and tasks, categorized by area. Contributions are welcome!

### Core Mastodon Features

- **[High Priority] Bookmark Support:**
  - Implement a `bookmark_post` action and key binding.
  - Create a new `Timeline` type for viewing bookmarked posts (`api.bookmarks()`).
- **[High Priority] Content Filtering:**
  - Automatically fetch and respect server-side keyword filters.
  - Hide posts that match filter criteria.
  - *Stretch Goal:* An interface within Mastui to add, edit, and delete filters.
- **[Medium Priority] User List Timelines:**
  - Add an interface (perhaps in the profile switcher or a new menu) to view user-created lists as timelines (`api.timeline_list(list_id)`).
- **[Medium Priority] Post Management:**
  - Ability to delete your own posts.
  - Ability to view who has boosted or favourited a post.
- **[Low Priority] Post Drafts:**
  - Save post content from the composer window to a local draft.
  - Prompt to load the draft when opening the composer again.

### UI/UX Enhancements

- **Command Palette:**
  - A floating search bar (e.g., triggered by `Ctrl+P`) that allows fuzzy-finding and executing any action in the app (e.g., "Compose Post", "Switch Profile", "Toggle DMs"). This would be a major power-user feature.
- **More Granular Theming:**
  - Allow users to customize individual colors (e.g., timestamp color, boost text color) in the theme file.
- **Improved Image Viewer:**
  - An overlay or pop-up image viewer that can display images at a larger size.
  - Support for animated GIFs.
- **Link URL Previews:**
  - Show the full URL of a link when it is hovered or selected.

### Supporting Other Platforms (ActivityPub)

Supporting other Fediverse platforms requires adapting to their unique API endpoints and data structures. The priority is based on API similarity to Mastodon.

1.  **Pleroma / Akkoma (High Priority / Easy):**
    - **Why:** These platforms maintain a high degree of Mastodon API compatibility. Many features should work out-of-the-box.
    - **Tasks:** Identify and handle Pleroma/Akkoma-specific features like longer character limits, Markdown support in posts (instead of HTML), and different reaction emoji.

2.  **GoToSocial (Medium Priority / Medium):**
    - **Why:** Aims for Mastodon client API compatibility but is a newer project with a more focused feature set.
    - **Tasks:** Thoroughly test all existing features against a GoToSocial instance. Identify any missing API endpoints (e.g., polls, advanced search) and gracefully disable those features when connected to a GoToSocial server.

3.  **Misskey / Firefish / Calckey (Low Priority / Hard):**
    - **Why:** These platforms have their own distinct API that is very different from Mastodon's. Supporting them would require a significant abstraction layer.
    - **Tasks:** This would be a major undertaking. It would involve creating a separate API translation layer that maps Misskey API calls and objects to the structure Mastui currently expects, or refactoring Mastui's core to not be so tightly coupled to Mastodon's data structures.

4.  **Friendica (Low Priority / Very Hard):**
    - **Why:** Friendica has its own rich history and API that predates much of the modern Fediverse's Mastodon-centric API compatibility. It has some Mastodon API support, but it's not as complete.
    - **Tasks:** Similar to Misskey, this would require a dedicated API abstraction layer and extensive testing.

### Technical Debt & Refactoring

- **Comprehensive Test Suite:**
  - Build out a test suite using `pytest`.
  - Mock the Mastodon API to test application logic without making network calls.
- **Code Documentation:**
  - A full pass to add docstrings and type hints to all public methods and classes.
- **State Management Refactor:**
  - Consider a more centralized state management approach (like a dedicated `Store` class) instead of passing the `app` object down to many widgets. This could make the app easier to reason about as it grows in complexity.
