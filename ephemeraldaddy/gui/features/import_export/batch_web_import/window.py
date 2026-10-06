from __future__ import annotations

from threading import Event

from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from ephemeraldaddy.io.geocode import geocode_location
from ephemeraldaddy.io.web_profile.csv_io import load_seeds, parse_pasted_names, export_failures
from ephemeraldaddy.io.web_profile.import_service import import_rows
from ephemeraldaddy.io.web_profile.lookup_service import WebProfileLookupService
from ephemeraldaddy.io.web_profile.models import ValidatedPlace
from ephemeraldaddy.io.web_profile.pacing import paced_requests


def _place_key(value):
    return " ".join(value.casefold().split())


class _BatchWorker(QObject):
    result = Signal(object)
    progress = Signal(str)
    finished = Signal()

    def __init__(self):
        super().__init__()
        self.cancel_event = Event()

    def cancel(self):
        self.cancel_event.set()


class _LookupWorker(_BatchWorker):
    def __init__(self, seeds):
        super().__init__()
        self.seeds = seeds

    @Slot()
    def run(self):
        try:
            service = None
            with paced_requests(self.cancel_event):
                for index, seed in enumerate(self.seeds, 1):
                    if self.cancel_event.is_set():
                        break
                    self.progress.emit(f"Searching {index} / {len(self.seeds)} — {seed.name}")
                    if seed.restored:
                        row = seed.to_row()
                    else:
                        if service is None:
                            service = WebProfileLookupService()
                        row = service.lookup(seed)
                    if self.cancel_event.is_set():
                        break
                    self.result.emit(row)
        finally:
            self.finished.emit()


class _PlaceValidationWorker(_BatchWorker):
    def __init__(self, places, cache):
        super().__init__()
        self.places = places
        self.cache = dict(cache)

    @Slot()
    def run(self):
        # Failures are reused only during this pass, so a later retry can recover.
        errors = {}
        try:
            for index, query in self.places:
                if self.cancel_event.is_set():
                    break
                self.progress.emit(f"Validating birth place {index + 1} / {len(self.places)}")
                key = _place_key(query)
                place = self.cache.get(key)
                error = errors.get(key, "")
                if key and place is None and not error:
                    try:
                        lat, lon, label = geocode_location(query)
                        place = ValidatedPlace(label, lat, lon)
                        self.cache[key] = place
                        self.cache[_place_key(label)] = place
                    except Exception as exc:
                        error = f"Birth place could not be resolved: {exc}"
                        errors[key] = error
                if self.cancel_event.is_set():
                    break
                self.result.emit((index, query, place, error))
        finally:
            self.finished.emit()


class BatchWebImportWindow(QWidget):
    def __init__(self, owner=None):
        super().__init__(owner, Qt.Window)
        self.owner = owner
        self.rows = []
        self.seeds = []
        self.worker = None
        self.worker_thread = None
        self._close_pending = False
        self._place_cache = {}
        self.setWindowTitle("Batch Import")
        self.resize(1200, 650)
        layout = QVBoxLayout(self)
        self.names = QTextEdit()
        self.names.setPlaceholderText("One public figure per line")
        layout.addWidget(self.names)
        bar = QHBoxLayout()
        layout.addLayout(bar)
        self._action_buttons = []
        for label, handler in (
            ("Load CSV", self.load_csv), ("Look Up Names", self.lookup),
            ("Validate all", self.validate_all),
            ("Import Selected & Export CSV of Failures", self.do_import),
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            bar.addWidget(button)
            self._action_buttons.append(button)
        self.progress = QLabel("Ready")
        layout.addWidget(self.progress)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels((
            "Include", "Name", "Birth Date", "Birth Time", "Birth Place",
            "Sources", "Bio Blurb", "Errors",
        ))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.table)

    def _set_busy(self, busy):
        for button in self._action_buttons:
            button.setEnabled(not busy)
        self.names.setReadOnly(busy)
        self.table.setEnabled(not busy)

    def _start_worker(self, worker, result_handler, completion_text):
        self._result_handler = result_handler
        self._completion_text = completion_text
        self._close_pending = False
        self.worker = worker
        self.worker_thread = QThread(self)
        worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(worker.run)
        # A window-owned Qt slot keeps Python callbacks on the GUI thread.
        worker.result.connect(self._dispatch_worker_result, Qt.QueuedConnection)
        worker.progress.connect(self.progress.setText)
        worker.finished.connect(self.worker_thread.quit)
        worker.finished.connect(worker.deleteLater)
        self.worker_thread.finished.connect(self._worker_finished)
        self._set_busy(True)
        self.worker_thread.start()

    @Slot(object)
    def _dispatch_worker_result(self, result):
        if self.worker is not None and not self._close_pending:
            self._result_handler(result)

    @Slot()
    def _worker_finished(self):
        self.worker = None
        self._result_handler = None
        self.worker_thread.deleteLater()
        self.worker_thread = None
        self._set_busy(False)
        self.progress.setText(self._completion_text)
        if self._close_pending:
            self.close()

    def load_csv(self):
        if self.worker is not None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Load CSV", "", "CSV (*.csv)")
        if not path:
            return
        with open(path, newline="", encoding="utf-8-sig") as stream:
            seeds = load_seeds(stream)
        self.seeds = seeds
        self.names.setPlainText("\n".join(seed.name for seed in seeds))
        self.rows = []
        self.table.setRowCount(0)
        for seed in seeds:
            if seed.restored:
                self.add_row(seed.to_row())
        self.progress.setText("CSV loaded; restored rows can be edited and validated.")

    def lookup(self):
        if self.worker is not None:
            return
        # Repair CSVs are already resolved input: do not overwrite manual edits.
        if self.seeds and all(seed.restored for seed in self.seeds):
            self.progress.setText("Edit restored rows, then validate their birth places.")
            return
        seeds = self.seeds or parse_pasted_names(self.names.toPlainText())
        if not seeds:
            return
        self.rows = []
        self.table.setRowCount(0)
        self._start_worker(_LookupWorker(seeds), self.add_row, "Lookup complete")

    @Slot(object)
    def add_row(self, row):
        if self._close_pending:
            return
        self.rows.append(row)
        index = self.table.rowCount()
        self.table.insertRow(index)
        values = (
            "", row.name, row.birth_date, row.birth_time or "unknown", row.birth_place,
            "; ".join(row.sources), row.biography, row.error_text,
        )
        for column, value in enumerate(values):
            self.table.setItem(index, column, QTableWidgetItem(value))
        self.table.item(index, 0).setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        self.table.item(index, 0).setCheckState(Qt.Unchecked)

    def _sync(self):
        for index, row in enumerate(self.rows):
            row.name = self.table.item(index, 1).text()
            row.birth_date = self.table.item(index, 2).text()
            row.birth_time = self.table.item(index, 3).text()
            row.set_birth_place(self.table.item(index, 4).text())
            row.sources = [source.strip() for source in self.table.item(index, 5).text().split(";") if source.strip()]
            row.biography = self.table.item(index, 6).text()
            row.included = self.table.item(index, 0).checkState() == Qt.Checked

    def validate_all(self):
        if self.worker is not None or not self.rows:
            return
        self._sync()
        places = []
        for index, row in enumerate(self.rows):
            row.clear_place_errors()
            self.table.item(index, 7).setText(row.error_text)
            places.append((index, row.birth_place))
        self._start_worker(
            _PlaceValidationWorker(places, self._place_cache),
            self._apply_place_result, "Place validation complete",
        )

    @Slot(object)
    def _apply_place_result(self, result):
        index, query, place, error = result
        if place is not None:
            self._place_cache[_place_key(query)] = place
            self._place_cache[_place_key(place.label)] = place
        if self._close_pending or index >= len(self.rows):
            return
        # Ignore stale results if a caller changed the table programmatically.
        if self.table.item(index, 4).text().strip() != query:
            return
        row = self.rows[index]
        row.clear_place_errors()
        if place is not None:
            row.place = place
            row.birth_place = place.label
            self.table.item(index, 4).setText(place.label)
        elif error:
            row.place = None
            row.blocking_errors.append(error)
        self.table.item(index, 7).setText(row.error_text)

    def do_import(self):
        if self.worker is not None:
            return
        self._sync()
        for index, row in enumerate(self.rows):
            if row.included and not row.importable:
                row.included = False
                self.table.item(index, 0).setCheckState(Qt.Unchecked)
        uids, failed = import_rows(self.rows)
        refresh = getattr(self.owner, "_refresh_charts", None)
        if uids and callable(refresh):
            refresh(changed_uids=set(uids))
        failures = [row for row in self.rows if row.validation_errors() or row in failed]
        if failures:
            path, _ = QFileDialog.getSaveFileName(self, "Export failures", "batch-import-failures.csv", "CSV (*.csv)")
            if path:
                export_failures(failures, path)
        QMessageBox.information(self, "Batch Import", f"Imported {len(uids)} chart(s).")

    def closeEvent(self, event):
        if self.worker_thread is not None and self.worker_thread.isRunning():
            self._close_pending = True
            self.worker.cancel()
            self.progress.setText("Cancelling lookup…")
            event.ignore()
            return
        super().closeEvent(event)


def open_batch_import_window(owner):
    window = BatchWebImportWindow(owner)
    window.setAttribute(Qt.WA_DeleteOnClose, True)
    window.show()
    window.raise_()
    owner._batch_web_import_window = window
    return window
