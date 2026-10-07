#!/usr/bin/env python3
"""Launcher for the Espresso-powered Mastui client.

Usage:
    ./scripts/espresso_mastui.py                   # Launch with cached profile data
    ./scripts/espresso_mastui.py --profile <name>  # Launch with specific profile
    ./scripts/espresso_mastui.py --demo            # Launch with mock demo posts
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
MASTUI_DIR = REPO_ROOT
ESPRESSO_SRC = REPO_ROOT.parent / "espresso" / "src"

for p in (MASTUI_DIR, ESPRESSO_SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Auto-detect poetry virtualenv site-packages if running with system python
try:
    import mastodon
except ImportError:
    poetry_dir = Path.home() / ".cache" / "pypoetry" / "virtualenvs"
    if poetry_dir.exists():
        for sp in sorted(poetry_dir.glob("mastui-*/lib/python*/site-packages"), reverse=True):
            if sp.is_dir() and str(sp) not in sys.path:
                sys.path.insert(0, str(sp))

from espresso import Program
from mastui.espresso_app import MastuiEspressoApp


def parse_simple_env(env_path: Path) -> dict[str, str]:
    """Parse key=value pairs from a .env file without external dependencies."""
    vals: dict[str, str] = {}
    if not env_path.exists():
        return vals
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip().strip("'\"")
    except Exception:
        pass
    return vals


def resolve_profile_dir(requested_profile: str | None = None) -> tuple[str, Path | None]:
    """Find the target profile name and its directory."""
    config_dir = Path.home() / ".config" / "mastui"
    profiles_dir = config_dir / "profiles"

    if requested_profile:
        target_dir = profiles_dir / requested_profile
        if target_dir.exists():
            return requested_profile, target_dir

    # Check last_profile.txt
    last_profile_file = config_dir / "last_profile.txt"
    if last_profile_file.exists():
        try:
            name = last_profile_file.read_text(encoding="utf-8").strip()
            if name:
                target_dir = profiles_dir / name
                if target_dir.exists():
                    return name, target_dir
        except Exception:
            pass

    # Check if 'default' exists
    if (profiles_dir / "default").exists():
        return "default", profiles_dir / "default"

    # Fallback to any directory in profiles/
    if profiles_dir.exists():
        dirs = [d for d in profiles_dir.iterdir() if d.is_dir()]
        if dirs:
            return dirs[0].name, dirs[0]

    return "default", None


def read_cached_posts_safe(
    db_path: Path, timeline_id: str, limit: int = 50, max_id: str | None = None
) -> list[dict]:
    """Safely query cached timeline posts from SQLite in read-only mode."""
    if not db_path.exists():
        return []
    try:
        uri = f"file:{db_path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if max_id:
            cursor.execute(
                "SELECT data FROM posts WHERE timeline_id = ? AND id < ? ORDER BY created_at DESC, id DESC LIMIT ?",
                (timeline_id, max_id, limit),
            )
        else:
            cursor.execute(
                "SELECT data FROM posts WHERE timeline_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
                (timeline_id, limit),
            )
        rows = cursor.fetchall()
        posts = [json.loads(row["data"]) for row in rows]
        conn.close()
        return posts
    except Exception:
        return []


def read_cached_conversations_safe(db_path: Path, limit: int = 50) -> list[dict]:
    """Safely query cached conversations from SQLite in read-only mode."""
    if not db_path.exists():
        return []
    try:
        uri = f"file:{db_path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM conversations LIMIT ?", (limit,))
        rows = cursor.fetchall()
        convs = [json.loads(row["data"]) for row in rows]
        conn.close()
        return convs
    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser(description="Mastui on Espresso TUI")
    parser.add_argument("--demo", action="store_true", help="Launch with built-in interactive demo posts")
    parser.add_argument("--profile", default=None, help="Name of Mastui profile to load")
    parser.add_argument("--login", action="store_true", help="Launch directly into the account login / onboarding screen")
    parser.add_argument("--limit", type=int, default=50, help="Max posts to load per timeline from cache")
    args = parser.parse_args()

    timeline_posts: dict[str, list[dict]] = {}
    username = "kim@mastui.app"
    instance = "social.data.coop"
    profile_dir: Path | None = None
    profile_name: str | None = None
    db_file: Path | None = None
    api = None

    if not args.demo:
        profile_name, profile_dir = resolve_profile_dir(args.profile)
        if profile_dir:
            env_file = profile_dir / ".env"
            env_vals = parse_simple_env(env_file)
            instance = env_vals.get("MASTODON_HOST") or instance

            if "@" in profile_name:
                username = profile_name
            else:
                username = f"user@{instance}"

            db_file = profile_dir / "cache.db"
            if db_file.exists():
                timeline_posts["home"] = read_cached_posts_safe(db_file, "home", limit=args.limit)
                timeline_posts["local"] = read_cached_posts_safe(db_file, "local", limit=args.limit)
                timeline_posts["federated"] = read_cached_posts_safe(db_file, "federated", limit=args.limit)
                timeline_posts["notifications"] = read_cached_posts_safe(db_file, "notifications", limit=args.limit)
                timeline_posts["conversations"] = read_cached_conversations_safe(db_file, limit=args.limit)

            # Attempt live Mastodon API initialization
            try:
                from mastui.config import Config
                from mastui.mastodon_api import get_api
                conf = Config(profile_dir)
                api = get_api(conf)
            except Exception:
                pass

    is_demo = args.demo or (profile_dir is None and not any(timeline_posts.values()) and not args.login)

    # If not in demo mode, but timelines are empty, populate home with empty hint card
    if not is_demo and not any(timeline_posts.values()):
        empty_hint = {
            "id": "welcome_empty",
            "created_at": "",
            "account": {"display_name": "Mastui Client", "acct": username},
            "content": f"<p>Welcome to <strong>Mastui</strong>! No cached posts found for @{username} on {instance}. Press <strong>[c]</strong> to compose your first toot, <strong>[u]</strong> to switch/add account, or <strong>[?]</strong> for help.</p>",
            "visibility": "public",
        }
        timeline_posts["home"] = [empty_hint]

    app = MastuiEspressoApp(
        username=username,
        instance=instance,
        timeline_posts=timeline_posts,
        is_demo=is_demo,
        profile_dir=profile_dir,
        profile_name=profile_name or ("demo" if is_demo else "default"),
        api=api,
        cache_db_path=db_file,
        show_splash=True,
        show_login=args.login or (not args.demo and profile_dir is None),
    )
    program = Program(app, alt_screen=True, mouse=True)
    program.run()


if __name__ == "__main__":
    main()
