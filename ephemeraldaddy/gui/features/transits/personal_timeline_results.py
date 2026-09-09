"""Results window for life-event overlap against the active Personal Timeline filter."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.gui.features.transits.personal_timeline_analysis import (
    LifeEventAnchor,
    PersonalTimelineAnalysisResult,
    analyze_personal_timeline,
    load_life_event_json,
)


class _AnalysisWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        chart_uid: str,
        chart: Any,
        transit_windows: list[Any],
        events: list[LifeEventAnchor],
    ) -> None:
        super().__init__()
        self.chart_uid = chart_uid
        self.chart = chart
        self.transit_windows = transit_windows
        self.events = events

    def run(self) -> None:
        try:
            result = analyze_personal_timeline(
                self.chart_uid,
                self.chart,
                self.transit_windows,
                self.events,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(result)


class PersonalTimelineResultsWindow(QMainWindow):
    """Analyze Library of Ghosts-style event JSON against filtered transit windows."""

    def __init__(
        self,
        *,
        chart_uid: str,
        chart: Any,
        transit_windows: list[Any],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.Window)
        self.chart_uid = str(chart_uid).strip().upper()
        self.chart = chart
        self.transit_windows = list(transit_windows)
        self._thread: QThread | None = None
        self._worker: _AnalysisWorker | None = None
        self._event_source: Path | None = None
        self._result: PersonalTimelineAnalysisResult | None = None

        chart_name = str(getattr(chart, "name", "Unnamed chart") or "Unnamed chart")
        self.setWindowTitle(f"Personal Timeline Results — {chart_name}")
        self.resize(1040, 700)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.setCentralWidget(central)

        title = QLabel(f"Personal Timeline Results — {chart_name}", central)
        title_font = title.font()
        title_font.setPointSize(max(12, title_font.pointSize() + 3))
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        explanation = QLabel(
            f"This snapshot uses the {len(self.transit_windows):,} transit windows currently "
            "visible in Personal Timeline. Change the timeline filters and open Results again "
            "to compare a different candidate set.",
            central,
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        self.load_button = QPushButton("Load Library of Ghosts JSON…", central)
        self.load_button.clicked.connect(self._choose_event_json)
        layout.addWidget(self.load_button, alignment=Qt.AlignLeft)

        self.source_label = QLabel("No life-event JSON loaded.", central)
        self.source_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.source_label.setWordWrap(True)
        layout.addWidget(self.source_label)

        metrics = QWidget(central)
        metric_grid = QGridLayout(metrics)
        metric_grid.setContentsMargins(0, 0, 0, 0)
        labels = (
            ("Observed overlap", "observed"),
            ("Background exposure", "exposure"),
            ("Exact-hit proximity", "exact"),
            ("Random expectation", "random"),
            ("Overlap / exposure ratio", "lift"),
        )
        self.metric_values: dict[str, QLabel] = {}
        for row, (label, key) in enumerate(labels):
            name = QLabel(label + ":", metrics)
            value = QLabel("—", metrics)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            metric_grid.addWidget(name, row, 0)
            metric_grid.addWidget(value, row, 1)
            self.metric_values[key] = value
        metric_grid.setColumnStretch(1, 1)
        layout.addWidget(metrics)

        self.status_label = QLabel(
            "Load a media-free Library of Ghosts timeline JSON file to calculate hits.", central
        )
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar(central)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.table = QTableWidget(0, 6, central)
        self.table.setHorizontalHeaderLabels(
            ("Date", "Event", "Anchor", "Transit overlap", "Exact ±30d", "Matching transits")
        )
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

    def _choose_event_json(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Load Library of Ghosts timeline JSON",
            "",
            "JSON files (*.json);;All files (*)",
        )
        if not selected:
            return

        birth = getattr(self.chart, "dt", None)
        if not isinstance(birth, datetime.datetime) or birth.tzinfo is None:
            QMessageBox.warning(
                self,
                "Personal Timeline Results",
                "The selected chart does not have a timezone-aware birth datetime.",
            )
            return
        try:
            events = load_life_event_json(Path(selected), birth.tzinfo)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Could not load life-event JSON", str(exc))
            return

        self._event_source = Path(selected)
        self.source_label.setText(
            f"Life events: {self._event_source} · {len(events):,} dated event anchors"
        )
        self._start_analysis(events)

    def _start_analysis(self, events: list[LifeEventAnchor]) -> None:
        self.load_button.setEnabled(False)
        self.status_label.setText(
            "Calculating overlap, lifespan exposure, exact-hit proximity, and randomized expectation…"
        )
        self.progress_bar.setRange(0, 0)
        self.table.setRowCount(0)

        thread = QThread(self)
        worker = _AnalysisWorker(
            self.chart_uid,
            self.chart,
            list(self.transit_windows),
            list(events),
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._analysis_finished)
        worker.failed.connect(self._analysis_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(self._thread_finished)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _analysis_finished(self, result: object) -> None:
        if not isinstance(result, PersonalTimelineAnalysisResult):
            self._analysis_failed("The results worker returned an unexpected value.")
            return
        self._result = result
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.load_button.setEnabled(True)

        count = result.event_count
        self.metric_values["observed"].setText(
            f"{result.observed_hits:,}/{count:,} events ({result.observed_rate:.1%})"
        )
        self.metric_values["exposure"].setText(f"{result.background_exposure:.1%} of elapsed lifespan")
        self.metric_values["exact"].setText(
            f"{result.exact_proximity_hits:,}/{count:,} events within ±{result.exact_proximity_days} days"
        )
        self.metric_values["random"].setText(
            f"{result.random_expected_hits:.2f}/{count:,} mean hits across "
            f"{result.randomization_trials:,} date shuffles"
        )
        lift = result.lift_vs_background
        self.metric_values["lift"].setText("—" if lift is None else f"{lift:.2f}×")

        self.status_label.setText(
            f"Analyzed {count:,} dated event anchors from {result.analysis_start:%Y-%m-%d} "
            f"through {result.analysis_end:%Y-%m-%d} against the currently filtered transit set."
        )
        self._populate_event_results(result)

    def _analysis_failed(self, message: str) -> None:
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.load_button.setEnabled(True)
        self.status_label.setText(f"Could not calculate Personal Timeline Results: {message}")

    def _thread_finished(self) -> None:
        self._worker = None
        self._thread = None

    def _populate_event_results(self, result: PersonalTimelineAnalysisResult) -> None:
        self.table.setRowCount(len(result.events))
        for row, item in enumerate(result.events):
            event = item.event
            values = (
                event.display_date,
                event.name,
                f"{event.source_field} · {event.precision}",
                "Yes" if item.overlaps_transit else "No",
                "Yes" if item.exact_hit_nearby else "No",
                "; ".join(item.transit_labels) if item.transit_labels else "—",
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
