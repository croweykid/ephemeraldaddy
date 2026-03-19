from __future__ import annotations

import csv
from collections import OrderedDict

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget


def export_aspect_distribution_csv_dialog(
    parent: QWidget,
    aspect_counts: OrderedDict[str, float],
    *,
    default_file_stem: str = "aspect_distribution",
) -> None:
    """Open save dialog and export aspect distribution counts to CSV."""
    default_filename = f"{default_file_stem}.csv"
    file_path, _selected_filter = QFileDialog.getSaveFileName(
        parent,
        "Export Aspect Distribution as CSV",
        default_filename,
        "CSV Files (*.csv)",
    )
    if not file_path:
        return
    if not file_path.lower().endswith(".csv"):
        file_path = f"{file_path}.csv"

    try:
        with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["aspect_type", "count"])
            for aspect_key, count in aspect_counts.items():
                writer.writerow([aspect_key, count])
    except Exception as exc:
        QMessageBox.critical(parent, "Export failed", f"Could not write CSV file.\n\n{exc}")
        return

    QMessageBox.information(parent, "Export complete", f"Exported aspect distribution CSV to:\n{file_path}")
