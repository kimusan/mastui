# Mastui - A Mastodon TUI Client Built with Python

![A screenshot](https://raw.githubusercontent.com/kimusan/mastui/main/mastui.png)

Mastui is a Mastodon TUI client built with Python and Textual. It allows users to interact with their Mastodon instance in a terminal environment, providing a more efficient and intuitive way of managing their Mastodon experience. The UI is multi-column to get an easy overview of activities.

## Features

* Timeline Viewing in a multi-column layout
* Post and Reply creation
* "Infinite" scrolling of timelines
* Like posts
* View user profiles
* Follow/Unfollow users
* View post threads
* Support for local Mastodon servers
* Light/Dark mode theming
* Content warning support

### TODO

* database backend
* Bookmarking
* Hashtag Searching
* Unliking posts
* Direct Messaging

## Installation

The recommended way to install Mastui is with `pipx`.

1.  **Install pipx** (if you don't have it already):
    ```bash
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    ```

2.  **Install mastui using pipx**:
    ```bash
    pipx install mastui
    ```

After this, you can run the application from anywhere by simply typing `mastui`.

## Technology Stack

* [Python](https://www.python.org/)
* [Poetry](https://python-poetry.org/) for dependency management
* [Textual](https://textual.textualize.io/) for the TUI framework
* [Mastodon.py](https://mastodonpy.readthedocs.io/) for interacting with the Mastodon API
* [html2text](https://github.com/Alir3z4/html2text) for converting HTML to Markdown

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
