from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from PySide6.QtWidgets import QInputDialog, QMessageBox, QWidget

from ephemeraldaddy.gui.wikipedia_blurb_getter import populate_wikipedia_biography
from ephemeraldaddy.gui.wikipedia_search import (
    parse_wikipedia_birth_data,
    resolve_wikipedia_page_options,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WikipediaImportResult:
    profile_data: dict[str, Any]
    finish_manually: bool


def confirm_manual_wikipedia_import(parent: QWidget, page_title: str) -> bool:
    """Ask whether a Wikipedia result without a birthplace should become a draft."""
    prompt = QMessageBox(parent)
    prompt.setIcon(QMessageBox.Icon.Information)
    prompt.setWindowTitle("Astrotheme import")
    prompt.setText(
        f"{page_title} found on Wikipedia, but no birth place info is available.\n\n"
        "Import available info anyway and fill in blank fields manually? Or just forget it?"
    )
    cancel_button = prompt.addButton(
        "Cancel import",
        QMessageBox.ButtonRole.RejectRole,
    )
    finish_button = prompt.addButton(
        "Finish manually",
        QMessageBox.ButtonRole.AcceptRole,
    )
    prompt.setDefaultButton(cancel_button)
    prompt.setEscapeButton(cancel_button)
    prompt.exec()
    return prompt.clickedButton() is finish_button


def resolve_wikipedia_import(
    parent: QWidget,
    raw_query: str,
    *,
    debug_id: str,
) -> WikipediaImportResult | None:
    """Run the Wikipedia fallback dialogs and return normalized import data."""
    wikipedia_prompt = QMessageBox(parent)
    wikipedia_prompt.setIcon(QMessageBox.Icon.Information)
    wikipedia_prompt.setWindowTitle("Astrotheme import")
    wikipedia_prompt.setText(
        f"{raw_query} cannot be found on Astrotheme - trying Wikipedia..."
    )
    wikipedia_prompt.setStandardButtons(
        QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
    )
    cool_button = wikipedia_prompt.button(QMessageBox.StandardButton.Ok)
    cancel_button = wikipedia_prompt.button(QMessageBox.StandardButton.Cancel)
    if cool_button is not None:
        cool_button.setText("Cool")
        wikipedia_prompt.setDefaultButton(cool_button)
        cool_button.setStyleSheet(
            "QPushButton { background-color: #7b2cbf; border-color: #9d4edd; color: #ffffff; }"
            "QPushButton:hover { background-color: #8f3fd1; }"
        )
    if cancel_button is not None:
        wikipedia_prompt.setEscapeButton(cancel_button)
        cancel_button.setStyleSheet(
            "QPushButton { background-color: #5f6368; border-color: #747981; color: #f4f1ea; }"
            "QPushButton:hover { background-color: #6f747c; }"
        )
    wikipedia_prompt.exec()
    if wikipedia_prompt.standardButton(
        wikipedia_prompt.clickedButton()
    ) == QMessageBox.StandardButton.Cancel:
        logger.info(
            "Astrotheme import canceled before Wikipedia backup (id=%s query=%r).",
            debug_id,
            raw_query,
        )
        return None

    try:
        resolution = resolve_wikipedia_page_options(raw_query)
    except Exception as exc:
        logger.exception(
            "Astrotheme import Wikipedia resolution failed (id=%s query=%r): %s",
            debug_id,
            raw_query,
            exc,
        )
        QMessageBox.warning(
            parent,
            "Astrotheme import",
            f"Could not load backup Wikipedia lookup:\n{exc}",
        )
        return None

    status = str(resolution.get("status", "") or "")
    selected_title = ""
    if status == "not_found":
        QMessageBox.information(
            parent, "Astrotheme import", f"{raw_query} not found on Wikipedia. :("
        )
        return None
    if status == "multiple":
        options = [
            str(item).strip()
            for item in resolution.get("options", [])
            if str(item).strip()
        ]
        if not options:
            QMessageBox.information(
                parent, "Astrotheme import", f"{raw_query} not found on Wikipedia. :("
            )
            return None
        selected_title, confirmed = QInputDialog.getItem(
            parent,
            "Wikipedia backup search",
            "Multiple Wikipedia pages found. Pick one:",
            options,
            0,
            False,
        )
        if not confirmed or not selected_title:
            return None
    else:
        selected_title = str(resolution.get("title", "")).strip()

    if not selected_title:
        QMessageBox.information(
            parent, "Astrotheme import", f"{raw_query} not found on Wikipedia. :("
        )
        return None

    try:
        wiki_data = parse_wikipedia_birth_data(selected_title)
    except Exception as exc:
        logger.exception(
            "Astrotheme import Wikipedia parse failed (id=%s title=%r): %s",
            debug_id,
            selected_title,
            exc,
        )
        QMessageBox.information(
            parent,
            "Astrotheme import",
            f"{selected_title} found on Wikipedia, but no birthdate info is available; search abandoned.",
        )
        return None

    birth_place = str(wiki_data.get("birth_place", "")).strip()
    finish_manually = False
    if not birth_place:
        finish_manually = confirm_manual_wikipedia_import(parent, selected_title)
        if not finish_manually:
            logger.info(
                "Wikipedia import canceled because birthplace is unavailable "
                "(id=%s title=%r).",
                debug_id,
                selected_title,
            )
            return None

    profile_data = {
        "name": str(wiki_data.get("name") or selected_title),
        "birth_year": int(wiki_data["birth_year"]),
        "birth_month": int(wiki_data["birth_month"]),
        "birth_day": int(wiki_data["birth_day"]),
        "birth_hour": 12,
        "birth_minute": 0,
        "time_unknown": True,
        "birth_place": birth_place,
        "data_rating": "XX",
        "biography": str(wiki_data.get("biography", "") or ""),
        "profile_url": str(wiki_data.get("source_url", "")),
    }
    try:
        populate_wikipedia_biography(profile_data, page_title=selected_title)
    except Exception as exc:
        logger.warning(
            "Wikipedia biography import failed (id=%s title=%r): %s",
            debug_id,
            selected_title,
            exc,
        )
    return WikipediaImportResult(profile_data, finish_manually)
