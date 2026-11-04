"""Trait accuracy review and blind astrological analysis dialogs."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from PySide6.QtCore import QObject, QRegularExpression, QThread, Qt, Signal, Slot
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QScrollArea, QVBoxLayout, QWidget,
)

from ephemeraldaddy.analysis.trait_reviews import (
    ACCURACY_LABELS, normalize_accuracy_rankings, perceived_accuracy,
)
from ephemeraldaddy.analysis.traits import _TRAIT_SCORE_CATEGORIES, _json_safe_trait_value
from ephemeraldaddy.core import db

RankingQuery = Callable[[Callable[[float], None], Callable[[], bool]], list[dict[str, Any]]]


class _AccuracyRankingWorker(QObject):
    finished = Signal(object, object)
    failed = Signal(str)
    progress = Signal(float)

    def __init__(self, query: RankingQuery, saved_entries: list[dict[str, Any]]) -> None:
        super().__init__()
        self._query = query
        self._saved_entries = saved_entries

    @Slot()
    def run(self) -> None:
        try:
            names = {
                uid: str(row["name"] or "Unnamed chart")
                for uid, row in db.load_chart_rows_for_uids(
                    entry["chart_uid"] for entry in self._saved_entries
                ).items()
            } if self._saved_entries else {}
            rows = self._query(self.progress.emit, QThread.currentThread().isInterruptionRequested)
            self.finished.emit(rows, names)
        except Exception as exc:
            self.failed.emit(str(exc))


class RateAccuracyDialog(QDialog):
    """Own one immutable review cohort and its editable one-digit ratings.

    The query callback is the existing Database View ranking boundary; this
    dialog never owns window attributes or analytical cache invalidation.
    """

    def __init__(
        self,
        *,
        trait_name: str,
        entries: list[dict[str, Any]],
        query: RankingQuery,
        save: Callable[[list[dict[str, Any]]], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Rate Accuracy — {trait_name}")
        self.resize(650, 740)
        self._entries = normalize_accuracy_rankings(entries)
        self._save = save
        self._ready = bool(self._entries)
        self._pending_result: int | None = None
        self._thread: QThread | None = None
        self._labels: dict[str, QLabel] = {}
        self.inputs: dict[str, QLineEdit] = {}
        layout = QVBoxLayout(self)
        help_label = QLabel(
            "Rate how well this trait fits each chart, or leave it blank. "
            "The average uses rated charts only. Closing this window saves your ratings.\n"
            "1 = useless · 2 = pretty inaccurate · 3 = mixed results · "
            "4 = mostly accurate · 5 = very accurate\n"
            "Gray italic names are saved predictions outside the current top 40."
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        self.status_label = QLabel("Loading the top 40 predictions above DB norm…")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.average_label = QLabel()
        layout.addWidget(self.average_label)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        rows_widget = QWidget()
        self._rows_layout = QVBoxLayout(rows_widget)
        self._rows_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(rows_widget)
        layout.addWidget(scroll, 1)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self.buttons.button(QDialogButtonBox.Close).setText("Close and Save")
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._render_entries()

        self._thread = QThread(self)
        self._worker = _AccuracyRankingWorker(query, self._entries)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._loaded, Qt.QueuedConnection)
        self._worker.failed.connect(self._failed, Qt.QueuedConnection)
        self._worker.progress.connect(self._progress, Qt.QueuedConnection)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread_finished)
        self._thread.start()

    def _render_entries(self) -> None:
        for entry in self._entries:
            uid = entry["chart_uid"]
            row = QHBoxLayout()
            label = QLabel(entry["name"] or "Unavailable chart")
            label.setTextFormat(Qt.PlainText)
            label.setWordWrap(True)
            row.addWidget(label, 1)
            field = QLineEdit()
            field.setAccessibleName(f"Accuracy rating for {label.text()}")
            field.setMaxLength(1)
            field.setValidator(QRegularExpressionValidator(QRegularExpression("[1-5]?"), field))
            field.setAlignment(Qt.AlignCenter)
            field.setFixedWidth(38)
            field.setToolTip("Enter 1–5, or clear to leave unrated")
            field.setText("" if entry["value"] is None else str(entry["value"]))
            field.textChanged.connect(lambda text, entry=entry: self._rating_changed(entry, text))
            row.addWidget(field)
            self._rows_layout.addLayout(row)
            self._labels[uid] = label
            self.inputs[uid] = field
        self._update_average()

    def _rating_changed(self, entry: dict[str, Any], text: str) -> None:
        entry["value"] = int(text) if text in {"1", "2", "3", "4", "5"} else None
        self._update_average()

    def _update_average(self) -> None:
        average = perceived_accuracy(self._entries)
        count = sum(entry["value"] is not None for entry in self._entries)
        if average is None:
            self.average_label.setText("Perceived accuracy: unrated")
        else:
            label = ACCURACY_LABELS[min(4, int(average + 0.5) - 1)]
            self.average_label.setText(f"Perceived accuracy: {average:.2f} / 5 — {label} ({count} rated)")

    @Slot(float)
    def _progress(self, percent: float) -> None:
        if self._pending_result is None:
            self.status_label.setText(f"Checking current top 40 predictions… {percent:.0f}%")

    @Slot(object, object)
    def _loaded(self, rows: list[dict[str, Any]], names: dict[str, str]) -> None:
        if self._pending_result is not None:
            return
        current_uids = {row["chart_uid"] for row in rows}
        if not self._entries:
            self._entries = normalize_accuracy_rankings(rows)
            self._render_entries()
        for entry in self._entries:
            uid = entry["chart_uid"]
            if uid in names:
                entry["name"] = names[uid]
                self._labels[uid].setText(names[uid])
            stale = uid not in current_uids
            label = self._labels[uid]
            font = label.font()
            font.setItalic(stale)
            label.setFont(font)
            if stale:
                # An explicit rule also overrides the appwide QWidget color.
                label.setStyleSheet("color: #999999; font-style: italic;")
                label.setToolTip("Prior prediction — no longer in the current top 40 above DB norm")
        self._ready = True
        self.status_label.setText(
            f"{len(self._entries)} saved predictions. Blank ratings are excluded from the average."
            if self._entries else "No charts currently score above DB norm for this trait."
        )

    @Slot(str)
    def _failed(self, message: str) -> None:
        self.status_label.setText(
            f"Could not compare current predictions: {message}\n"
            + ("Your saved chart ratings remain editable." if self._entries else "No ratings have been changed.")
        )

    @Slot()
    def _thread_finished(self) -> None:
        self._worker = None
        if self._pending_result is not None:
            self._finish_close(self._pending_result)

    def done(self, result: int) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._pending_result = result
            self._thread.requestInterruption()
            self.status_label.setText("Finishing the current chart before closing…")
            self.buttons.setEnabled(False)
            return
        self._finish_close(result)

    def _finish_close(self, result: int) -> None:
        if self._ready:
            try:
                self._save(self._entries)
            except Exception as exc:
                self._pending_result = None
                self.buttons.setEnabled(True)
                QMessageBox.warning(self, "Trait ratings could not be saved", str(exc))
                return
        super().done(result)


class AstroAnalysisDialog(QDialog):
    """Paragraph editor with factor evidence and no Trait label to bias analysis."""

    def __init__(self, profile: Mapping[str, Any], text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Astro Analysis")
        self.resize(720, 680)
        layout = QVBoxLayout(self)
        help_label = QLabel(
            "Describe what these astrological factors theoretically entail through the lens of astrology. "
            "Analyze the factors independently of the trait's name. Write in paragraphs."
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        factors = {key: value for key, value in profile.items() if key in _TRAIT_SCORE_CATEGORIES and value}
        evidence = QPlainTextEdit()
        evidence.setReadOnly(True)
        evidence.setPlainText(json.dumps(_json_safe_trait_value(factors), ensure_ascii=False, indent=2))
        evidence.setAccessibleName("Astrological factors")
        layout.addWidget(evidence, 1)
        self.editor = QPlainTextEdit()
        self.editor.setAccessibleName("Astrological analysis")
        self.editor.setPlaceholderText("Enter a blind astrological analysis…")
        self.editor.setPlainText(text)
        layout.addWidget(self.editor, 2)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
