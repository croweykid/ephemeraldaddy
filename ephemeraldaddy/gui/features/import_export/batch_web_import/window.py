from __future__ import annotations

from threading import Event
from copy import deepcopy
from dataclasses import replace

from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt, QTimer, QSignalBlocker
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QInputDialog, QDialog,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from ephemeraldaddy.io.geocode import search_locations
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
    def __init__(self, seeds, *, indices=None):
        super().__init__()
        self.seeds = seeds
        self.indices = indices

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
                    self.result.emit(row if self.indices is None else (self.indices[index - 1], row))
        finally:
            self.finished.emit()


class _PlaceValidationWorker(_BatchWorker):
    def __init__(self, places, cache):
        super().__init__()
        self.places = places
        self.cache = dict(cache)

    @Slot()
    def run(self):
        # Unchosen candidates and failures are reused only during this pass.
        candidates, errors = {}, {}
        try:
            with paced_requests(self.cancel_event):
                for index, query in self.places:
                    if self.cancel_event.is_set():
                        break
                    self.progress.emit(f"Validating birth place {index + 1}")
                    key = _place_key(query)
                    if key in self.cache:
                        matches = [self.cache[key]]
                    else:
                        if key not in candidates and key not in errors:
                            try:
                                matches = [ValidatedPlace(label, lat, lon) for label, lat, lon
                                           in search_locations(query, limit=7, allow_online=True)]
                                if not matches:
                                    raise ValueError("No matches found")
                                candidates[key] = matches
                                if len(matches) == 1:
                                    self.cache[key] = matches[0]
                                    self.cache[_place_key(matches[0].label)] = matches[0]
                            except Exception as exc:
                                errors[key] = f"Birth place could not be resolved: {exc}"
                        matches = candidates.get(key, [])
                    if self.cancel_event.is_set():
                        break
                    self.result.emit((index, query, matches, errors.get(key, "")))
        finally:
            self.finished.emit()


class _ImportWorker(_BatchWorker):
    def __init__(self, rows):
        super().__init__()
        # Workers own snapshots; the window applies state changes on its thread.
        self.rows = [(index, deepcopy(row)) for index, row in rows]

    @Slot()
    def run(self):
        error = ""
        uids = []
        try:
            indices = {id(row): index for index, row in self.rows}
            uids, _ = import_rows(
                [row for _, row in self.rows], cancel_event=self.cancel_event,
                progress=self.progress.emit,
                on_result=lambda row: self.result.emit(("row", indices[id(row)], row)),
            )
        except Exception as exc:
            error = str(exc)
        finally:
            self.result.emit(("complete", uids, error))
            self.finished.emit()


class BatchWebImportWindow(QWidget):
    def __init__(self, owner=None):
        super().__init__(owner, Qt.Window)
        self.owner = owner
        self.rows = []
        self.seeds = []
        self._csv_edited_fields = {}
        self.worker = None
        self.worker_thread = None
        self._close_pending = False
        self._place_cache = {}
        self._busy = False
        self._place_choices = []
        self._place_dialog = None
        self._declined_places = set()
        self._import_summary = None
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
            ("Validate Selected Places", self.validate_selected),
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
        self.table.itemChanged.connect(self._table_item_changed)

    def _set_busy(self, busy):
        self._busy = busy
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
        if self.worker is not None and (not self._close_pending or isinstance(self.worker, _ImportWorker)):
            self._result_handler(result)

    @Slot()
    def _worker_finished(self):
        # finished can arrive while native thread cleanup is still running.
        # Join that cleanup before dropping the Python worker reference, so it
        # cannot race the worker's deferred QObject deletion on another thread.
        self.worker_thread.wait()
        was_import = isinstance(self.worker, _ImportWorker)
        self.worker = None
        self._result_handler = None
        self.worker_thread.deleteLater()
        self.worker_thread = None
        if was_import:
            self._finish_import()
        if self._place_choices and not self._close_pending:
            self._show_next_place_choice()
        else:
            self._finish_task()

    def _finish_task(self):
        self._set_busy(False)
        self.progress.setText(self._completion_text)
        if self._close_pending:
            QTimer.singleShot(0, self.close)

    def load_csv(self):
        if self._busy:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Load CSV", "", "CSV (*.csv)")
        if not path:
            return
        with open(path, newline="", encoding="utf-8-sig") as stream:
            seeds = load_seeds(stream)
        self.seeds = seeds
        self.names.setPlainText("\n".join(seed.name for seed in seeds))
        self.rows = []
        self._csv_edited_fields.clear()
        self.table.setRowCount(0)
        for seed in seeds:
            self.add_row(seed.to_row())
        self.progress.setText("CSV loaded; look up unresolved names, or edit and validate restored rows.")

    def lookup(self):
        if self._busy:
            return
        if self.seeds:
            self._sync()
            indices = [index for index, seed in enumerate(self.seeds)
                       if not seed.restored and self.rows[index].name.strip()
                       and self.rows[index].imported_uid is None]
            if not indices:
                self.progress.setText("Edit restored rows, then validate their birth places.")
                return
            # Query corrected names, then merge results with per-field repairs.
            self._start_worker(
                _LookupWorker([replace(self.seeds[index], name=self.rows[index].name)
                               for index in indices], indices=indices),
                self._apply_lookup_result, "Lookup complete",
            )
            return
        seeds = parse_pasted_names(self.names.toPlainText())
        if not seeds:
            return
        self.rows = []
        self.table.setRowCount(0)
        self._start_worker(_LookupWorker(seeds), self.add_row, "Lookup complete")

    def _apply_lookup_result(self, result):
        index, row = result
        previous = self.rows[index]
        fields = self._csv_edited_fields.get(index, set())
        for field in fields:
            setattr(row, field, deepcopy(getattr(previous, field)))
        if "birth_place" in fields:
            row.place = previous.place
        row.manually_repaired = previous.manually_repaired
        row.included = previous.included and row.importable
        self.rows[index] = row
        self._display_row(index, row)

    @Slot(object)
    def add_row(self, row):
        if self._close_pending:
            return
        self.rows.append(row)
        index = self.table.rowCount()
        with QSignalBlocker(self.table):
            self.table.insertRow(index)
        self._display_row(index, row)

    def _display_row(self, index, row):
        values = (
            "", row.name, row.birth_date, row.birth_time or "unknown", row.birth_place,
            "; ".join(row.sources), row.biography, row.error_text,
        )
        with QSignalBlocker(self.table):
            for column, value in enumerate(values):
                self.table.setItem(index, column, QTableWidgetItem(value))
            checkbox = self.table.item(index, 0)
            checkbox.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            checkbox.setCheckState(Qt.Checked if row.included and row.importable else Qt.Unchecked)
            self.table.item(index, 7).setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if row.imported_uid is not None:
                self._lock_imported_row(index)

    def _lock_imported_row(self, index):
        self.table.item(index, 0).setFlags(Qt.NoItemFlags)
        for column in range(1, 7):
            item = self.table.item(index, column)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)

    def _sync_row(self, index):
        row = self.rows[index]
        with QSignalBlocker(self.table):
            checkbox = self.table.item(index, 0)
            if row.imported_uid is None:
                row.set_birth_fields(*(self.table.item(index, column).text() for column in range(1, 5)))
                row.sources = [source.strip() for source in self.table.item(index, 5).text().split(";") if source.strip()]
                row.biography = self.table.item(index, 6).text()
            errors = row.validation_errors()
            row.included = checkbox.checkState() == Qt.Checked and not errors
            if not row.included:
                checkbox.setCheckState(Qt.Unchecked)
            self.table.item(index, 7).setText(row.error_text)
            checkbox.setToolTip(" ".join(errors))
        return errors

    def _sync(self):
        for index in range(len(self.rows)):
            self._sync_row(index)

    @Slot(QTableWidgetItem)
    def _table_item_changed(self, item):
        index, column = item.row(), item.column()
        if self._busy or index < 0 or index >= len(self.rows) or column < 0 or column > 6:
            return
        if self.seeds and column in range(1, 7):
            field = ("name", "birth_date", "birth_time", "birth_place", "sources", "biography")[column - 1]
            self._csv_edited_fields.setdefault(index, set()).add(field)
        was_checked = self.table.item(index, 0).checkState() == Qt.Checked
        errors = self._sync_row(index)
        if was_checked and errors:
            error = errors[0]
            field = next((label for prefix, label in (
                ("Name", "Name"), ("Birth date", "Birth Date"),
                ("Birth time", "Birth Time"), ("Birth place", "Birth Place"),
            ) if error.startswith(prefix)), None)
            if field:
                self.progress.setText(f"Please correct the {field} field before selecting. {error}")
            else:
                self.progress.setText(f"Please resolve this row before selecting. {error}")

    def validate_all(self):
        self._validate_places(range(len(self.rows)))

    def validate_selected(self):
        self._validate_places(index.row() for index in self.table.selectionModel().selectedRows())

    def _validate_places(self, indices):
        if self._busy:
            return
        self._sync()
        places = []
        self._place_choices = []
        self._declined_places = set()
        for index in indices:
            row = self.rows[index]
            if row.imported_uid is not None:
                continue
            row.clear_place_errors()
            self.table.item(index, 7).setText(row.error_text)
            places.append((index, row.birth_place))
        if places:
            self._start_worker(
                _PlaceValidationWorker(places, self._place_cache),
                self._apply_place_result, "Place validation complete",
            )

    @Slot(object)
    def _apply_place_result(self, result):
        index, query, matches, error = result
        if self._close_pending or index >= len(self.rows):
            return
        if self.table.item(index, 4).text().strip() != query:
            return
        if len(matches) > 1:
            self.rows[index].place = None
            self._place_choices.append((index, query, matches))
            self._sync_row(index)
        else:
            self._set_place_result(index, query, matches[0] if matches else None, error)

    def _set_place_result(self, index, query, place, error=""):
        row = self.rows[index]
        row.clear_place_errors()
        row.place = place
        if place is not None:
            self._place_cache[_place_key(query)] = place
            self._place_cache[_place_key(place.label)] = place
            row.birth_place = place.label
            with QSignalBlocker(self.table):
                self.table.item(index, 4).setText(place.label)
        elif error:
            row.blocking_errors.append(error)
        self._sync_row(index)

    def _show_next_place_choice(self):
        while self._place_choices and not self._close_pending:
            index, query, matches = self._place_choices.pop(0)
            if self.table.item(index, 4).text().strip() != query:
                continue
            key = _place_key(query)
            if key in self._place_cache:
                self._set_place_result(index, query, self._place_cache[key])
                continue
            if key in self._declined_places:
                self._set_place_result(index, query, None, "Birth place selection required.")
                continue
            self._current_place_choice = (index, query, matches)
            dialog = QInputDialog(self)
            dialog.setWindowTitle("Choose birth place")
            dialog.setLabelText(f"{self.rows[index].name}: choose a match for {query}")
            dialog.setComboBoxItems([
                f"{number}. {place.label} ({place.latitude:.5f}, {place.longitude:.5f})"
                for number, place in enumerate(matches, 1)
            ])
            dialog.setComboBoxEditable(False)
            self._place_dialog = dialog
            dialog.finished.connect(self._place_choice_finished)
            dialog.open()
            return
        self._finish_task()

    @Slot(int)
    def _place_choice_finished(self, outcome):
        dialog = self._place_dialog
        index, query, matches = self._current_place_choice
        self._place_dialog = None
        if not self._close_pending and self.table.item(index, 4).text().strip() == query:
            if outcome == QDialog.Accepted:
                choice = int(dialog.textValue().split(".", 1)[0]) - 1
                self._set_place_result(index, query, matches[choice])
            else:
                self._declined_places.add(_place_key(query))
                self._set_place_result(index, query, None, "Birth place selection required.")
        dialog.deleteLater()
        self._show_next_place_choice()

    def do_import(self):
        if self._busy:
            return
        self._sync()
        selected = []
        for index, row in enumerate(self.rows):
            if row.included and row.importable:
                selected.append((index, row))
            elif row.included:
                row.included = False
                self.table.item(index, 0).setCheckState(Qt.Unchecked)
        self._import_summary = None
        if selected:
            self._start_worker(_ImportWorker(selected), self._apply_import_result, "Import complete")
        else:
            self._import_summary = ([], "")
            self._finish_import()

    def _apply_import_result(self, result):
        if result[0] == "complete":
            self._import_summary = result[1:]
            return
        _, index, row = result
        self.rows[index] = row
        with QSignalBlocker(self.table):
            self.table.item(index, 0).setCheckState(Qt.Unchecked)
            if row.imported_uid is not None:
                self._lock_imported_row(index)
            self.table.item(index, 7).setText(row.error_text)

    def _finish_import(self):
        uids, error = self._import_summary or ([], "")
        refresh = getattr(self.owner, "_refresh_charts", None)
        if uids and callable(refresh):
            refresh(changed_uids=set(uids))
        if self._close_pending:
            return
        failures = [row for row in self.rows if row.imported_uid is None
                    and (row.validation_errors() or row.save_error)]
        if failures:
            path, _ = QFileDialog.getSaveFileName(self, "Export failures", "batch-import-failures.csv", "CSV (*.csv)")
            if path:
                export_failures(failures, path)
        if error:
            QMessageBox.warning(self, "Batch Import", f"Import stopped: {error}")
        else:
            QMessageBox.information(self, "Batch Import", f"Imported {len(uids)} chart(s).")

    def closeEvent(self, event):
        # Wait for the finished slot as well as the native thread: queued import
        # results must be applied before the window can be deleted.
        if self.worker_thread is not None:
            self._close_pending = True
            self.worker.cancel()
            self.progress.setText("Cancelling; waiting for the current operation…")
            event.ignore()
            return
        if self._place_dialog is not None:
            self._close_pending = True
            event.ignore()
            self._place_choices.clear()
            self._place_dialog.reject()
            return
        super().closeEvent(event)


def open_batch_import_window(owner):
    window = BatchWebImportWindow(owner)
    window.setAttribute(Qt.WA_DeleteOnClose, True)
    window.show()
    window.raise_()
    owner._batch_web_import_window = window
    return window
