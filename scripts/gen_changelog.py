#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


SECTION_RE = re.compile(r"^## \[(?P<name>[^\]]+)\](?: - (?P<date>\d{4}-\d{2}-\d{2}))?$")
TAG_RE = re.compile(r"^v?\d+\.\d+\.\d+(?:[A-Za-z0-9.-]+)?$")


@dataclass
class ReleaseTag:
    raw: str
    version: str
    date: str


@dataclass
class Section:
    name: str
    date: Optional[str]
    body: List[str]


def run(cmd: List[str], *, cwd: Optional[str] = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd).decode("utf-8", "replace").strip()


def normalize_version(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def get_release_tags_first_parent() -> List[ReleaseTag]:
    commits = run(["git", "rev-list", "--first-parent", "--reverse", "HEAD"]).splitlines()
    tags: List[ReleaseTag] = []
    for commit in commits:
        tags_here = run(["git", "tag", "--points-at", commit]).splitlines()
        for tag in tags_here:
            tag = tag.strip()
            if not tag or not TAG_RE.match(tag):
                continue
            date = run(["git", "log", "-1", "--date=short", "--pretty=format:%ad", tag])
            tags.append(ReleaseTag(raw=tag, version=normalize_version(tag), date=date))
    return tags


def subjects_for_range(start_tag: Optional[str], end_ref: str) -> List[str]:
    range_spec = end_ref if start_tag is None else f"{start_tag}..{end_ref}"
    out = run(
        [
            "git",
            "log",
            "--first-parent",
            "--no-merges",
            "--pretty=format:%s",
            range_spec,
        ]
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def parse_changelog(path: Path) -> tuple[List[str], List[str], Dict[str, Section]]:
    if not path.exists():
        preamble = [
            "# Changelog",
            "",
            "All notable changes to this project are documented in this file.",
            "",
            "This changelog is derived from git release tags and commit history on `main`.",
        ]
        return preamble, [], {}

    lines = path.read_text(encoding="utf-8").splitlines()
    preamble: List[str] = []
    order: List[str] = []
    sections: Dict[str, Section] = {}

    idx = 0
    while idx < len(lines):
        match = SECTION_RE.match(lines[idx].strip())
        if match:
            break
        preamble.append(lines[idx])
        idx += 1

    while idx < len(lines):
        header = lines[idx].strip()
        match = SECTION_RE.match(header)
        if not match:
            idx += 1
            continue

        name = match.group("name")
        date = match.group("date")
        idx += 1

        body: List[str] = []
        while idx < len(lines):
            if SECTION_RE.match(lines[idx].strip()):
                break
            body.append(lines[idx])
            idx += 1

        while body and not body[-1].strip():
            body.pop()
        while body and not body[0].strip():
            body.pop(0)

        sections[name] = Section(name=name, date=date, body=body)
        order.append(name)

    return preamble, order, sections


def bullets(subjects: List[str], *, empty_message: str) -> List[str]:
    if not subjects:
        return [f"- {empty_message}"]
    return [f"- {subject}" for subject in subjects]


def append_section(lines: List[str], name: str, date: Optional[str], body: List[str]) -> None:
    if date:
        lines.append(f"## [{name}] - {date}")
    else:
        lines.append(f"## [{name}]")
    lines.append("")
    if body:
        lines.extend(body)
    else:
        lines.append("- No changes yet.")
    lines.append("")


def build_changelog(
    output: Path,
    release_version: Optional[str],
    release_date: Optional[str],
) -> None:
    preamble, existing_order, existing_sections = parse_changelog(output)
    tags = get_release_tags_first_parent()
    tags_by_version = {tag.version: tag for tag in tags}

    generated_tag_entries: Dict[str, List[str]] = {}
    previous_tag: Optional[str] = None
    for tag in tags:
        generated_tag_entries[tag.version] = subjects_for_range(previous_tag, tag.raw)
        previous_tag = tag.raw

    latest_tag = tags[-1].raw if tags else None
    unreleased_entries = subjects_for_range(latest_tag, "HEAD")
    release_entries: List[str] = []
    if release_version:
        release_entries = list(unreleased_entries)
        unreleased_entries = []

    lines: List[str] = []
    if preamble:
        lines.extend(preamble)
    else:
        lines.extend(
            [
                "# Changelog",
                "",
                "All notable changes to this project are documented in this file.",
                "",
                "This changelog is derived from git release tags and commit history on `main`.",
            ]
        )
    while lines and not lines[-1].strip():
        lines.pop()
    lines.append("")

    append_section(
        lines,
        "Unreleased",
        None,
        bullets(unreleased_entries, empty_message="No changes yet."),
    )

    ordered_versions: List[str] = []
    if release_version and release_version not in tags_by_version:
        ordered_versions.append(release_version)
    ordered_versions.extend(tag.version for tag in reversed(tags))

    for version in ordered_versions:
        if release_version and version == release_version and version not in tags_by_version:
            date = release_date or dt.date.today().isoformat()
            existing = existing_sections.get(version)
            body = existing.body if existing else bullets(
                release_entries,
                empty_message="No changes recorded in commit history for this release.",
            )
            append_section(lines, version, date, body)
            continue

        tag = tags_by_version.get(version)
        if not tag:
            continue

        existing = existing_sections.get(version)
        body = existing.body if existing else bullets(
            generated_tag_entries.get(version, []),
            empty_message="No changes recorded in commit history for this release.",
        )
        append_section(lines, version, tag.date, body)

    known_names = {"Unreleased", *ordered_versions}
    for name in existing_order:
        if name in known_names:
            continue
        section = existing_sections[name]
        append_section(lines, section.name, section.date, section.body)

    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update CHANGELOG.md from git tags/history.")
    parser.add_argument(
        "--output",
        default="CHANGELOG.md",
        help="Path to changelog file (default: CHANGELOG.md).",
    )
    parser.add_argument(
        "--release-version",
        help=(
            "Optional release version (e.g. 1.8.0). "
            "When set, creates/updates that section from current unreleased commits."
        ),
    )
    parser.add_argument(
        "--release-date",
        help="Optional release date in YYYY-MM-DD. Defaults to today when --release-version is set.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_changelog(
        output=Path(args.output),
        release_version=args.release_version,
        release_date=args.release_date,
    )


if __name__ == "__main__":
    main()
