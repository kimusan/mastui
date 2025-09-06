#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass(order=True)
class Tag:
    major: int
    minor: int
    patch: int
    name: str


SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def run(cmd: List[str], *, cwd: Optional[str] = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd).decode("utf-8", "replace").strip()


def get_tags() -> List[Tag]:
    tags_raw = run(["git", "tag", "--list"]).splitlines()
    tags: List[Tag] = []
    for t in tags_raw:
        m = SEMVER.match(t.strip())
        if not m:
            continue
        tags.append(Tag(int(m.group(1)), int(m.group(2)), int(m.group(3)), t.strip()))
    tags.sort()  # by major, minor, patch
    return tags


def log_range(a: Optional[str], b: str) -> List[str]:
    rng = b if a is None else f"{a}..{b}"
    if a is None:
        # first release: since the beginning
        rng = b
    out = run([
        "git",
        "log",
        rng,
        "--no-merges",
        "--pretty=format:%h %ad %s",
        "--date=short",
    ])
    return [l for l in out.splitlines() if l.strip()]


def log_since(tag: str) -> List[str]:
    out = run([
        "git",
        "log",
        f"{tag}..HEAD",
        "--no-merges",
        "--pretty=format:%h %ad %s",
        "--date=short",
    ])
    return [l for l in out.splitlines() if l.strip()]


def main() -> None:
    tags = get_tags()
    lines: List[str] = []
    lines.append("# Changelog")
    lines.append("")

    # Build release sections ascending, then render descending (newest first)
    sections: List[tuple[str, List[str]]] = []
    prev: Optional[str] = None
    for t in tags:
        rng_log = log_range(prev, t.name)
        sections.append((t.name, rng_log))
        prev = t.name

    # Unreleased at top if any
    if tags:
        head_log = log_since(tags[-1].name)
        if head_log:
            lines.append("## [Unreleased]")
            lines.append("")
            for l in head_log:
                lines.append(f"- {l}")
            lines.append("")

    # Now print sections in reverse (newest first)
    for name, entries in reversed(sections):
        lines.append(f"## {name}")
        lines.append("")
        if entries:
            for l in entries:
                lines.append(f"- {l}")
        else:
            lines.append("- No changes recorded")
        lines.append("")

    with open("CHANGELOG.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


if __name__ == "__main__":
    main()
