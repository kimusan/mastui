"""Onboarding and login modal for logging into Mastodon instances and creating profiles."""

from __future__ import annotations

import logging
import re
import urllib.parse
import webbrowser
from dataclasses import dataclass
from typing import Any, Callable

from espresso.beans.modal_stack import ModalCloseMsg
from espresso.beans.spinner import DOTS, Spinner
from espresso.beans.textinput import TextInput
from espresso.core.keys import KeyMsg
from espresso.core.mouse import MouseAction, MouseButton, MouseMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi
from mastui.espresso_clipboard import copy_to_clipboard

try:
    from mastui.mastodon_api import create_app, login
except Exception:
    import sys
    from pathlib import Path
    poetry_dir = Path.home() / ".cache" / "pypoetry" / "virtualenvs"
    if poetry_dir.exists():
        for sp in sorted(poetry_dir.glob("mastui-*/lib/python*/site-packages"), reverse=True):
            if sp.is_dir() and str(sp) not in sys.path:
                sys.path.append(str(sp))
    try:
        from mastui.mastodon_api import create_app, login
    except Exception:
        create_app = None
        login = None

log = logging.getLogger(__name__)


@dataclass
class AuthLinkGeneratedMsg(Msg):
    """Dispatched when create_app finishes generating the authorization URL."""
    auth_url: str | None
    client_id: str | None
    client_secret: str | None
    error: str | None


@dataclass
class LoginCompletedMsg(Msg):
    """Dispatched when login() finishes exchanging the auth code for access token."""
    api: Any
    env_content: str | None
    profile_name: str | None
    error: str | None


@dataclass
class LoginSuccessMsg(Msg):
    """Dispatched when a new profile has been successfully logged in and saved."""
    profile_name: str
    env_content: str
    api: Any


def clean_host_input(host_input: str) -> str:
    """Normalize user input domain into a clean hostname."""
    if not host_input:
        return ""
    text = host_input.strip()
    if not text:
        return ""
    if "://" not in text:
        text = f"https://{text}"
    parsed = urllib.parse.urlparse(text)
    hostname = parsed.hostname or ""
    if not hostname or any(c.isspace() for c in hostname):
        return ""
    if parsed.port:
        return f"{hostname}:{parsed.port}"
    return hostname


def clean_auth_code_input(code_input: str) -> str:
    """Extract clean auth code or access token from input or callback URL."""
    val = (code_input or "").strip().strip("'\"")
    if not val:
        return ""
    if "code=" in val:
        try:
            parsed = urllib.parse.urlparse(val)
            qs = urllib.parse.parse_qs(parsed.query)
            if "code" in qs:
                return qs["code"][0].strip().strip("'\"")
            # Fallback split
            after = val.split("code=", 1)[1]
            return after.split("&")[0].split("#")[0].split()[0].strip().strip("'\"")
        except Exception:
            pass
    if val.startswith("Bearer "):
        val = val[7:].strip()
    return val


class LoginModal(Model):
    """Interactive onboarding and login screen for connecting a Mastodon account."""

    # Stages
    STAGE_HOST = "host"
    STAGE_CREATING_APP = "creating_app"
    STAGE_CODE = "code"
    STAGE_LOGGING_IN = "logging_in"
    STAGE_SUCCESS = "success"

    def __init__(
        self,
        default_host: str = "mastodon.social",
        width: int = 74,
        height: int = 22,
        theme: Any = None,
        create_app_fn: Callable[..., Any] = create_app,
        login_fn: Callable[..., Any] = login,
        ssl_verify: bool = True,
    ) -> None:
        self.width = max(56, width)
        self.height = max(16, height)
        self.theme = theme
        self.create_app_fn = create_app_fn
        self.login_fn = login_fn
        self.ssl_verify = ssl_verify

        self.stage = self.STAGE_HOST
        self.host_input = TextInput(placeholder="mastodon.social", value=default_host or "")
        self.host_input.focus()

        self.code_input = TextInput(placeholder="Paste authorization code here", value="", char_limit=1024)
        self.spinner = Spinner(DOTS, fps=12.0)
        self.spinner_text = "Connecting to instance..."

        self.cleaned_host: str = ""
        self.auth_url: str = ""
        self.client_id: str = ""
        self.client_secret: str = ""
        self.error_message: str = ""
        self.status_message: str = ""
        self.created_profile_name: str = ""
        self.created_env_content: str = ""
        self.created_api: Any = None

    def init(self) -> Cmd | None:
        return self.host_input.init()

    def _start_create_app(self) -> Cmd:
        host = self.cleaned_host
        verify = self.ssl_verify
        fn = self.create_app_fn

        if not fn:
            def _err_task() -> Msg:
                return AuthLinkGeneratedMsg(None, None, None, "Mastodon API library is not installed in current environment.")
            return _err_task

        def _task() -> Msg:
            try:
                res = fn(host, verify)
                auth_url, c_id, c_secret, err = res
                return AuthLinkGeneratedMsg(auth_url, c_id, c_secret, err)
            except Exception as exc:
                return AuthLinkGeneratedMsg(None, None, None, str(exc))

        return _task

    def _start_login(self) -> Cmd:
        host = self.cleaned_host
        c_id = self.client_id
        c_sec = self.client_secret
        code = clean_auth_code_input(self.code_input.value)
        verify = self.ssl_verify
        fn = self.login_fn

        if not fn:
            def _err_task() -> Msg:
                return LoginCompletedMsg(None, None, None, "Mastodon API library is not installed in current environment.")
            return _err_task

        def _task() -> Msg:
            try:
                api, env_content, err = fn(host, c_id, c_sec, code, verify)
                if err or not api:
                    return LoginCompletedMsg(None, None, None, err or "Invalid authorization code")
                
                # Retrieve current authenticated user handle
                profile_name = f"user@{host}"
                try:
                    me = api.me()
                    raw_uname = me.get("username", "")
                    clean_uname = "".join(c for c in raw_uname if c.isalnum() or c in "-_")
                    profile_name = f"{clean_uname}@{host}"
                except Exception:
                    pass

                return LoginCompletedMsg(api, env_content, profile_name, None)
            except Exception as exc:
                return LoginCompletedMsg(None, None, None, str(exc))

        return _task

    def update(self, msg: Msg) -> tuple[LoginModal, Cmd | None]:
        if isinstance(msg, AuthLinkGeneratedMsg):
            if msg.error:
                self.stage = self.STAGE_HOST
                self.error_message = msg.error
                self.host_input.focus()
                return self, None
            self.auth_url = msg.auth_url or ""
            self.client_id = msg.client_id or ""
            self.client_secret = msg.client_secret or ""
            self.stage = self.STAGE_CODE
            self.code_input.focus()
            self.error_message = ""
            
            # Copy to clipboard
            if self.auth_url:
                copied = copy_to_clipboard(self.auth_url)
                if copied:
                    self.status_message = "✓ Authorization link copied to your clipboard!"
                else:
                    self.status_message = "Open authorization link in browser (press [Ctrl+O])"
            return self, None

        if isinstance(msg, LoginCompletedMsg):
            if msg.error:
                self.stage = self.STAGE_CODE
                self.error_message = msg.error
                self.code_input.focus()
                return self, None
            
            self.stage = self.STAGE_SUCCESS
            self.created_profile_name = msg.profile_name or f"user@{self.cleaned_host}"
            self.created_env_content = msg.env_content or ""
            self.created_api = msg.api
            self.error_message = ""

            # Return success message to parent app
            p_name = self.created_profile_name
            env_c = self.created_env_content
            api_obj = self.created_api
            def _success() -> Msg:
                return LoginSuccessMsg(p_name, env_c, api_obj)
            return self, _success

        # Spinner update during loading stages
        if self.stage in (self.STAGE_CREATING_APP, self.STAGE_LOGGING_IN):
            self.spinner, s_cmd = self.spinner.update(msg)

        if isinstance(msg, KeyMsg):
            match msg.key:
                case "esc":
                    def _close() -> Msg:
                        return ModalCloseMsg()
                    return self, _close

                case "enter":
                    if self.stage == self.STAGE_HOST:
                        raw_h = self.host_input.value.strip() or self.host_input.placeholder
                        clean = clean_host_input(raw_h)
                        if not clean:
                            self.error_message = "Please enter a valid instance domain (e.g. mastodon.social)"
                            return self, None
                        self.cleaned_host = clean
                        self.stage = self.STAGE_CREATING_APP
                        self.error_message = ""
                        self.spinner_text = f"Connecting to {clean}..."
                        return self, self._start_create_app()

                    elif self.stage == self.STAGE_CODE:
                        code = clean_auth_code_input(self.code_input.value)
                        if not code:
                            self.error_message = "Please enter the authorization code."
                            return self, None
                        self.stage = self.STAGE_LOGGING_IN
                        self.error_message = ""
                        self.spinner_text = "Exchanging code and verifying login..."
                        return self, self._start_login()

                    elif self.stage == self.STAGE_SUCCESS:
                        def _dismiss() -> Msg:
                            return ModalCloseMsg()
                        return self, _dismiss

                case "ctrl+o" | "alt+o":
                    # Open authorization URL in web browser if on code stage
                    if self.stage == self.STAGE_CODE and self.auth_url:
                        try:
                            webbrowser.open(self.auth_url)
                            self.status_message = "✓ Opened authorization page in web browser!"
                        except Exception:
                            self.status_message = "Failed to launch web browser."
                        return self, None

                case "ctrl+y" | "alt+c":
                    # Copy authorization URL to clipboard
                    if self.stage == self.STAGE_CODE and self.auth_url:
                        copied = copy_to_clipboard(self.auth_url)
                        if copied:
                            self.status_message = "✓ Copied authorization URL to clipboard!"
                        else:
                            self.status_message = "Could not copy URL to clipboard."
                        return self, None

                case "ctrl+b" | "alt+b":
                    # Back to host input stage to try another instance or get new credentials
                    if self.stage == self.STAGE_CODE:
                        self.stage = self.STAGE_HOST
                        self.error_message = ""
                        self.host_input.focus()
                        return self, None

        # Pass input messages to active text input
        if self.stage == self.STAGE_HOST:
            self.host_input, cmd = self.host_input.update(msg)
            return self, cmd
        elif self.stage == self.STAGE_CODE:
            self.code_input, cmd = self.code_input.update(msg)
            return self, cmd

        return self, None

    def view(self) -> str:
        inner_w = max(50, self.width - 4)

        header = Style().bold(True).foreground("#00E5FF").render("🔑 MASTUI ONBOARDING & LOGIN")
        sep = Style().foreground("#333355").render("─" * inner_w)
        lines: list[str] = [header, sep, ""]

        if self.stage == self.STAGE_HOST:
            lines.append(Style().bold(True).foreground("#FAFAFA").render("Welcome to Mastui!"))
            lines.append(Style().foreground("#AAAABB").render("Log into your Mastodon account to view timelines, boost, and toot."))
            lines.append("")
            lines.append(Style().bold(True).foreground("#7D56F4").render("Mastodon Instance Domain:"))
            
            box = Style().border(ROUNDED_BORDER).border_foreground("#7D56F4").width(min(45, inner_w - 4))
            lines.append(box.render(self.host_input.view()))

            if self.error_message:
                lines.append("")
                lines.append(Style().bold(True).foreground("#FF5252").render(f"⚠ {self.error_message}"))

            lines.append("")
            hint = Style().foreground("#666688").render("[Enter] Get Authorization Link    [Esc] Cancel / Demo Mode")
            lines.append(hint)

        elif self.stage == self.STAGE_CREATING_APP:
            lines.append(Style().bold(True).foreground("#FAFAFA").render(f"Connecting to https://{self.cleaned_host}..."))
            lines.append("")
            lines.append(self.spinner.view())
            lines.append("")
            lines.append(Style().foreground("#666688").render("Creating OAuth application and generating auth link..."))

        elif self.stage == self.STAGE_CODE:
            lines.append(Style().bold(True).foreground("#00E676").render("Step 1: Authorize Application"))
            if self.status_message:
                lines.append(Style().foreground("#00E5FF").render(self.status_message))
            lines.append(Style().foreground("#AAAABB").render("Open this authorization URL in your browser:"))
            
            url_display = truncate_ansi(self.auth_url, inner_w - 6)
            lines.append(Style().italic(True).foreground("#7D56F4").render(f"  {url_display}"))
            lines.append("")

            lines.append(Style().bold(True).foreground("#00E676").render("Step 2: Enter Authorization Code or Access Token"))
            lines.append(Style().foreground("#AAAABB").render("Copy the code from your browser (or paste a personal access token):"))
            
            box = Style().border(ROUNDED_BORDER).border_foreground("#00E5FF").width(min(54, inner_w - 4))
            lines.append(box.render(self.code_input.view()))

            if self.error_message:
                lines.append("")
                lines.append(Style().bold(True).foreground("#FF5252").render(f"⚠ {self.error_message}"))

            lines.append("")
            hint = Style().foreground("#666688").render("[Enter] Complete Login   [Ctrl+O] Open Browser   [Alt+C] Copy Link   [Alt+B] Back   [Esc] Cancel")
            lines.append(hint)

        elif self.stage == self.STAGE_LOGGING_IN:
            lines.append(Style().bold(True).foreground("#FAFAFA").render("Authenticating..."))
            lines.append("")
            lines.append(self.spinner.view())
            lines.append("")
            lines.append(Style().foreground("#666688").render("Exchanging token and fetching account profile..."))

        elif self.stage == self.STAGE_SUCCESS:
            lines.append(Style().bold(True).foreground("#00E676").render("🎉 LOGIN SUCCESSFUL!"))
            lines.append("")
            lines.append(Style().foreground("#FAFAFA").render(f"Connected to account: @{self.created_profile_name}"))
            lines.append(Style().foreground("#AAAABB").render("Profile configuration and credentials saved."))
            lines.append("")
            lines.append(Style().foreground("#666688").render("Press [Enter] or [Esc] to continue to your timelines."))

        content = "\n".join(lines)
        return (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#00E5FF")
            .width(inner_w)
            .padding(1, 2)
            .render(content)
        )
