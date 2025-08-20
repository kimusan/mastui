# Mastui - A Modern Mastodon TUI Client

Mastui is a powerful, fast, and feature-rich Mastodon client for your terminal. Built with Python and the modern [Textual](https://textual.textualize.io/) framework, it provides a highly efficient, multi-column layout that lets you keep an eye on all the action at once. Whether you're a power user who wants to manage multiple timelines or someone who just loves the terminal, Mastui is designed to be your new favorite way to interact with Mastodon.

:eight_pointed_black_star: :eight_pointed_black_star: [Follow Mastui on Mastodon](https://mastodon.social/@mastui) :eight_pointed_black_star: :eight_pointed_black_star:

## Features

* **Multi-Column Layout:** View your Home, Notifications, and Federated timelines all at once.
* **Timeline Caching:** A persistent SQLite cache makes loading posts fast and resilient to network issues.
* **Compose and Reply:** A full-featured compose window for new posts and replies, with a character counter, content warnings, and language selection.
* **"Infinite" Scrolling:** Scroll down to load older posts from your cache or the server.
* **Interactive Posts:** Like, boost, and reply to posts with keyboard shortcuts.
* **View Profiles and Threads:** Dive deeper into conversations by viewing post threads and user profiles.
* **Image Support:** View images directly in your terminal with multiple renderers (Auto, ANSI, Sixel, TGP), with a persistent image cache.
* **Highly Configurable:**
  * Toggle the visibility of each timeline.
  * Configure auto-refresh intervals for each timeline.
  * Choose between light and dark mode themes.
* **And much more...** including content warning support, SSL verification options, and a detailed help screen.

## Screenshots

Here's a glimpse of what Mastui looks like in action.

**Single-Column View**
*The default three-column layout is showing the Home, Notifications, and Federated timelines (see top of this site). In narrow spaces it looks like this*
![Multi-Column View](assets/screenshots/mastui-single-column-view.png)

**Profile View**
*Viewing a user's profile, with their bio, stats, and links.*
![Profile View](assets/screenshots/mastui-profile-view.png)

**Image Support**
*Images can be displayed directly in the timeline.*
![Image Support](assets/screenshots/mastui-image-support.png)

**Light Theme**
*Mastui supports both light and dark themes, which can be configured in the options.*
![Light Theme](assets/screenshots/mastui-light-theme.png)

**Options Window**
*The options window, where you can configure everything from timeline visibility to image rendering.*
![Options Window](assets/screenshots/mastui-options-window.png)

## Installation

The recommended way to install Mastui is with `pipx`.

1. **Install pipx** (if you don't have it already):

    ```bash
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    ```

2. **Install mastui using pipx**:

    ```bash
    pipx install mastui
    ```

After this, you can run the application from anywhere by simply typing `mastui`.

## Upgrading

To upgrade to the latest version of Mastui, run the following command:

```bash
pipx upgrade mastui
```

## Technology Stack

* [Python](https://www.python.org/)
* [Poetry](https://python-poetry.org/) for dependency management
* [Textual](https://textual.textualize.io/) for the TUI framework
* [textual-image](https://pypi.org/project/textual-image/) for image rendering
* [Mastodon.py](https://mastodonpy.readthedocs.io/) for interacting with the Mastodon API
* [httpx](https://www.python-httpx.org/) for HTTP requests
* [html2text](https://github.com/Alir3z4/html2text) for converting HTML to Markdown
* [python-dateutil](https://dateutil.readthedocs.io/) for parsing datetimes

## Known issues

* Sixel images seems to be generated correctly but not displayed correctly in some terminals (even ones with Sixel support)

## License

Mastui is licensed under the MIT license. See LICENSE for more information.

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use SemVer for versioning. For the versions available, see the tags on this repository.

## Authors

* **Kim Schulz** - *Initial work* - [kimusan](https://github.com/kimusan)

See also the list of contributors who participated in this project.

## Acknowledgments

* Inspiration and guidance from the Textual community and the Poetry team
* The Mastodon community for their contributions to the development of the application and its features
* Other projects that have inspired or influenced the design of Mastui

Please feel free to reach out to me if you have any questions, comments, or concerns.

