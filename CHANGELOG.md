# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - Unreleased

### Added
- **Reply All:** Automatically include all participants when replying to a post.
- **Jump to Top:** Use the `g` key to instantly scroll to the top of a timeline.
- **Log Viewer:** A hidden log viewer (`F12`) is available when running with `--debug`.
- **Enhanced Notifications:** Get detailed pop-up notifications for DMs and optionally for mentions, follows, boosts, and favourites.
- **Edit Posts:** Edit your own posts using the `e` key.
- **Direct Messages:** A dedicated timeline for viewing and replying to Direct Messages.
- **Multi-Profile Support:** Log into and switch between multiple accounts.
- **Search:** Full-text search for users, hashtags, and posts.
- **Mute/Block:** Mute and block users from their profile pages.
- **Polls:** View, vote on, and create polls.
- **Custom Themes:** Support for user-created custom themes.

### Changed
- **Optimized Startup:** The app now loads the last used profile automatically and displays the splash screen immediately while loading data in the background.
- **Lazy Loading:** Images are now "lazy loaded" only when they scroll into view, improving performance and reducing bandwidth.
- **UI Polish:**
    - The selected item in the active timeline is now clearly highlighted.
    - Timestamps now correctly show both date and time.
    - Toggling the DM timeline is now a smooth operation without UI jumping.
    - Scroll position is preserved during timeline refreshes.
- **Performance:** Drastically reduced the number of API calls on startup, making the application much faster.

### Fixed
- Correctly handle "boost" and "like" actions in all views, including threads and hashtag timelines.
- Numerous small bug fixes and stability improvements.

## [0.7.0]

### Added
- Support for creating and voting on polls.
- Option to force a single-timeline mode for narrow screens.
- A retro green-on-black theme.

### Changed
- Improved message rendering with `BeautifulSoup`.
- Made the single-column mode more dynamic.

## [0.5.3]

### Added
- Support for Sixel and TGP (iTerm) image rendering.
- A help screen (`?`) detailing key bindings.

### Fixed
- Corrected a bug where duplicate IDs could cause errors in thread view.
- Fixed an issue with the authentication link creation.

## [0.5.0]

### Added
- Initial support for viewing images in timelines.
- User-selectable dark and light themes.
- Configuration for auto-refresh intervals.

### Changed
- Improved startup time.
- Timestamps are now displayed on posts.

## [0.4.1]

### Fixed
- Corrected an issue with storing theme selections.

## [0.3.4]

### Added
- Profile view screen to see user bios and stats.

## [0.2.0]

### Added
- Thread view to see the context of a conversation.
- SSL verification is now handled correctly.
- Visual indicators for boosting and liking posts.

### Changed
- Optimized the boost and like functionality.
- Posts are now preserved on timeline refresh.
