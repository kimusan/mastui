#!/usr/bin/env bash
set -euo pipefail

if ! command -v poetry >/dev/null 2>&1; then
	echo "poetry not found; please install poetry" >&2
	exit 1
fi

if [[ $# -lt 1 ]]; then
	echo "Usage: $0 <major|minor|patch|prepatch|prerelease|<version>>" >&2
	exit 1
fi

BUMP_ARG="$1"

# Bump version in pyproject.toml
poetry version "$BUMP_ARG"
NEW_VER="$(poetry version -s)"

# Update CHANGELOG.md while preserving existing release notes.
# This promotes current Unreleased commits into the new version section.
python3 scripts/gen_changelog.py --release-version "$NEW_VER"

# Stage and commit
git add pyproject.toml CHANGELOG.md || true
git commit -m "chore(release): v${NEW_VER}"

# Create tag
git tag "v${NEW_VER}"

echo "Release prepared: v${NEW_VER}"
echo "Next steps: git push && git push --tags"
