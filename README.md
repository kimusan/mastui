# Mastui - A Fast and Modern Mastodon Client for the Terminal

<p align="center">
  
  <img src="https://raw.githubusercontent.com/kimusan/mastui/refs/heads/main/assets/mastui-logo.png" alt="Mastui Logo" width="400"/>
</p>

<p align="center">
  <strong>A powerful, feature-rich, and beautiful Mastodon TUI client.</strong>
  <br />
  <a href="https://mastui.app"><strong>Explore the Homepage »</strong></a>
  <br />
  <br />
  <a href="https://mastodon.social/@mastui">Follow Mastui on Mastodon for Updates</a>
</p>

---

**Mastui** is a modern Mastodon client for your terminal. Built with Python and the powerful [Textual](https://textual.textualize.io/) framework, it provides a highly efficient, multi-column layout that lets you keep an eye on all the action at once.

Whether you're a power user who wants to manage multiple accounts or someone who just loves the terminal, Mastui is designed to be your new favorite way to interact with Mastodon.

![Main Mastui View](https://raw.githubusercontent.com/kimusan/mastui/refs/heads/main/assets/screenshots/mastui-main-view.png)

## 🧰 Requirements

- Python **3.9+**
- A terminal with UTF-8 support and 120+ columns recommended
- Optional: Sixel/TGP-capable terminal for high fidelity image rendering
- Mastodon access token (the onboarding flow can create one for you)
- `pipx` or `pip` for installation

### Supported Operating Systems

- **Linux**
- **macOS**
- **Windows** (PowerShell/WSL)
- **Android** (via Termux)

If you encounter any platform-specific issues, please [open an issue](https://github.com/kimusan/mastui/issues).

## ✨ Key Features

- **Multi-Column Layout:** Home, Local, Federated, Mentions, and DM timelines can be shown side-by-side. Layout automatically collapses for narrow terminals.
- **Multi-Profile & Sandboxed Config:** Every account has its own config directory, keymap, credentials, cache, and custom theme overrides.
- **Timeline Power Features**
  - Like, boost, reply, edit, and view threads directly from the keyboard
  - Jump to the top (`g`), refresh (`r`), or move between columns with configurable bindings
  - Persistent SQLite cache enables offline reading and super fast scrolling
- **Rich Composer**
  - Content warnings, poll builder, visibility controls, and language selector
  - Autocomplete for `@mentions` and `#hashtags` sourced from your follows and the local instance
  - Inline preview of original post when replying
- **Media Friendly**
  - Inline image previews with ANSI, Sixel, or TGP renderers (auto-detect)
  - Polls rendered with vote counts or interactive voting UI
  - URL extractor modal lets you copy media/card links without leaving the TUI
- **Personalization**
  - Quick theme switches plus custom CSS overrides
  - Keybinding editor with per-profile `keymap.json`
  - Options modal to toggle timelines, enable image caching, configure auto-refresh cadence, and curate the language list used in the composer
- **Productivity niceties**
  - Search panel for people, tags, and posts
  - Hashtag timeline modal
  - Profile and conversation screens with follow/mute/block actions
  - Log viewer (`F12`) when running with `--debug`

## 🖼️ Screenshots

| **Thread View** | **Profile View** |
| :---: | :---: |
| ![Thread View](https://raw.githubusercontent.com/kimusan/mastui/refs/heads/main/assets/screenshots/mastui-thread-view.png) | ![Profile View](https://raw.githubusercontent.com/kimusan/mastui/refs/heads/main/assets/screenshots/mastui-profile-view.png) |
| **Compose Window with Poll** | **Options Screen** |
| ![Compose poll](https://raw.githubusercontent.com/kimusan/mastui/refs/heads/main/assets/screenshots/mastui-compose-poll.png) | ![Options Window](https://raw.githubusercontent.com/kimusan/mastui/refs/heads/main/assets/screenshots/mastui-options-window.png) |
| **Retro Green Theme** | **Light Theme** |
| ![Retro Theme](https://raw.githubusercontent.com/kimusan/mastui/refs/heads/main/assets/screenshots/mastui-retro-green-on-black-theme.png) | ![Light Theme](https://raw.githubusercontent.com/kimusan/mastui/refs/heads/main/assets/screenshots/mastui-light-theme.png) |

## 🚀 Installation

### pipx (recommended)

```bash
pipx install mastui
# later upgrades
pipx upgrade mastui
```

### pip / virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install mastui
```

### From Source

```bash
git clone https://github.com/kimusan/mastui.git
cd mastui
pip install poetry
poetry install
poetry run mastui --debug
```

Mastui stores profile data under `~/.config/mastui/<profile>` (or the platform equivalent). Remove those directories to wipe a profile, or use the built-in profile manager.

## ⌨️ Key Bindings

This is a summary of the most common key bindings. For a full list, press `?` inside the app.

| Key(s) | Action |
| --- | --- |
| `q` | Quit the application |
| `d` | Toggle dark/light mode |
| `u` | Switch user profile |
| `o` | Open options screen |
| `/` | Open search screen |
| `?` | Show the full help screen |
| `up`/`down` | Move selection up/down |
| `left`/`right` | Focus timeline to the left/right |
| `g` | Jump to the top of the focused timeline |
| `r` | Refresh all timelines |
| `c` | Compose a new post |
| `a` | Reply to the selected post |
| `l` | Like / Unlike the selected post |
| `b` | Boost / Reblog the selected post |
| `e` | Edit one of your own posts |
| `p` | View the author's profile |
| `enter` | View the post's thread |

## 🗺️ Roadmap

Mastui is actively developed. Here are some of the features planned for future releases:

* **Bookmarks:** Bookmark posts and view them in a dedicated timeline.
* **Content Filtering:** Support for Mastodon's server-side content and keyword filters.
* **User Lists:** View and interact with your created user lists as timelines.
* **Post Management:** Delete your own posts.
* **Profile Management:** Re-authenticate or delete profiles from within the app.
* **Post Drafts:** Save and load drafts of your posts.
* **Localization:** Support for multiple languages in the UI.

Have an idea? Feel free to [open an issue](https://github.com/kimusan/mastui/issues) to discuss it.

## 🤝 Contributing

Contributions are welcome! Please read `CONTRIBUTING.md` for details on our code of conduct and the process for submitting pull requests.

## 🛠️ Technology Stack

Mastui is built with some fantastic open-source libraries:

* [Textual](https://textual.textualize.io/) for the TUI framework
* [Python](https://www.python.org/)
* [Mastodon.py](https://mastodonpy.readthedocs.io/) for interacting with the Mastodon API
* [textual-image](https://pypi.org/project/textual-image/) for image rendering
* [httpx](https://www.python-httpx.org/) for HTTP requests
* [html2text](https://github.com/Alir3z4/html2text) for converting HTML to Markdown
* [python-dateutil](https://dateutil.readthedocs.io/) for parsing datetimes

## ✍️ Authors

* **Kim Schulz** - *Initial work* - [kimusan](https://github.com/kimusan)

See also the list of contributors who participated in this project.

## 📜 License

Mastui is licensed under the MIT License. See the `LICENSE` file for more information.
