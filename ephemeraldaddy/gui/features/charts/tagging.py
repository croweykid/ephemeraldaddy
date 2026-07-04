"""Shared UI/tag parsing helpers for chart metadata tags."""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCompleter, QLabel, QLineEdit

from ephemeraldaddy.gui.style import build_tag_chip_html, configure_tag_chip_label


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
    configure_tag_chip_label(preview_label)
    if not tags:
        preview_label.setText("")
        return
    chips = []
    for tag in tags:
        chips.append(build_tag_chip_html(tag))
    preview_label.setText("".join(chips))


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
    # Keep typing focus anchored in the tag editor.  The completer popup is
    # purely a suggestion surface; allowing it to take focus can interrupt
    # rapid typing in Chart View's right-hand Subjective Notes panel.
    completer.popup().setFocusPolicy(Qt.NoFocus)
    completer.activated[str].connect(
        lambda value, target=line_edit: replace_active_tag_segment(target, value)
    )
    line_edit.setCompleter(completer)
    line_edit._tags_completer = completer
