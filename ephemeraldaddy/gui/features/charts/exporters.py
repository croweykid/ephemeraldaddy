from __future__ import annotations

import csv
from collections import OrderedDict

from PySide6.QtCore import QSettings
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


def get_preferred_text_export_extension(
    settings: QSettings,
    *,
    preference_key: str,
    default_extension: str = ".txt",
) -> str:
    """Resolve the preferred text-export extension persisted in app settings."""
    raw_value = str(settings.value(preference_key, default_extension) or "").strip().lower()
    return ".md" if raw_value == ".md" else ".txt"


def get_text_export_path(
    parent: QWidget,
    settings: QSettings,
    *,
    dialog_title: str,
    default_stem: str,
    preference_key: str,
    default_extension: str = ".txt",
) -> str | None:
    """Open a TXT/MD save dialog and persist the last selected extension."""
    preferred_extension = get_preferred_text_export_extension(
        settings,
        preference_key=preference_key,
        default_extension=default_extension,
    )
    if preferred_extension == ".md":
        filters = "Markdown Files (*.md);;Text Files (*.txt)"
    else:
        filters = "Text Files (*.txt);;Markdown Files (*.md)"
    default_filename = f"{default_stem}{preferred_extension}"
    file_path, selected_filter = QFileDialog.getSaveFileName(
        parent,
        dialog_title,
        default_filename,
        filters,
    )
    if not file_path:
        return None

    selected_extension = ".md" if "*.md" in selected_filter else ".txt"
    if file_path.lower().endswith(".md"):
        selected_extension = ".md"
    elif file_path.lower().endswith(".txt"):
        selected_extension = ".txt"
    else:
        file_path = f"{file_path}{selected_extension}"

    settings.setValue(preference_key, selected_extension)
    return file_path
