"""Qt orchestration helpers for importing incomplete external web profiles."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


class IncompleteWikipediaImportChoice(Enum):
    CANCEL = "cancel"
    FINISH_MANUALLY = "finish_manually"


def missing_wikipedia_birth_fields(profile: Mapping[str, Any]) -> tuple[str, ...]:
    """Describe authoritative fields that Wikipedia could not provide."""
    missing: list[str] = []
    if not all(profile.get(key) is not None for key in ("birth_year", "birth_month", "birth_day")):
        missing.append("birth date")
    if not str(profile.get("birth_place", "") or "").strip():
        missing.append("birth place")
    return tuple(missing)


def choose_incomplete_wikipedia_import(
    parent: QWidget,
    *,
    page_title: str,
    missing_fields: tuple[str, ...],
) -> IncompleteWikipediaImportChoice:
    """Let the user retain useful Wikipedia fields or abandon the import."""
    from PySide6.QtWidgets import QMessageBox

    missing_text = " and ".join(missing_fields) or "some birth information"
    availability_verb = "is" if len(missing_fields) == 1 else "are"
    prompt = QMessageBox(parent)
    prompt.setIcon(QMessageBox.Icon.Information)
    prompt.setWindowTitle("Astrotheme import")
    prompt.setText(
        f"{page_title} was found on Wikipedia, but {missing_text} {availability_verb} not available.\n\n"
        "Import the available information anyway and fill in the blank fields manually?"
    )
    cancel_button = prompt.addButton("Cancel import", QMessageBox.ButtonRole.RejectRole)
    finish_button = prompt.addButton("Finish manually", QMessageBox.ButtonRole.AcceptRole)
    prompt.setDefaultButton(cancel_button)
    prompt.setEscapeButton(cancel_button)
    prompt.exec()
    if prompt.clickedButton() is finish_button:
        return IncompleteWikipediaImportChoice.FINISH_MANUALLY
    return IncompleteWikipediaImportChoice.CANCEL
