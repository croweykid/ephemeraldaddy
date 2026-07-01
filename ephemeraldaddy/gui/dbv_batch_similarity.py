"""Similarity batch-edit helpers for Database View's right-side Batch Editor panel."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCompleter, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget

from ephemeraldaddy.core.db import get_chart_uid_map, list_charts
from ephemeraldaddy.gui.features.charts.chart_similarity_relationships import save_chart_similarity_relationship
from ephemeraldaddy.gui.features.charts.provenance import chart_row_is_similarity_participant
from ephemeraldaddy.gui.features.charts.similarity_pairing import build_chart_lookup, resolve_chart_id

logger = logging.getLogger(__name__)


def build_batch_similarity_section(
    owner: Any,
    add_collapsible_section: Callable[[str], tuple[QWidget, QVBoxLayout]],
) -> QWidget:
    """Build the Batch Editor Similarity section and wire its Apply action."""
    similarity_section, similarity_section_layout = add_collapsible_section("👥Similarity")
    similarity_help = QLabel(
        "Assign the selected chart(s) a perceived similarity score to another chart."
    )
    similarity_help.setWordWrap(True)
    similarity_section_layout.addWidget(similarity_help)

    owner.batch_similarity_chart_input = QLineEdit()
    owner.batch_similarity_chart_input.setPlaceholderText("chart name")
    similarity_section_layout.addWidget(owner.batch_similarity_chart_input)

    similarity_score_row = QHBoxLayout()
    similarity_score_row.addWidget(QLabel("Perceived %:"))
    owner.batch_similarity_percent_spin = QSpinBox()
    owner.batch_similarity_percent_spin.setRange(0, 100)
    owner.batch_similarity_percent_spin.setSuffix("%")
    owner.batch_similarity_percent_spin.setValue(0)
    similarity_score_row.addWidget(owner.batch_similarity_percent_spin)

    batch_similarity_apply_button = QPushButton("Apply")
    batch_similarity_apply_button.clicked.connect(lambda: apply_batch_similarity(owner))
    similarity_score_row.addWidget(batch_similarity_apply_button)
    similarity_score_row.addStretch(1)
    similarity_section_layout.addLayout(similarity_score_row)

    owner._bind_batch_enter_apply(owner.batch_similarity_chart_input, batch_similarity_apply_button.click)
    owner._bind_batch_enter_apply(owner.batch_similarity_percent_spin, batch_similarity_apply_button.click)
    refresh_batch_similarity_chart_options(owner)
    return similarity_section


def apply_batch_similarity_chart_completer(owner: Any, choices: list[str]) -> None:
    """Apply chart-name autocomplete choices to the Batch Editor Similarity chart field."""
    field = getattr(owner, "batch_similarity_chart_input", None)
    if not isinstance(field, QLineEdit):
        return
    completer = QCompleter(choices, field)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    field.setCompleter(completer)


def refresh_batch_similarity_chart_options(owner: Any, choices: list[str] | None = None) -> None:
    """Refresh the Batch Editor Similarity chart lookup and autocomplete choices."""
    if choices is None:
        similarity_rows = [
            normalized
            for row in list_charts()
            if (normalized := owner._normalize_chart_row(row)) is not None
            and chart_row_is_similarity_participant(normalized)
        ]
        chart_lookup, choices = build_chart_lookup(similarity_rows)
    else:
        chart_lookup = getattr(owner, "_batch_similarity_chart_lookup", {})
    owner._batch_similarity_chart_lookup = chart_lookup
    apply_batch_similarity_chart_completer(owner, choices)


def apply_batch_similarity(owner: Any) -> None:
    """Persist one perceived similarity percentage from selected chart(s) to a target chart."""
    selected_chart_ids = owner._exclude_similarities_placeholder_chart_ids(
        owner._selected_chart_ids()
    )
    if not selected_chart_ids:
        QMessageBox.information(
            owner,
            "Batch similarity",
            "Select one or more charts to assign a perceived similarity score.",
        )
        return

    lookup = getattr(owner, "_batch_similarity_chart_lookup", None)
    if not isinstance(lookup, dict) or not lookup:
        refresh_batch_similarity_chart_options(owner)
        lookup = getattr(owner, "_batch_similarity_chart_lookup", {})

    target_chart_id = resolve_chart_id(
        owner.batch_similarity_chart_input.text(),
        lookup if isinstance(lookup, dict) else {},
    )
    if target_chart_id is None:
        QMessageBox.warning(
            owner,
            "Batch similarity",
            "Choose a chart from the Similarity chart field autocomplete list.",
        )
        return

    target_chart = owner._get_chart_for_filter(int(target_chart_id))
    if target_chart is None:
        QMessageBox.warning(
            owner,
            "Batch similarity",
            "The selected similarity target chart could not be loaded.",
        )
        return

    changed_chart_ids = [chart_id for chart_id in selected_chart_ids if int(chart_id) != int(target_chart_id)]
    skipped_self_count = len(selected_chart_ids) - len(changed_chart_ids)
    if not changed_chart_ids:
        QMessageBox.warning(
            owner,
            "Batch similarity",
            "A chart cannot be assigned a perceived similarity score to itself.",
        )
        return

    target_display_name = getattr(target_chart, "name", "") or f"Chart #{target_chart_id}"
    if not owner._confirm_batch_edit(
        f"assign {owner.batch_similarity_percent_spin.value()}% perceived similarity to "
        f"{target_display_name} for",
        len(changed_chart_ids),
    ):
        return

    chart_uid_map = get_chart_uid_map([*changed_chart_ids, int(target_chart_id)])
    target_name = str(target_display_name).strip()
    score = int(owner.batch_similarity_percent_spin.value())
    saved_count = 0
    failures: list[str] = []
    relationship_path: Path | None = None

    for chart_id in changed_chart_ids:
        chart = owner._get_chart_for_filter(int(chart_id))
        if chart is None:
            failures.append(f"Chart #{chart_id}")
            continue
        chart_name = str(getattr(chart, "name", "") or f"Chart #{chart_id}").strip()
        try:
            relationship_path = save_chart_similarity_relationship(
                chart_1_id=int(chart_id),
                chart_1_name=chart_name,
                chart_2_id=int(target_chart_id),
                chart_2_name=target_name,
                chart_1_uid=chart_uid_map.get(int(chart_id)),
                chart_2_uid=chart_uid_map.get(int(target_chart_id)),
                user_reported_accuracy=score,
                not_applicable=False,
            )
        except Exception:
            logger.exception(
                "Failed to save batch perceived similarity relationship for chart %s to %s.",
                chart_id,
                target_chart_id,
            )
            failures.append(chart_name)
            continue
        saved_count += 1

    if saved_count:
        logger.info(
            "Saved %s batch perceived similarity relationship(s) to %s",
            saved_count,
            relationship_path,
        )
        owner._refresh_perceived_similarity_predictors_panel()

    message = f"Saved {saved_count} perceived similarity score(s)."
    if skipped_self_count:
        message += f"\nSkipped {skipped_self_count} self-link."
    if failures:
        message += "\nFailed: " + ", ".join(failures[:5])
        if len(failures) > 5:
            message += f", and {len(failures) - 5} more"
        QMessageBox.warning(owner, "Batch similarity", message)
    else:
        QMessageBox.information(owner, "Batch similarity", message)
