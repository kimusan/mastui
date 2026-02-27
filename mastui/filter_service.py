from __future__ import annotations

from typing import Any


def list_filters(api) -> list[dict]:
    filters = list(api.filters_v2() or [])
    filters.sort(key=lambda item: str(item.get("title", "")).lower())
    return filters


def create_filter(api, payload: dict[str, Any]) -> dict:
    return api.create_filter_v2(
        title=payload["title"],
        context=payload["context"],
        filter_action=payload["filter_action"],
        expires_in=payload.get("expires_in"),
        keywords_attributes=[
            {
                "keyword": kw["keyword"],
                "whole_word": bool(kw.get("whole_word", False)),
            }
            for kw in payload["keywords"]
        ],
    )


def update_filter(api, existing_filter: dict, payload: dict[str, Any]) -> dict:
    filter_id = existing_filter["id"]

    update_kwargs = {
        "title": payload["title"],
        "context": payload["context"],
        "filter_action": payload["filter_action"],
    }
    if payload.get("update_expires", True):
        update_kwargs["expires_in"] = payload.get("expires_in")

    api.update_filter_v2(filter_id=filter_id, **update_kwargs)
    _sync_filter_keywords(
        api,
        filter_id=filter_id,
        existing_keywords=list(existing_filter.get("keywords") or []),
        updated_keywords=payload["keywords"],
    )
    return api.filter_v2(filter_id)


def delete_filter(api, filter_id: str) -> None:
    api.delete_filter_v2(filter_id)


def _sync_filter_keywords(
    api,
    filter_id: str,
    existing_keywords: list[dict],
    updated_keywords: list[dict],
) -> None:
    existing_by_id = {
        str(keyword["id"]): keyword
        for keyword in existing_keywords
        if keyword.get("id") is not None
    }
    kept_existing_ids: set[str] = set()
    deleted_existing_ids: set[str] = set()

    for keyword in updated_keywords:
        text = str(keyword.get("keyword", "")).strip()
        if not text:
            continue

        whole_word = bool(keyword.get("whole_word", False))
        existing_id = keyword.get("id")
        if existing_id is None:
            api.add_filter_keyword_v2(filter_id, text, whole_word=whole_word)
            continue

        existing_id_str = str(existing_id)
        existing_entry = existing_by_id.get(existing_id_str)
        if not existing_entry:
            api.add_filter_keyword_v2(filter_id, text, whole_word=whole_word)
            continue

        same_text = str(existing_entry.get("keyword", "")) == text
        same_whole_word = bool(existing_entry.get("whole_word", False)) == whole_word
        if same_text and same_whole_word:
            kept_existing_ids.add(existing_id_str)
            continue

        api.delete_filter_keyword_v2(existing_id_str)
        deleted_existing_ids.add(existing_id_str)
        api.add_filter_keyword_v2(filter_id, text, whole_word=whole_word)

    for existing_id, _ in existing_by_id.items():
        if existing_id in kept_existing_ids or existing_id in deleted_existing_ids:
            continue
        api.delete_filter_keyword_v2(existing_id)
