from __future__ import annotations

from typing import Iterable, Sequence

# Catalog loosely follows Mastodon's supported languages.
LANGUAGE_CATALOG: list[tuple[str, str]] = [
    ("Arabic", "ar"),
    ("Bulgarian", "bg"),
    ("Catalan", "ca"),
    ("Chinese (Simplified)", "zh"),
    ("Chinese (Hong Kong)", "zh-hk"),
    ("Chinese (Traditional)", "zh-tw"),
    ("Croatian", "hr"),
    ("Czech", "cs"),
    ("Danish", "da"),
    ("Dutch", "nl"),
    ("English", "en"),
    ("English (UK)", "en-gb"),
    ("English (US)", "en-us"),
    ("Esperanto", "eo"),
    ("Estonian", "et"),
    ("Finnish", "fi"),
    ("French", "fr"),
    ("Galician", "gl"),
    ("German", "de"),
    ("Greek", "el"),
    ("Hebrew", "he"),
    ("Hindi", "hi"),
    ("Hungarian", "hu"),
    ("Indonesian", "id"),
    ("Irish", "ga"),
    ("Italian", "it"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Latvian", "lv"),
    ("Lithuanian", "lt"),
    ("Malay", "ms"),
    ("Norwegian Bokmål", "nb"),
    ("Polish", "pl"),
    ("Portuguese", "pt"),
    ("Portuguese (Brazil)", "pt-br"),
    ("Romanian", "ro"),
    ("Russian", "ru"),
    ("Serbian", "sr"),
    ("Slovak", "sk"),
    ("Slovenian", "sl"),
    ("Spanish", "es"),
    ("Swedish", "sv"),
    ("Thai", "th"),
    ("Turkish", "tr"),
    ("Ukrainian", "uk"),
    ("Vietnamese", "vi"),
    ("Welsh", "cy"),
]

DEFAULT_LANGUAGE_CODES: list[str] = [
    "zh",
    "da",
    "en",
    "fr",
    "de",
    "ja",
    "ko",
    "es",
]

_LANGUAGE_NAME_MAP = {code: label for label, code in LANGUAGE_CATALOG}


def normalize_language_code(code: str | None) -> str | None:
    """Normalize user supplied language codes for storage."""
    if not code:
        return None
    return code.strip().lower()


def get_language_label(code: str) -> str:
    """Resolve a friendly name for a language code."""
    normalized = normalize_language_code(code)
    if not normalized:
        return ""

    if normalized in _LANGUAGE_NAME_MAP:
        return _LANGUAGE_NAME_MAP[normalized]

    parts = normalized.split("-")
    if len(parts) > 1 and parts[0] in _LANGUAGE_NAME_MAP:
        region = parts[1].upper()
        return f"{_LANGUAGE_NAME_MAP[parts[0]]} ({region})"

    return normalized.upper()


def dedupe_language_codes(codes: Iterable[str]) -> list[str]:
    """Return normalized, de-duplicated language codes."""
    seen: set[str] = set()
    normalized_codes: list[str] = []
    for code in codes:
        normalized = normalize_language_code(code)
        if not normalized or normalized in seen:
            continue
        normalized_codes.append(normalized)
        seen.add(normalized)
    return normalized_codes


def get_language_options(
    preferred_codes: Sequence[str], extra_codes: Iterable[str] | None = None
) -> list[tuple[str, str]]:
    """Build Select options honoring preferred order."""
    ordered = dedupe_language_codes(preferred_codes)
    if extra_codes:
        for extra in dedupe_language_codes(extra_codes):
            if extra not in ordered:
                ordered.append(extra)
    if not ordered:
        ordered = DEFAULT_LANGUAGE_CODES.copy()
    return [(f"{get_language_label(code)} ({code})", code) for code in ordered]


def get_available_language_options(exclude: Iterable[str] | None = None) -> list[tuple[str, str]]:
    """Return catalog entries that are not excluded."""
    excluded = set(dedupe_language_codes(exclude or []))
    return [
        (f"{label} ({code})", code)
        for label, code in LANGUAGE_CATALOG
        if normalize_language_code(code) not in excluded
    ]


def get_default_language_codes() -> list[str]:
    """Return a copy of the default ordering."""
    return DEFAULT_LANGUAGE_CODES.copy()
