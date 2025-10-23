# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-10-04

### Added

- **Local Timeline:** Added support for viewing the local timeline.
- **Roadmap:** Added a `ROADMAP.md` file to outline future development.

### Fixed

- **Network Errors:** Improved handling of network timeouts and connection errors.
- **Image Loading:** Fixed a crash that could occur when loading images in the background.
- **Poll Notifications:** Fixed a crash that could occur when receiving a notification for a poll on a deleted post.

## [1.1.0] - 2025-10-04

### Added

- **Customizable Keybindings:** Users can now define their own keybindings via an in-app screen.

## [1.0.1] - 2025-09-12

### Fixed

- Corrected an issue where refreshing the thread view would fail.
- Fixed a bug that prevented replying within the thread view.

## [1.0.0] - 2025-09-06

### Added

- **Direct Messages:** A dedicated timeline for viewing and replying to Direct Messages.
- **Multi-Profile Support:** Log into and switch between multiple accounts.
- **Search:** Full-text search for users, hashtags, and posts.
- **Edit Posts:** Edit your own posts using the `e` key.
- **Mute/Block:** Mute and block users from their profile pages.
- **Jump to Top:** Use the `g` key to instantly scroll to the top of a timeline.
- **Log Viewer:** A hidden log viewer (`F12`) is available when running with `--debug`.
- **Enhanced Notifications:** Get detailed pop-up notifications for DMs and optionally for mentions, follows, boosts, and favourites.

### Changed

- **Optimized Startup:** The app now loads the last used profile automatically and displays the splash screen immediately while loading data in the background.
- **UI Polish:**
  - The selected item in the active timeline is now clearly highlighted.
  - Timestamps now correctly show both date and time.
  - Toggling the DM timeline is now a smooth operation without UI jumping.
  - Scroll position is preserved during timeline refreshes.
- **Performance:** Drastically reduced the number of API calls on startup, making the application much faster.
- **Reply All:** Automatically include all participants when replying to a post.

### Fixed

- Correctly handle "boost" and "like" actions in all views, including threads and hashtag timelines.
- Images now load reliably after a regression with the lazy loading feature.
- Numerous small bug fixes and stability improvements.

## [0.9.0] - 2025-08-29

### Added

- **Polls:** View, vote on, and create polls.
- **Custom Themes:** Support for user-created custom themes.
- **Profile Pictures:** Avatars are now displayed in profile views.
- **Mouse Support:** Full mouse support for scrolling and interaction.
- **Caching:** A backend cache was added to improve performance and preserve posts between sessions.

### Changed

- **UI Overhaul:** Major UI cleanup and streamlining of modal windows. All styling is now consolidated in the main CSS file.
- **Onboarding:** The login and authentication flow has been improved and made more robust.
- **Clickable Links:** Hashtags and links in posts are now clickable.

### Fixed

- **Thread View:** Corrected bugs related to duplicate IDs and rendering issues in conversation threads.
- **Authentication:** Fixed several issues related to the authentication flow and SSL verification.
- **Scrolling:** Fixed an issue where the view would jump back to the top when scrolling with the mouse.

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
