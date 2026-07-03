from __future__ import annotations

import csv
import datetime
import re
from pathlib import Path
from collections import OrderedDict
from typing import Callable

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget


from ephemeraldaddy.gui.features.charts.similarities_export import (
    build_similarities_json_export_payload,
    format_similarities_json_export_payload,
    similarities_json_payload_has_factors,
)


_SIMILARITIES_EXPORT_SAVE_DIR_KEY = "similarities_analysis/last_export_directory"


def similarities_export_sample_suffix(export_sections) -> str:
    """Return a filename suffix such as ``_75samples`` for Similarities exports."""
    for _section_title, matches in export_sections or []:
        for match in matches or []:
            if len(match) < 3:
                continue
            try:
                sample_size = int(match[2])
            except (TypeError, ValueError):
                continue
            if sample_size > 0:
                return f"_{sample_size}samples"
    return ""


def similarities_export_default_path(settings: QSettings, default_filename: str) -> str:
    """Return default filename in the most recent Similarities export directory."""
    last_directory = str(settings.value(_SIMILARITIES_EXPORT_SAVE_DIR_KEY, "") or "").strip()
    if last_directory:
        return str(Path(last_directory) / default_filename)
    return default_filename


def remember_similarities_export_directory(settings: QSettings, file_path: str) -> None:
    """Persist the directory containing the latest Similarities Analysis export."""
    directory = str(Path(file_path).expanduser().parent)
    if directory:
        settings.setValue(_SIMILARITIES_EXPORT_SAVE_DIR_KEY, directory)


def sanitize_export_token(value: str, fallback: str = "chart") -> str:
    """Return a filesystem-friendly token for generated export filenames."""
    token = re.sub(r"[^A-Za-z0-9_-]+", "_", (value or "").strip()).strip("_")
    return token or fallback


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


def export_similarities_analysis_json_dialog(
    parent: QWidget,
    export_sections,
    *,
    reactivate_callback: Callable[[], None] | None = None,
) -> None:
    """Prompt for a name/path and export Similarities Analysis data as Python."""
    if not export_sections:
        QMessageBox.information(
            parent,
            "No similarities data",
            "Select at least 2 charts to generate similarities before exporting.",
        )
        return

    selection_name, accepted = QInputDialog.getText(
        parent,
        "Selection name",
        "Name this selection (used as the Python key and profile name):",
        text="Selection",
    )
    if not accepted:
        return
    selection_name = selection_name.strip() or "Selection"

    payload = build_similarities_json_export_payload(selection_name, export_sections)
    if not similarities_json_payload_has_factors(payload, selection_name):
        QMessageBox.information(
            parent,
            "No Python factors",
            "No similarities fall beyond the second standard-error tier from the database norm.",
        )
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    sanitized_name = re.sub(r"[^\w\s-]", "", selection_name).strip() or "selection"
    sanitized_name = re.sub(r"\s+", "_", sanitized_name)
    sample_suffix = similarities_export_sample_suffix(export_sections)
    default_filename = f"ephemeraldaddy_{sanitized_name} similarities analysis_{timestamp}{sample_suffix}.py"
    settings = QSettings()
    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        "Export similarities analysis as Python",
        similarities_export_default_path(settings, default_filename),
        "Python Files (*.py)",
    )
    if reactivate_callback is not None:
        QTimer.singleShot(0, reactivate_callback)
    if not file_path:
        return
    if not file_path.lower().endswith(".py"):
        file_path = f"{file_path}.py"
    remember_similarities_export_directory(settings, file_path)

    try:
        with open(file_path, "w", encoding="utf-8") as export_file:
            export_file.write(format_similarities_json_export_payload(payload))
    except Exception as exc:
        QMessageBox.critical(
            parent,
            "Export failed",
            f"Could not export similarities analysis as Python:\n{exc}",
        )
        return

    QMessageBox.information(
        parent,
        "Export complete",
        f"Saved similarities analysis Python file to:\n{file_path}",
    )
