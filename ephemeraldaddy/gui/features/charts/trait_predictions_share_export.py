"""Share/export adapter for Chart View Trait Predictions."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFileDialog, QTableView, QToolButton

from ephemeraldaddy.gui.style import configure_share_export_icon_button


def _share_icon_path() -> str | None:
    icon_path = Path(__file__).resolve().parents[3] / "graphics" / "share_icon2.png"
    return str(icon_path) if icon_path.exists() else None


def _visible_trait_rows(table: QTableView) -> list[list[str]]:
    model = table.model()
    if model is None:
        return []
    return [
        [
            str(model.data(model.index(row, column), Qt.DisplayRole) or "")
            for column in range(model.columnCount())
        ]
        for row in range(model.rowCount())
    ]


def _trait_headers(table: QTableView) -> list[str]:
    model = table.model()
    if model is None:
        return []
    return [
        str(model.headerData(column, Qt.Horizontal, Qt.DisplayRole) or "")
        for column in range(model.columnCount())
    ]


def _export_visible_traits(owner: Any, table: QTableView) -> None:
    rows = _visible_trait_rows(table)
    if not rows:
        return

    combo = getattr(owner, "traits_prediction_mode_combo", None)
    mode = combo.currentData() if isinstance(combo, QComboBox) else "above"
    direction = "below" if mode == "below" else "above"
    default_name = f"traits-{direction}-db-average.csv"

    path, _selected_filter = QFileDialog.getSaveFileName(
        owner,
        "Export Traits",
        default_name,
        "CSV File (*.csv)",
    )
    if not path:
        return
    if not path.lower().endswith(".csv"):
        path = f"{path}.csv"

    with open(path, "w", encoding="utf-8", newline="") as export_file:
        writer = csv.writer(export_file)
        headers = _trait_headers(table)
        if headers:
            writer.writerow(headers)
        writer.writerows(rows)


def _install_traits_export_button(owner: Any, table: QTableView) -> None:
    existing = getattr(owner, "traits_prediction_export_button", None)
    if isinstance(existing, QToolButton):
        return

    combo = getattr(owner, "traits_prediction_mode_combo", None)
    header_row = combo.parentWidget() if isinstance(combo, QComboBox) else None
    header_layout = header_row.layout() if header_row is not None else None
    if header_row is None or header_layout is None:
        return

    export_button = QToolButton(header_row)
    configure_share_export_icon_button(
        export_button,
        share_icon_path=_share_icon_path(),
        tooltip="Export the visible Traits table data as CSV",
    )
    export_button.clicked.connect(lambda: _export_visible_traits(owner, table))
    header_layout.addWidget(export_button, alignment=Qt.AlignRight)
    owner.traits_prediction_export_button = export_button


def install_trait_predictions_share_export(trait_predictions: Any) -> None:
    """Install the Traits share/export control without changing scoring behavior."""
    if getattr(
        trait_predictions,
        "_ephemeraldaddy_trait_predictions_share_export_installed",
        False,
    ):
        return

    original_configure = trait_predictions.configure_traits_prediction_table

    def configure_traits_prediction_table(owner: Any, table: QTableView) -> None:
        original_configure(owner, table)
        _install_traits_export_button(owner, table)

    trait_predictions.configure_traits_prediction_table = configure_traits_prediction_table
    trait_predictions._ephemeraldaddy_trait_predictions_share_export_installed = True
