from __future__ import annotations
from threading import Event
from ephemeraldaddy.io.web_profile.pacing import paced_requests
from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)
from ephemeraldaddy.io.geocode import geocode_location
from ephemeraldaddy.io.web_profile.csv_io import load_seeds, parse_pasted_names, export_failures
from ephemeraldaddy.io.web_profile.import_service import import_rows
from ephemeraldaddy.io.web_profile.lookup_service import WebProfileLookupService
from ephemeraldaddy.io.web_profile.models import ValidatedPlace

class _LookupWorker(QObject):
    result=Signal(object); progress=Signal(str); finished=Signal()
    def __init__(self, seeds):
        super().__init__()
        self.seeds = seeds
        self.cancel_event = Event()

    def cancel(self):
        self.cancel_event.set()

    @Slot()
    def run(self):
        try:
            service = WebProfileLookupService()
            with paced_requests(self.cancel_event):
                for index, seed in enumerate(self.seeds, 1):
                    if self.cancel_event.is_set():
                        break
                    self.progress.emit(f"Searching {index} / {len(self.seeds)} — {seed.name}")
                    row = service.lookup(seed)
                    if self.cancel_event.is_set():
                        break
                    self.result.emit(row)
        finally:
            self.finished.emit()

class BatchWebImportWindow(QWidget):
    def __init__(self,owner=None):
        super().__init__(owner); self.owner=owner; self.rows=[]; self.seeds=[]
        self.setWindowTitle("Batch Import"); self.resize(1200,650)
        layout=QVBoxLayout(self); self.names=QTextEdit(); self.names.setPlaceholderText("One public figure per line"); layout.addWidget(self.names)
        bar=QHBoxLayout(); layout.addLayout(bar)
        for label,handler in (("Load CSV",self.load_csv),("Look Up Names",self.lookup),("Validate all",self.validate_all),("Import Selected & Export CSV of Failures",self.do_import)):
            button=QPushButton(label); button.clicked.connect(handler); bar.addWidget(button)
        self.progress=QLabel("Ready"); layout.addWidget(self.progress)
        self.table=QTableWidget(0,8); self.table.setHorizontalHeaderLabels(("Include","Name","Birth Date","Birth Time","Birth Place","Sources","Bio Blurb","Errors")); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); layout.addWidget(self.table)
    def load_csv(self):
        path,_=QFileDialog.getOpenFileName(self,"Load CSV","","CSV (*.csv)")
        if path:
            with open(path,newline="",encoding="utf-8-sig") as stream: self.seeds=load_seeds(stream)
            self.names.setPlainText("\n".join(s.name for s in self.seeds))
    def lookup(self):
        if getattr(self, "worker", None) is not None:
            return
        seeds=self.seeds or parse_pasted_names(self.names.toPlainText())
        if not seeds: return
        self.rows=[]; self.table.setRowCount(0); self.lookup_thread=QThread(self); self.worker=_LookupWorker(seeds); self.worker.moveToThread(self.lookup_thread)
        self._close_pending = False
        self.lookup_thread.started.connect(self.worker.run)
        self.worker.result.connect(self.add_row)
        self.worker.progress.connect(self.progress.setText)
        self.worker.finished.connect(self.lookup_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.lookup_thread.finished.connect(self._lookup_finished)
        self.lookup_thread.start()

    @Slot()
    def _lookup_finished(self):
        self.worker = None
        self.lookup_thread.deleteLater()
        self.lookup_thread = None
        self.progress.setText("Lookup complete")
        if self._close_pending:
            self.close()
    @Slot(object)
    def add_row(self,row):
        self.rows.append(row); r=self.table.rowCount(); self.table.insertRow(r)
        values=("",row.name,row.birth_date,row.birth_time or "unknown",row.birth_place,"; ".join(row.sources),row.biography,row.error_text)
        for c,value in enumerate(values): self.table.setItem(r,c,QTableWidgetItem(value))
        self.table.item(r,0).setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable)
        self.table.item(r,0).setCheckState(Qt.Unchecked)
    def _sync(self):
        for i,row in enumerate(self.rows):
            row.name=self.table.item(i,1).text(); row.birth_date=self.table.item(i,2).text(); row.birth_time=self.table.item(i,3).text(); row.set_birth_place(self.table.item(i,4).text()); row.biography=self.table.item(i,6).text(); row.included=self.table.item(i,0).checkState()==Qt.Checked
    def validate_all(self):
        self._sync(); cache={}
        for i,row in enumerate(self.rows):
            row.clear_place_errors()
            key=" ".join(row.birth_place.lower().split())
            if not key:
                self.table.item(i,7).setText(row.error_text)
                continue
            try:
                if key not in cache:
                    cache[key] = geocode_location(row.birth_place)
                lat,lon,label=cache[key]; row.place=ValidatedPlace(label,lat,lon); row.birth_place=label; self.table.item(i,4).setText(label)
            except Exception as exc: row.blocking_errors.append(f"Birth place could not be resolved: {exc}")
            self.table.item(i,7).setText(row.error_text)
    def do_import(self):
        self._sync()
        for i,row in enumerate(self.rows):
            if row.included and not row.importable: row.included=False; self.table.item(i,0).setCheckState(Qt.Unchecked)
        uids,failed=import_rows(self.rows); refresh=getattr(self.owner,"_refresh_charts",None)
        if uids and callable(refresh): refresh(changed_uids=set(uids))
        failures=[r for r in self.rows if r.validation_errors() or r in failed]
        if failures:
            path,_=QFileDialog.getSaveFileName(self,"Export failures","batch-import-failures.csv","CSV (*.csv)")
            if path: export_failures(failures,path)
        QMessageBox.information(self,"Batch Import",f"Imported {len(uids)} chart(s).")
    def closeEvent(self, event):
        thread = getattr(self, "lookup_thread", None)
        if thread is not None and thread.isRunning():
            self._close_pending = True
            self.worker.cancel()
            self.progress.setText("Cancelling lookup…")
            event.ignore()
            return
        super().closeEvent(event)

def open_batch_import_window(owner):
    window=BatchWebImportWindow(owner); window.setAttribute(Qt.WA_DeleteOnClose,True); window.show(); window.raise_(); owner._batch_web_import_window=window; return window
