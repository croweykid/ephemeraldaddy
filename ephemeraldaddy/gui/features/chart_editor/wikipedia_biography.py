from __future__ import annotations

import datetime
from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import QInputDialog, QWidget

from ephemeraldaddy.gui.wikipedia_blurb_getter import (
    WikipediaPageNotFound,
    fetch_wikipedia_blurb,
    unique_title_matching_birth_date,
)
from ephemeraldaddy.gui.wikipedia_search import (
    parse_wikipedia_birth_data,
    resolve_wikipedia_page_options,
)


def _candidate_birth_date(title: str) -> datetime.date | None:
    try:
        data = parse_wikipedia_birth_data(title)
        return datetime.date(
            int(data["birth_year"]),
            int(data["birth_month"]),
            int(data["birth_day"]),
        )
    except (KeyError, OSError, TypeError, ValueError):
        return None


def parse_chart_birth_date(year: str, month: str, day: str) -> datetime.date | None:
    """Build a factual chart date when all three editor fields are valid."""
    try:
        return datetime.date(int(year), int(month), int(day))
    except (TypeError, ValueError):
        return None


def fetch_wikipedia_biography_with_dialogs(
    parent: QWidget,
    *,
    chart_name: str,
    chart_birth_date: datetime.date | None,
    resolve_options: Callable[[str], dict[str, Any]] = resolve_wikipedia_page_options,
    candidate_birth_date: Callable[[str], datetime.date | None] = _candidate_birth_date,
) -> str | None:
    """Resolve and confirm the Wikipedia person used by Chart Editor's Get Bio."""
    query = chart_name.strip()
    while True:
        resolution = resolve_options(query)
        status = str(resolution.get("status") or "")
        if status != "not_found":
            break
        query, accepted = QInputDialog.getText(
            parent,
            "Wikipedia biography search",
            "No exact Wikipedia match was found. Edit the name to search:",
            text=query,
        )
        query = query.strip()
        if not accepted or not query:
            return None

    if status == "single":
        options = [str(resolution.get("title") or "").strip()]
    else:
        options = [
            str(option).strip()
            for option in resolution.get("options", [])
            if str(option).strip()
        ]
    if not options:
        raise WikipediaPageNotFound(f"No Wikipedia page was found for {query!r}.")

    dated_options = [(title, candidate_birth_date(title)) for title in options]
    birthday_match = unique_title_matching_birth_date(dated_options, chart_birth_date)
    if birthday_match is not None:
        selected_title = birthday_match
    else:
        labels = [
            f"{title} — born {birth_date.isoformat()}"
            if birth_date is not None
            else f"{title} — birth date unavailable"
            for title, birth_date in dated_options
        ]
        selected_label, accepted = QInputDialog.getItem(
            parent,
            "Wikipedia biography search",
            "Confirm the correct Wikipedia page:",
            labels,
            0,
            False,
        )
        if not accepted or not selected_label:
            return None
        selected_title = options[labels.index(selected_label)]

    blurb = fetch_wikipedia_blurb(selected_title)
    if not blurb.text:
        raise ValueError(f"Wikipedia did not provide biography text for {selected_title!r}.")
    return blurb.text
