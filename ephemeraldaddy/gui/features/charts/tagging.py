"""Shared UI/tag parsing helpers for chart metadata tags."""

from __future__ import annotations

import html
import urllib.parse
from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCompleter, QLabel, QLineEdit


def normalize_tag_list(tags: Iterable[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in tags:
        tag = str(raw_value or "").strip()
        if not tag:
            continue
        dedupe_key = tag.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append(tag)
    return normalized


def parse_tag_text(raw_value: str | None) -> list[str]:
    return normalize_tag_list((raw_value or "").split(","))


def render_tag_chip_preview(preview_label: QLabel | None, tags: list[str]) -> None:
    if preview_label is None:
        return
    if not tags:
        preview_label.setText("")
        return
    chips = []
    for tag in tags:
        chips.append(
            "<span style=\""
            "background:#d9d9d9;"
            "color:#222;"
            "border:1px solid #bdbdbd;"
            "border-radius:8px;"
            "padding:1px 6px;"
            "margin-right:4px;"
            "\">"
            f"{html.escape(tag)}"
            "</span>"
        )
    preview_label.setText(" ".join(chips))


def render_removable_tag_chip_preview(
    preview_label: QLabel | None,
    tags: list[str],
    *,
    empty_text: str = "No tags yet.",
    remove_link_prefix: str = "remove_tag:",
) -> None:
    if preview_label is None:
        return
    if not tags:
        preview_label.setText(f"<span style='color:#8d8d8d;'>{html.escape(empty_text)}</span>")
        return
    chips: list[str] = []
    for tag in sorted(normalize_tag_list(tags), key=lambda value: value.casefold()):
        encoded_tag = urllib.parse.quote(tag, safe="")
        chips.append(
            "<span style='display:inline-block;"
            "padding:2px 8px;"
            "margin:0 6px 6px 0;"
            "border:1px solid #3a3a3a;"
            "border-radius:999px;"
            "background-color:#222;'>"
            f"{html.escape(tag)}"
            f"<a href='{html.escape(remove_link_prefix)}{encoded_tag}' style='color:#ff6f6f;text-decoration:none;font-weight:700;'> ✕</a>"
            "</span>"
        )
    preview_label.setText("".join(chips))


def parse_single_tag_text(raw_value: str | None) -> tuple[str | None, str | None]:
    parsed_tags = parse_tag_text(raw_value)
    if not parsed_tags:
        return None, None
    if len(parsed_tags) > 1:
        return None, "Please enter only one tag in this field."
    return parsed_tags[0], None


def merge_display_and_input_tags(
    display_tags: Iterable[str] | None,
    raw_input: str | None,
) -> list[str]:
    return normalize_tag_list([*normalize_tag_list(display_tags), *parse_tag_text(raw_input)])


def remove_tag_casefold(tags: Iterable[str] | None, tag_to_remove: str | None) -> list[str]:
    normalized_remove_key = str(tag_to_remove or "").strip().casefold()
    if not normalized_remove_key:
        return normalize_tag_list(tags)
    return [
        tag
        for tag in normalize_tag_list(tags)
        if tag.casefold() != normalized_remove_key
    ]


def replace_active_tag_segment(line_edit: QLineEdit, completed_tag: str) -> None:
    leading, separator, _trailing = line_edit.text().rpartition(",")
    prefix = f"{leading}, " if separator else ""
    new_text = f"{prefix}{completed_tag}, "
    line_edit.setText(new_text)
    line_edit.setCursorPosition(len(new_text))


def apply_tag_completer(
    line_edit: QLineEdit,
    known_tags: list[str],
) -> None:
    completer = QCompleter(known_tags, line_edit)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    completer.activated[str].connect(
        lambda value, target=line_edit: replace_active_tag_segment(target, value)
    )
    line_edit.setCompleter(completer)
    line_edit._tags_completer = completer
