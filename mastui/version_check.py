import json
import logging
from datetime import datetime, timedelta, timezone
from importlib import metadata
from pathlib import Path

import requests
import tomllib

log = logging.getLogger(__name__)

PYPI_URL = "https://pypi.org/pypi/mastui/json"
RELEASE_URL = "https://pypi.org/project/mastui/"
STATE_FILENAME = "update_state.json"
ONE_DAY = timedelta(hours=24)


def _parse_version(version_str: str) -> tuple:
    """Simple semantic-ish version parser."""
    parts = []
    for piece in version_str.split("."):
        if piece.isdigit():
            parts.append(int(piece))
        else:
            # Split possible alpha/beta suffixes
            num = "".join([c for c in piece if c.isdigit()])
            suffix = "".join([c for c in piece if not c.isdigit()])
            if num:
                parts.append(int(num))
            if suffix:
                parts.append(suffix)
    return tuple(parts)


def get_installed_version() -> str:
    """Return the installed version of mastui, or fall back to pyproject."""
    try:
        return metadata.version("mastui")
    except metadata.PackageNotFoundError:
        pass
    # Try reading pyproject when running from source
    try:
        root = Path(__file__).resolve().parents[1]
        data = tomllib.loads((root / "pyproject.toml").read_text())
        return data["tool"]["poetry"]["version"]
    except Exception as e:
        log.debug(f"Could not read version from pyproject: {e}")
        return "0.0.0"


def _load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text())
    except Exception as e:
        log.debug(f"Could not load update state {state_path}: {e}")
        return {}


def _save_state(state_path: Path, state: dict) -> None:
    try:
        state_path.write_text(json.dumps(state))
    except Exception as e:
        log.debug(f"Could not save update state {state_path}: {e}")


def fetch_latest_version() -> str | None:
    """Fetch the latest version string from PyPI."""
    try:
        resp = requests.get(PYPI_URL, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return data.get("info", {}).get("version")
    except Exception as e:
        log.debug(f"Failed to fetch latest version from PyPI: {e}")
        return None


def check_for_update(profile_path: Path, current_version: str, force: bool = False) -> dict:
    """Check whether a newer version is available.

    Returns dict with:
      latest_version: str | None
      is_newer: bool
      should_notify: bool
      release_url: str
      last_checked: datetime
    """
    state_path = profile_path / STATE_FILENAME
    state = _load_state(state_path)
    now = datetime.now(timezone.utc)

    last_checked_str = state.get("last_checked")
    last_checked = None
    if last_checked_str:
        try:
            last_checked = datetime.fromisoformat(last_checked_str)
        except Exception:
            last_checked = None

    latest_cached = state.get("latest_version")
    notified_version = state.get("notified_version")
    last_notified_str = state.get("last_notified")
    last_notified = None
    if last_notified_str:
        try:
            last_notified = datetime.fromisoformat(last_notified_str)
        except Exception:
            last_notified = None

    def should_notify_for(latest_version: str) -> bool:
        if not latest_version:
            return False
        newer = _parse_version(latest_version) > _parse_version(current_version)
        if not newer:
            return False
        if notified_version != latest_version:
            return True
        if last_notified and now - last_notified > ONE_DAY:
            return True  # Remind daily if still on an older build
        return False

    if not force and last_checked and now - last_checked < ONE_DAY and latest_cached:
        is_newer = _parse_version(latest_cached) > _parse_version(current_version)
        should_notify = should_notify_for(latest_cached)
        return {
            "latest_version": latest_cached,
            "is_newer": is_newer,
            "should_notify": should_notify,
            "release_url": RELEASE_URL,
            "last_checked": last_checked,
        }

    latest = fetch_latest_version()
    if not latest:
        return {
            "latest_version": latest_cached,
            "is_newer": False,
            "should_notify": False,
            "release_url": RELEASE_URL,
            "last_checked": now,
        }

    is_newer = _parse_version(latest) > _parse_version(current_version)
    should_notify = should_notify_for(latest)

    state.update(
        {
            "last_checked": now.isoformat(),
            "latest_version": latest,
            "notified_version": latest if should_notify else notified_version,
            "last_notified": now.isoformat() if should_notify else last_notified_str,
        }
    )
    _save_state(state_path, state)

    return {
        "latest_version": latest,
        "is_newer": is_newer,
        "should_notify": should_notify,
        "release_url": RELEASE_URL,
        "last_checked": now,
    }
