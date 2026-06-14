"""Batch total-chart export UI helpers for Database View."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QLabel,
    QMessageBox,
    QProgressBar,
    QVBoxLayout,
)

from ephemeraldaddy.core.loading_messages import LoadingMessageRotator

MAX_BATCH_EXPORT_CHARTS = 10
LARGE_BATCH_EXPORT_THRESHOLD = 5


def export_button_label(selected_count: int) -> str:
    if selected_count > 1:
        return f"Export {selected_count} Charts"
    return "Export chart"


class ChartExportProgressWidget(QFrame):
    """Floating vertical progress bar anchored near the lower-left corner."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("chart_export_progress_widget")
        self.setWindowFlags(Qt.Widget)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            "QFrame#chart_export_progress_widget {"
            " background: rgba(22, 18, 30, 230);"
            " border: 1px solid #8a2be2;"
            " border-radius: 8px;"
            "}"
            "QLabel { color: #f1e8ff; font-size: 10px; font-weight: 600; }"
            "QProgressBar { border: 1px solid #3f3f3f; border-radius: 4px; background: #101010; }"
            "QProgressBar::chunk { background-color: #8a2be2; border-radius: 3px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        label = QLabel("Chart Export\nProgress", self)
        label.setAlignment(Qt.AlignCenter)
        self.message_label = QLabel("Preparing export…", self)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setFixedWidth(140)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setOrientation(Qt.Vertical)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedSize(34, 150)
        layout.addWidget(label)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignHCenter)
        layout.addWidget(self.message_label)
        self.adjustSize()

    def anchor_to_parent(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        margin = 18
        x = margin
        y = max(margin, parent.height() - self.height() - margin)
        self.move(x, y)

    def set_fraction(self, completed: int, total: int) -> None:
        value = int((completed / max(total, 1)) * 100)
        self.progress_bar.setValue(value)

    def set_message(self, message: str) -> None:
        self.message_label.setText(message)
        self.adjustSize()
        self.anchor_to_parent()


def _show_loading_bar_hint(parent, progress_widget: ChartExportProgressWidget) -> QLabel:
    hint = QLabel(
        "◀ Here, check it out, I made a little loading bar so you can monitor progress.",
        parent,
    )
    hint.setObjectName("chart_export_progress_hint")
    hint.setAttribute(Qt.WA_StyledBackground, True)
    hint.setStyleSheet(
        "QLabel#chart_export_progress_hint {"
        " background: #f1e8ff; color: #2b163f; border: 1px solid #8a2be2;"
        " border-radius: 10px; padding: 8px 10px; font-weight: 600;"
        "}"
    )
    hint.adjustSize()
    progress_widget.anchor_to_parent()
    hint.move(progress_widget.x() + progress_widget.width() + 6, progress_widget.y() + 58)
    hint.show()
    QTimer.singleShot(6500, hint.deleteLater)
    return hint


def confirm_batch_export(parent, count: int) -> bool:
    if count > MAX_BATCH_EXPORT_CHARTS:
        QMessageBox.critical(
            parent,
            "Export charts",
            "For the love of all that’s holy, please select 10 or fewer charts to batch export.",
        )
        return False
    if count > LARGE_BATCH_EXPORT_THRESHOLD:
        box = QMessageBox(parent)
        box.setWindowTitle("Export charts")
        box.setText(f"Hey, I’m gonna export all {count} of these charts for you this time, but you gotta be patient…")
        cancel = box.addButton("Never mind. What was I thinking?", QMessageBox.RejectRole)
        ok = box.addButton("Cool", QMessageBox.AcceptRole)
        box.setDefaultButton(ok)
        box.exec()
        return box.clickedButton() is ok and box.clickedButton() is not cancel
    if count > 1:
        box = QMessageBox(parent)
        box.setWindowTitle("Export charts")
        box.setText(
            "I, EphemeralDaddy, will now work in the background to build and export charts, "
            "but it may take some time. Please don't close me (the app) until all charts are exported."
        )
        cancel = box.addButton("Just forget it, okay?", QMessageBox.RejectRole)
        ok = box.addButton("Yay", QMessageBox.AcceptRole)
        box.setDefaultButton(ok)
        box.exec()
        return box.clickedButton() is ok and box.clickedButton() is not cancel
    return True


def run_total_chart_export_flow(
    parent,
    chart_ids: Sequence[int],
    *,
    prompt_for_chart: Callable[[], int | None],
    load_chart: Callable[[int], object],
    sanitize_token: Callable[[str], str],
    write_export: Callable[[int, object, str, bool], None],
) -> None:
    chart_ids = list(chart_ids)
    if not chart_ids:
        chart_id = prompt_for_chart()
        if chart_id is None:
            return
        chart_ids = [chart_id]
    if len(chart_ids) == 1:
        _export_single(parent, chart_ids[0], load_chart, sanitize_token, write_export)
        return
    if not confirm_batch_export(parent, len(chart_ids)):
        return
    directory = QFileDialog.getExistingDirectory(parent, "Export Total Charts")
    if not directory:
        return
    progress = ChartExportProgressWidget(parent)
    loading_messages = LoadingMessageRotator(initial_message="Exporting charts…")
    progress.set_message(loading_messages.next())
    message_timer = QTimer(progress)
    message_timer.setInterval(3200)
    message_timer.timeout.connect(lambda: progress.set_message(loading_messages.next()))
    message_timer.start()
    progress.show()
    progress.anchor_to_parent()
    QApplication.processEvents()
    _show_loading_bar_hint(parent, progress)
    exported = 0
    try:
        for index, chart_id in enumerate(chart_ids, start=1):
            chart = load_chart(int(chart_id))
            name = (getattr(chart, "name", None) or "chart").strip() or "chart"
            path = Path(directory) / f"{sanitize_token(name)}-total-chart-export.md"
            path = _unique_path(path)
            write_export(int(chart_id), chart, str(path), True)
            exported = index
            progress.set_fraction(index, len(chart_ids))
            QApplication.processEvents()
    except Exception as exc:
        QMessageBox.critical(parent, "Export failed", f"Could not export total charts:\n{exc}")
        return
    finally:
        message_timer.stop()
        QTimer.singleShot(1200, progress.deleteLater)
    QMessageBox.information(parent, "Export complete", f"Saved {exported} total chart exports to:\n{directory}")


def _export_single(parent, chart_id, load_chart, sanitize_token, write_export) -> None:
    try:
        chart = load_chart(int(chart_id))
    except Exception as exc:
        QMessageBox.warning(parent, "Export chart", f"Unable to load selected chart.\n\n{exc}")
        return
    chart_name = (getattr(chart, "name", None) or "chart").strip() or "chart"
    default_filename = f"{sanitize_token(chart_name)}-total-chart-export.md"
    file_path, selected_filter = QFileDialog.getSaveFileName(
        parent,
        "Export Total Chart",
        default_filename,
        "Markdown Files (*.md);;Text Files (*.txt)",
    )
    if not file_path:
        return
    selected_extension = ".txt" if "*.txt" in selected_filter else ".md"
    if not file_path.lower().endswith((".md", ".txt")):
        file_path = f"{file_path}{selected_extension}"
    try:
        write_export(int(chart_id), chart, file_path, file_path.lower().endswith(".md"))
    except Exception as exc:
        QMessageBox.critical(parent, "Export failed", f"Could not export total chart:\n{exc}")
        return
    QMessageBox.information(parent, "Export complete", f"Saved total chart export to:\n{file_path}")


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    return path.with_name(f"{stem}-copy{suffix}")
