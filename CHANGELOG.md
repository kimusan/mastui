# Changelog

All notable changes to this project are documented in this file.

This changelog is derived from git release tags and commit history on `main`.

## [Unreleased]

- No changes yet.

## [1.8.0] - 2026-02-28

- fix(auth): narrow network exception handling
- fix(login): improve cancel flow and clickable auth link
- refactor(update): narrow exception handling in version checks
- fix(profile): prevent duplicate timelines after account switch
- chore(lint): remove unused imports and variables
- fix(security): only open http and https links
- refactor(updates): reduce widget lookup passes across views
- fix(utils): correct markdown link conversion regex
- refactor(login): remove duplicate on_login handler
- fix(security): restrict profile env file permissions
- fix(security): stop logging auth secrets
- fix(update): use package version fallback safely
- fix(login): correctly handle https host input
- docs(filters): document filter manager workflow
- feat(filters): add direct shortcut and centered modals
- fix(filters): make context selection interactive
- fix(filters): use ListItem placeholders in list views
- feat(filters): add server-side filter management UI

## [1.7.1] - 2026-02-13

- fix(startup): delay splash dismissal after timeline mount
- chore(release): automate changelog updates
- fix(startup): prevent splash deadlock on macOS

## [1.7.0] - 2026-01-17

- chore(release): v1.7.0
- fix(Issue#14): Handle ongoing Worker thread on exit
- refactor(rendering):  streamline timeline/UI performance and polish profile UX
- fix(issue#14): dont crash when scrolling to the end
- docs(README): updated readme with missing features and more

## [1.6.0] - 2025-12-07

- chore(release): v1.6.0
- fix(rendering): safe rendering
- feat(autocomplete): initial auto complete support
- fix(rendering): fixed problem with rendering certain characters

## [1.5.1] - 2025-12-05

- chore(release): v1.5.1
- fix(keybinding): dont show all keybindings in footer

## [1.5.0] - 2025-12-05

- chore(release): v1.5.0
- feat(keybindings): Added binding configuration for next/prev column
- feat(languages): Initial support for post language config

## [1.4.0] - 2025-12-04

- chore(release): v1.4.0
- fix(url_selector): problems with copying url + cleanup
- fix(onboarding): better warning for missing wl-clipboard
- feat(version_check): new version notification

## [1.3.0] - 2025-11-24

- chore(release): v1.3.0
- fix(help): fallback for ? key
- feat(boost): added unboost
- feat(delete): deletion confirm_dialog added
- feat(posts): delete posts
- refactor(UI): cleanup and notifications
- fix(Issue#13): Make it possible to use decimal refresh-interval
- feat(PR#12): url extractor functionality
- docs(CHANGELOG): updated changelog for 1.2.0 release

## [1.2.0] - 2025-10-23

- chore(release): v1.2.0
- docs(ROADMAP): Added a roadmap file
- fix(issue#11): possible fix for noneType error
- feat(issue#10): Added support for local timeline
- chore(files): add missing file
- fix(network): better handling of network errors
- fix(images): fixed a problem with exceptions from image rendering
- chore(release): v1.1.0
- chore(release): v1.2.0
- feat(config): user-defined keybinding
- chore(release): v1.1.0

## [1.0.1] - 2025-09-12

- chore(release): v1.0.1
- fix(thread): thread view refresh broken
- fix(threads): reply in thread view failed
- chore(cleanup): fixes formatting
- chore(cleanup): moved the main screenshot
- docs(readme): direct links for images again
- docs(readme): minor correction to links
- docs(readme): corrected image links again
- docs(readme): added missing screenshots

## [1.0.0] - 2025-09-06

- chore(release): v1.0.0
- docs(readme): fixed image links
- fix(image): Lazy loading images reverted

## [1.0.0a0] - 2025-09-06

- chore: bump to v1.0.0a0

## [0.9.0] - 2025-09-06

- chore(release): added release scripts
- refactor(UI): Streamlined the UI of the modal windows
- docs(md file): updated the project md files
- refactor(loading): load last profile on restart
- refactor(lazy load): optimized image lazy load
- fix(reply): now you reply all
- feat(logviewer): Added a logviewer for easier debugging
- feat(notifications): configurable notifications
- feat(UI): jump to top binding
- fix(UI): smoother toggling of direct message timeline
- fix(boost-like): Fixed boost-like in thread and hashtag view
- feat(edit post): added support for editing posts
- feat(direct messages): post, reply direct messages, new message notif
- feat(direct messages): Added direct message timeline
- refactor(search_screen): Better scrolling of search results
- refactor(CSS): move all css/style to the css file
- feat(functionality): added mute/block functionality
- feat(posting): post visibility added
- refactor(generel): code cleanup and minor fixes
- feat(UI): custom theme support, clickable links/hashtags in timelines
- feat(multi-profile): multi-profile support added
- fix(search): better result formatting
- feat(search): search support
- fix(issue#4): Fix for the onboarding process
- feat(images): Profile picture and dynamic rendering

## [0.7.1] - 2025-08-24

- fix(threads): fix id bug in threads view
- fix(spped): pause auto-refresh when posting
- refactor(security): fixed silent try-except-pass
- fix(mouse): fixed jump-back when mouse scrolling

## [0.7.0] - 2025-08-21

- feat(themes): added a retro green-on-black theme
- release: 0.7.0
- feat(poll): Added support for sending polls
- feat(polls): support for showing and voting on polls
- refactor(rendering): Better message rendering
- refactor(rendering): Moved to beautifulSoup for message rendering
- feat(single-timeline): Make it possible to force single-timeline mode
- refactor(UI): make single-column mode more dynamic
- Create FUNDING.yml
- docs(readme): updated readme with screenshots

## [0.6.2] - 2025-08-20

- refactor(UI): UI cleanup
- feat(UI): toggles for timelines
- docs(screenshots): added first screenshot to collection
- feat(layout): support for single-column view in narrow places
- docs(readme): fixed formatting
- docs(readme): added mastodon link

## [0.6.1] - 2025-08-20

- fix(onboarding): fixed wrong exception Untracked

## [0.6.0] - 2025-08-19

- refactor(onboarding): Switched to clipman + better layout
- feat(Caching): Added caching db for backend
- feat(mouse): The mouse is now fully functional
- Fix(Onboarding): First fetch after onboarding
- fix(ssl): Image fetching now corectly obeys --no-ssl-verify
- fix(issue#4): Added more debugging to onboarding
- fix(issue#4): better error handling for onboarding
- Update issue templates
- Chore: added "known issues" to README
- refactor(threadview): reformatted code to not hit duplicate id
- fix: duplicate ID errror when opening a thread view
- feat: added support for unlike/unfavorite
- feat: added support for unlike/unfavorite
- fix: fixed problem in auth link code

## [0.5.3] - 2025-08-14

- chore: version 0.5.3
- feat(image): Sixel and TGP image rendering
- Fix: corrected missing dependency
- Create SECURITY.md
- refactor: better error handling
- feat: added help screen to the app
- Create bandit.yml
- (docs) updated readme to reflect new features and dependencies
- version 0.5.1

## [0.5.1] - 2025-08-14

- fix log file location and only write it when requested

## [0.5.0] - 2025-08-14

- version 0.5.0
- user selectable dark and light theme
- Initial image support
- better window alignment
- Post text limit
- Auto refresh configuration
- display names
- Theme fix

## [0.4.1] - 2025-08-13

- version 0.4.1
- fixed problem with storing theme selection
- Faster startup time
- added timestamp to the post and corrected the order of notifications
- Version 0.3.4
- Debug off as default
- Profile view
- version 0.2.0
- Better thread interaction and navigation
- thread view
- SSL verification
- Threading and visual ques
- Optimized the boost and like functionality so it does not have to loop through the entire list of posts to find the right one.
- Fixed splash screen alignment
- added screenshot and updated readme a bit
- First release of the Mastui client. Still very much alpha stage

## [0.1.0] - 2025-08-11

- Initial commit
