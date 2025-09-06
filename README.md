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

## 💻 Cross-Platform Support

Mastui is built on the cross-platform Textual framework and is tested and expected to work on:

* **Linux**
* **macOS**
* **Microsoft Windows**
* **Android (via Termux)**

If you encounter any platform-specific issues, please [open an issue](https://github.com/kimusan/mastui/issues).

## ✨ Features

Mastui is packed with features to make your Mastodon experience seamless and efficient:

* **Multi-Column Layout:** View your Home, Notifications, Federated, and Direct Message timelines simultaneously. The layout automatically switches to a single-column view on narrow terminals.
* **Multi-Profile Support:** Securely log into multiple accounts and switch between them instantly with the `u` key. Each profile has its own configuration, cache, and theme settings.
* **Interactive Timelines:**
  * Like (`l`), Boost (`b`), and Reply (`a`) to posts directly.
  * Jump to the top of a timeline with `g`.
  * Scroll infinitely to load older posts from your cache or the server.
  * Scroll position is preserved during automatic refreshes, so you never lose your place.
* **Rich Content Support:**
  * **Image Previews:** View images directly in your terminal with lazy loading for a smooth experience. Multiple renderers are supported (ANSI, Sixel, TGP).
  * **Polls:** View and vote on polls.
  * **Markdown & Links:** Posts are rendered beautifully with clickable links.
* **Full-Featured Composer:**
  * Write new posts (`c`) and replies (`a`) in a full-screen composer.
  * Add Content Warnings (CWs) and select post language.
  * Create and manage polls directly.
* **Deeper Navigation:**
  * View full post threads (`Enter`).
  * View user profiles (`p`), including their bio, stats, and links.
  * Follow, Mute, and Block users directly from their profile.
* **Smart Notifications:**
  * Get detailed pop-up notifications for new Direct Messages (e.g., "New DM from @user").
  * Optionally enable pop-ups for mentions, follows, boosts, and favourites.
* **Highly Configurable:**
  * Toggle the visibility of each timeline.
  * Configure auto-refresh intervals for each timeline.
  * Choose from multiple built-in themes or create your own.
* **Advanced:**
  * Hidden log viewer (`F12`) for debugging when running with `--debug`.
  * Persistent SQLite cache for fast startup and offline reading.

## 🖼️ Screenshots

| **Thread View** | **Profile View** |
| :---: | :---: |
| ![Thread View](https://raw.githubusercontent.com/kimusan/mastui/refs/heads/main/assets/screenshots/mastui-thread-view.png) | ![Profile View](https://raw.githubusercontent.com/kimusan/mastui/refs/heads/main/assets/screenshots/mastui-profile-view.png) |
| **Compose Window with Poll** | **Options Screen** |
| ![Compose poll](https://raw.githubusercontent.com/kimusan/mastui/refs/heads/main/assets/screenshots/mastui-compose-poll.png) | ![Options Window](https://raw.githubusercontent.com/kimusan/mastui/refs/heads/main/assets/screenshots/mastui-options-window.png) |
| **Retro Green Theme** | **Light Theme** |
| ![Retro Theme](https://raw.githubusercontent.com/kimusan/mastui/refs/heads/main/assets/screenshots/mastui-retro-green-on-black-theme.png) | ![Light Theme](https://raw.githubusercontent.com/kimusan/mastui/refs/heads/main/assets/screenshots/mastui-light-theme.png) |

## 🚀 Installation

The recommended way to install Mastui is with `pipx`, which installs it in an isolated environment.

1. **Install pipx** (if you don't have it already):

    ```bash
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    ```

2. **Install Mastui using pipx**:

    ```bash
    pipx install mastui
    ```

After installation, you can run the application from anywhere by simply typing `mastui`.

### Upgrading

To upgrade to the latest version of Mastui, run:

```bash
pipx upgrade mastui
```

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

* [Python](https://www.python.org/)
* [Textual](https://textual.textualize.io/) for the TUI framework
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
