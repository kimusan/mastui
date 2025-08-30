# Contributing to Mastui

First off, thank you for considering contributing to Mastui! It's people like you that make open source such a great community.

## Code of Conduct

This project and everyone participating in it is governed by the [Mastui Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior.

## How Can I Contribute?

There are many ways to contribute, from writing code and documentation to reporting bugs and submitting feature requests.

### Reporting Bugs

If you find a bug, please open an issue and provide the following information:

- A clear and descriptive title.
- A detailed description of the problem, including steps to reproduce it.
- The version of Mastui you are using.
- Your operating system and terminal emulator.
- If possible, include the relevant section of your log file (`~/.config/mastui/mastui.log`) by running the app with the `--debug` flag.

### Suggesting Enhancements

If you have an idea for a new feature or an improvement to an existing one, please open an issue to start a discussion. This allows us to coordinate our efforts and avoid duplicated work.

### Pull Requests

We love pull requests! If you're ready to contribute code, here's how to get started.

#### Development Setup

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:

    ```bash
    git clone https://github.com/your-username/mastui.git
    cd mastui
    ```

3. **Install dependencies** using Poetry:

    ```bash
    poetry install
    ```

4. **Run the application** in development mode:

    ```bash
    poetry run mastui
    ```

    To run with debug logging enabled, which is highly recommended for development:

    ```bash
    poetry run mastui --debug
    ```

#### Making Changes

1. Create a new branch for your feature or bug fix:

    ```bash
    git checkout -b feature/your-great-feature
    ```

2. Make your changes.
3. Ensure your code follows the project's style. We use `ruff` for linting and formatting.

    ```bash
    # To check for linting errors
    poetry run ruff check .

    # To automatically format your code
    poetry run ruff format .
    ```

4. Commit your changes with a clear and descriptive commit message.
5. Push your branch to your fork on GitHub.
6. Open a pull request to the `main` branch of the original Mastui repository.

Thank you for your contribution!

