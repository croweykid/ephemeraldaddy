"""Batch total-chart export UI helpers for Database View."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot
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
            "QProgressBar::chunk { background-color: #9933ff; border-radius: 3px; }"
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


class _ChartExportWorker(QObject):
    progress = Signal(int, int)
    failed = Signal(str)
    finished = Signal(int, str)

    def __init__(
        self,
        export_jobs: Sequence[tuple[int, str]],
        *,
        load_chart: Callable[[int], object],
        write_export: Callable[[int, object, str, bool], None],
    ) -> None:
        super().__init__()
        self._export_jobs = list(export_jobs)
        self._load_chart = load_chart
        self._write_export = write_export

    @Slot()
    def run(self) -> None:
        exported = 0
        total = len(self._export_jobs)
        try:
            for index, (chart_id, file_path) in enumerate(self._export_jobs, start=1):
                chart = self._load_chart(int(chart_id))
                self._write_export(int(chart_id), chart, file_path, file_path.lower().endswith(".md"))
                exported = index
                self.progress.emit(index, total)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        destination = str(Path(self._export_jobs[0][1]).parent) if self._export_jobs else ""
        self.finished.emit(exported, destination)


class _ChartExportUiBridge(QObject):
    """Relays worker signals through an object owned by the GUI thread."""

    progress = Signal(int, int)
    failed = Signal(str)
    finished = Signal(int, str)

    @Slot(int, int)
    def forward_progress(self, completed: int, total: int) -> None:
        self.progress.emit(completed, total)

    @Slot(str)
    def forward_failed(self, error: str) -> None:
        self.failed.emit(error)

    @Slot(int, str)
    def forward_finished(self, exported: int, destination: str) -> None:
        self.finished.emit(exported, destination)


def _create_export_progress(parent) -> tuple[ChartExportProgressWidget, QTimer]:
    progress = ChartExportProgressWidget(parent)
    loading_messages = LoadingMessageRotator(initial_message="Exporting charts…")
    progress.set_message(loading_messages.next())
    progress.set_fraction(0, 1)
    message_timer = QTimer(progress)

    def _rotate_loading_message() -> None:
        message = loading_messages.next()
        progress.set_message(message)
        message_timer.setInterval(loading_messages.display_interval_ms(message))

    message_timer.setInterval(loading_messages.display_interval_ms(progress.message_label.text()))
    message_timer.timeout.connect(_rotate_loading_message)
    message_timer.start()
    progress.show()
    progress.raise_()
    progress.anchor_to_parent()
    QApplication.processEvents()
    _show_loading_bar_hint(parent, progress)
    return progress, message_timer


def _start_background_export(
    parent,
    export_jobs: Sequence[tuple[int, str]],
    *,
    load_chart: Callable[[int], object],
    write_export: Callable[[int, object, str, bool], None],
    completion_message: Callable[[int, str], str],
    failure_message: Callable[[str], str],
    progress_state: tuple[ChartExportProgressWidget, QTimer] | None = None,
) -> None:
    if progress_state is None:
        progress, message_timer = _create_export_progress(parent)
    else:
        progress, message_timer = progress_state
        progress.set_fraction(0, max(len(export_jobs), 1))

    thread = QThread(parent)
    worker = _ChartExportWorker(export_jobs, load_chart=load_chart, write_export=write_export)
    ui_bridge = _ChartExportUiBridge(parent)
    worker.moveToThread(thread)

    def _cleanup_ui() -> None:
        message_timer.stop()
        QTimer.singleShot(1200, progress.deleteLater)

    def _release_export_state() -> None:
        active_exports = getattr(parent, "_chart_export_threads", [])
        for export_state in list(active_exports):
            if export_state[0] is thread:
                active_exports.remove(export_state)
                break

    def _on_progress(completed: int, total: int) -> None:
        progress.set_fraction(completed, total)
        progress.raise_()
        QApplication.processEvents()

    def _on_failed(error: str) -> None:
        _cleanup_ui()
        QMessageBox.critical(parent, "Export failed", failure_message(error))

    def _on_finished(exported: int, destination: str) -> None:
        progress.set_fraction(exported, max(len(export_jobs), 1))
        _cleanup_ui()
        QMessageBox.information(parent, "Export complete", completion_message(exported, destination))

    thread.started.connect(worker.run)
    worker.progress.connect(ui_bridge.forward_progress, Qt.QueuedConnection)
    worker.failed.connect(ui_bridge.forward_failed, Qt.QueuedConnection)
    worker.finished.connect(ui_bridge.forward_finished, Qt.QueuedConnection)
    worker.failed.connect(worker.deleteLater)
    worker.finished.connect(worker.deleteLater)
    worker.failed.connect(thread.quit)
    worker.finished.connect(thread.quit)
    thread.finished.connect(_release_export_state)
    thread.finished.connect(thread.deleteLater)
    ui_bridge.progress.connect(_on_progress)
    ui_bridge.failed.connect(_on_failed)
    ui_bridge.finished.connect(_on_finished)
    active_exports = getattr(parent, "_chart_export_threads", [])
    export_state = (thread, worker, ui_bridge)
    active_exports.append(export_state)
    parent._chart_export_threads = active_exports
    thread.start()


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
        box.addButton("Never mind. What was I thinking?", QMessageBox.RejectRole)
        ok = box.addButton("Cool", QMessageBox.AcceptRole)
        box.setDefaultButton(ok)
        box.exec()
        return box.buttonRole(box.clickedButton()) == QMessageBox.AcceptRole
    if count > 1:
        box = QMessageBox(parent)
        box.setWindowTitle("Export charts")
        box.setText(
            "I, EphemeralDaddy, will now work in the background to build and export charts, "
            "but it may take some time. Please don't close me (the app) until all charts are exported."
        )
        box.addButton("Just forget it, okay?", QMessageBox.RejectRole)
        ok = box.addButton("Yay", QMessageBox.AcceptRole)
        box.setDefaultButton(ok)
        box.exec()
        return box.buttonRole(box.clickedButton()) == QMessageBox.AcceptRole
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
    directory = _choose_batch_export_directory(parent)
    if not directory:
        return
    progress = ChartExportProgressWidget(parent)
    loading_messages = LoadingMessageRotator(initial_message="Exporting charts…")
    progress.set_message(loading_messages.next())
    progress.set_fraction(0, 1)
    message_timer = QTimer(progress)

    def _rotate_loading_message() -> None:
        message = loading_messages.next()
        progress.set_message(message)
        message_timer.setInterval(loading_messages.display_interval_ms(message))

    message_timer.setInterval(loading_messages.display_interval_ms(progress.message_label.text()))
    message_timer.timeout.connect(_rotate_loading_message)
    message_timer.start()
    progress.show()
    progress.raise_()
    progress.anchor_to_parent()
    QApplication.processEvents()
    _show_loading_bar_hint(parent, progress)
    export_jobs: list[tuple[int, str]] = []
    try:
        for chart_id in chart_ids:
            chart = load_chart(int(chart_id))
            name = (getattr(chart, "name", None) or "chart").strip() or "chart"
            path = _unique_path(Path(directory) / f"{sanitize_token(name)}-total-chart-export.md")
            export_jobs.append((int(chart_id), str(path)))
    except Exception as exc:
        message_timer.stop()
        progress.deleteLater()
        QMessageBox.critical(parent, "Export failed", f"Could not prepare total chart exports:\n{exc}")
        return
    _start_background_export(
        parent,
        export_jobs,
        load_chart=load_chart,
        write_export=write_export,
        completion_message=lambda exported, destination: f"Saved {exported} total chart exports to:\n{destination}",
        failure_message=lambda error: f"Could not export total charts:\n{error}",
        progress_state=(progress, message_timer),
    )


def _choose_batch_export_directory(parent) -> str:
    QApplication.processEvents()
    dialog = QFileDialog(parent, "Export Total Charts")
    dialog.setOption(QFileDialog.DontUseNativeDialog, True)
    dialog.setFileMode(QFileDialog.Directory)
    dialog.setOption(QFileDialog.ShowDirsOnly, True)
    dialog.setLabelText(QFileDialog.Accept, "Export here")
    if dialog.exec() != QFileDialog.Accepted:
        return ""
    selected = dialog.selectedFiles()
    return selected[0] if selected else ""


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
    _start_background_export(
        parent,
        [(int(chart_id), file_path)],
        load_chart=load_chart,
        write_export=write_export,
        completion_message=lambda _exported, _destination: f"Saved total chart export to:\n{file_path}",
        failure_message=lambda error: f"Could not export total chart:\n{error}",
    )


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
