import copy
import threading
import time

import pytest
pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QValidator
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from ephemeraldaddy.gui.settings.modules import trait_reviews as ui


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def dispose_dialogs(app):
    yield
    for widget in app.topLevelWidgets():
        if isinstance(widget, QDialog):
            widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def wait_until(app, predicate):
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(5)
    assert predicate()


def finish_query(app, dialog):
    wait_until(app, lambda: not dialog._thread.isRunning())
    app.processEvents()


def test_initial_cohort_validates_single_digits_and_saves_average_on_close(app):
    saved = []
    dialog = ui.RateAccuracyDialog(
        trait_name="Creative", entries=[],
        query=lambda progress, cancelled: [{"chart_uid": uid, "name": "Same name"} for uid in ("A", "B", "C")],
        save=lambda entries: saved.append(copy.deepcopy(entries)),
    )
    dialog.show()
    finish_query(app, dialog)
    assert list(dialog.inputs) == ["A", "B", "C"]
    field = dialog.inputs["A"]
    for bad in ("0", "6", "x", "-1", "12"):
        assert field.validator().validate(bad, len(bad))[0] == QValidator.Invalid
    field.setFocus()
    QTest.keyClicks(field, "0x6")
    assert field.text() == ""
    QTest.keyClicks(field, "5")
    dialog.inputs["B"].setText("2")
    assert "3.50 / 5" in dialog.average_label.text()
    assert "2 rated" in dialog.average_label.text()
    dialog.inputs["B"].clear()
    assert "5.00 / 5" in dialog.average_label.text()
    assert not saved
    dialog.close()
    assert [entry["value"] for entry in saved[0]] == [5, None, None]


def test_reopen_preserves_saved_uids_and_marks_only_former_predictions(app, monkeypatch):
    monkeypatch.setattr(ui.db, "load_chart_rows_for_uids", lambda uids: {"A": {"name": "Renamed chart"}})
    saved = []
    dialog = ui.RateAccuracyDialog(
        trait_name="T", entries=[
            {"chart_uid": "A", "name": "Old name", "value": 4},
            {"chart_uid": "DELETED", "name": "Former chart", "value": 2},
        ],
        query=lambda progress, cancelled: [{"chart_uid": "A", "name": "Renamed chart"}, {"chart_uid": "NEW", "name": "New chart"}],
        save=lambda entries: saved.append(copy.deepcopy(entries)),
    )
    dialog.setStyleSheet("QLabel { color: #f5f5f5; font-size: 13px; }")
    dialog.show()
    finish_query(app, dialog)
    assert list(dialog.inputs) == ["A", "DELETED"]
    assert dialog.inputs["A"].text() == "4"
    assert dialog._labels["A"].text() == "Renamed chart"
    assert not dialog._labels["A"].font().italic()
    old = dialog._labels["DELETED"]
    assert old.font().italic()
    assert "#999999" in old.styleSheet()
    assert "font-style: italic" in old.styleSheet()
    assert "3.00 / 5" in dialog.average_label.text()
    dialog.reject()  # Escape uses the same save-on-close path.
    assert saved[0][1]["chart_uid"] == "DELETED"


def test_saved_ratings_remain_editable_when_current_norm_is_unavailable(app, monkeypatch):
    monkeypatch.setattr(ui.db, "load_chart_rows_for_uids", lambda uids: {})
    saved = []

    def fail(progress, cancelled):
        raise ValueError("Stored DB norm unavailable")

    dialog = ui.RateAccuracyDialog(
        trait_name="T", entries=[{"chart_uid": "A", "name": "Saved chart", "value": 2}],
        query=fail, save=lambda entries: saved.append(copy.deepcopy(entries)),
    )
    finish_query(app, dialog)
    assert "Stored DB norm unavailable" in dialog.status_label.text()
    assert not dialog._labels["A"].font().italic()
    dialog.inputs["A"].setText("4")
    dialog.accept()
    assert saved[0][0]["value"] == 4


def test_close_during_query_cancels_without_saving_partial_initial_cohort(app):
    started = threading.Event()
    saved = []

    def query(progress, cancelled):
        started.set()
        while not cancelled():
            time.sleep(0.005)
        return [{"chart_uid": "PARTIAL", "name": "Partial"}]

    dialog = ui.RateAccuracyDialog(trait_name="T", entries=[], query=query, save=saved.append)
    dialog.show()
    wait_until(app, started.is_set)
    dialog.reject()
    finish_query(app, dialog)
    assert not dialog.isVisible()
    assert not saved


def test_save_failure_keeps_ratings_available_for_retry(app, monkeypatch):
    warnings = []
    monkeypatch.setattr(ui.QMessageBox, "warning", lambda *args: warnings.append(args))

    def fail(entries):
        raise OSError("disk full")

    dialog = ui.RateAccuracyDialog(
        trait_name="T", entries=[], query=lambda progress, cancelled: [{"chart_uid": "A", "name": "Chart"}], save=fail,
    )
    dialog.show()
    finish_query(app, dialog)
    dialog.inputs["A"].setText("3")
    dialog.reject()
    assert dialog.isVisible()
    assert dialog.inputs["A"].text() == "3"
    assert warnings
    dialog._save = lambda entries: None
    dialog.reject()


def test_astro_analysis_shows_factors_without_trait_label_and_preserves_paragraphs(app):
    text = "First paragraph.\n\nSecond paragraph."
    dialog = ui.AstroAnalysisDialog(
        {"name": "Secret trait", "description": "Biased description", "signs": {"Aries": 4}, "positions": {"Mars in H1": 6}},
        text,
    )
    assert dialog.editor.toPlainText() == text
    evidence = next(editor for editor in dialog.findChildren(QPlainTextEdit) if editor.isReadOnly())
    assert "Secret trait" not in evidence.toPlainText()
    assert "Biased description" not in evidence.toPlainText()
    assert "Mars in H1" in evidence.toPlainText()
    dialog.reject()
    assert dialog.result() == QDialog.Rejected


def test_trait_manager_review_buttons_work_for_bundled_traits(app, monkeypatch):
    from ephemeraldaddy.gui.features.settings import traits_manager as manager

    trait = {"name": "Default", "uid": "default-uid", "path": "/bundled/defaults.json",
             "bundled": True, "profile": {}, "color": "#cc99ff"}
    monkeypatch.setattr(manager, "list_traits", lambda: [trait])
    owner = QWidget()
    owner._build_settings_help_label = lambda text: QLabel(text)
    manager.populate_traits_settings_layout(owner, QVBoxLayout(owner))
    assert not owner._traits_rate_accuracy_button.isEnabled()
    owner._traits_list_widget.item(0).setSelected(True)
    assert owner._traits_rate_accuracy_button.isEnabled()
    assert owner._traits_astro_analysis_button.isEnabled()
    assert not owner._traits_edit_button.isEnabled()
    clicked = []
    monkeypatch.setattr(manager, "on_trait_rate_accuracy_clicked", lambda current: clicked.append("rate"))
    monkeypatch.setattr(manager, "on_trait_astro_analysis_clicked", lambda current: clicked.append("analysis"))
    owner._traits_rate_accuracy_button.click()
    owner._traits_astro_analysis_button.click()
    assert clicked == ["rate", "analysis"]
    owner.deleteLater()
