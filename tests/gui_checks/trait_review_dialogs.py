import copy
import threading
import time
from types import SimpleNamespace

import pytest
pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtGui import QValidator
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPlainTextEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget

from ephemeraldaddy.gui.settings.modules import trait_reviews as ui


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def dispose_dialogs(app):
    yield
    for widget in app.topLevelWidgets():
        if isinstance(widget, QDialog):
            thread = getattr(widget, "_thread", None)
            if thread is not None and thread.isRunning():
                thread.requestInterruption()
                deadline = time.monotonic() + 15
                while thread.isRunning() and time.monotonic() < deadline:
                    app.processEvents()
                    QTest.qWait(10)
            widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def wait_until(app, predicate):
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
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
        trait_profile={"sample_uids": ["A"], "antisample_uids": ["DELETED"]},
    )
    dialog.setStyleSheet("QLabel { color: #f5f5f5; font-size: 13px; }")
    dialog.show()
    finish_query(app, dialog)
    assert list(dialog.inputs) == ["A", "DELETED"]
    assert dialog.inputs["A"].text() == "4"
    assert dialog._labels["A"].text() == "🧚 Renamed chart"
    assert not dialog._labels["A"].font().italic()
    old = dialog._labels["DELETED"]
    assert old.font().italic()
    assert "#999999" in old.styleSheet()
    assert "font-style: italic" in old.styleSheet()
    assert old.text() == "👹 Former chart"
    assert "3.00 / 5" in dialog.average_label.text()
    dialog.reject()  # Escape uses the same save-on-close path.
    assert saved[0][1]["chart_uid"] == "DELETED"
    assert saved[0][0]["name"] == "Renamed chart"


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
    def help_label(text):
        label = QLabel(text)
        label.setWordWrap(True)
        return label

    owner._build_settings_help_label = help_label
    manager.populate_traits_settings_layout(owner, QVBoxLayout(owner))
    owner.resize(700, 560)
    owner.show()
    app.processEvents()
    # Both review buttons belong beside the other actions in the second row.
    expected = [owner._traits_edit_button, owner._traits_reassess_unavailable_button,
                owner._traits_description_button, owner._traits_rate_accuracy_button,
                owner._traits_astro_analysis_button]
    button_rows = []
    for index in range(owner.layout().count()):
        layout = owner.layout().itemAt(index).layout()
        if layout is not None:
            button_rows.append([layout.itemAt(i).widget() for i in range(layout.count())
                                if isinstance(layout.itemAt(i).widget(), QPushButton)])
    assert len(button_rows) == 2
    assert button_rows[1] == expected
    assert owner._traits_reassess_unavailable_button.text() == "♻️ unavailable traits"
    assert len({button.geometry().top() for button in expected}) == 1
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


def test_first_async_results_are_visible_and_inputs_stay_next_to_names(app, monkeypatch, tmp_path):
    from ephemeraldaddy.gui import ranking_panel_core as rankings
    from ephemeraldaddy.gui.features.charts import database_analytics as analytics

    import json
    from datetime import datetime, timezone
    from ephemeraldaddy.analysis import trait_prediction_index as runtime
    from ephemeraldaddy.core import db, prediction_norms as norms
    index = runtime.TraitPredictionIndex()
    monkeypatch.setattr(runtime, "_INDEX", index)
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "charts.db")
    paths = norms.PredictionNormPaths(tmp_path / "source.json", tmp_path / "norms.json", tmp_path / "personal.json", tmp_path / "extra.json")
    paths.official.write_text(json.dumps({"version": 1, "trait_baselines": {"name:t": {"db_average": 60.}}}))
    monkeypatch.setattr(norms, "default_norm_paths", lambda: paths)
    charts = {f"REVWUID0000{i:03d}": SimpleNamespace(chart_uid=f"REVWUID0000{i:03d}", name=f"Chart {i}", score=100 - i * .5, dt=datetime(1950 + i, 1, 1, tzinfo=timezone.utc), birthtime_unknown=False, positions={}, lat=0, lon=0) for i in range(41)}
    conn = db._get_conn()
    with conn:
        for uid, chart in charts.items():
            conn.execute("INSERT INTO charts(chart_uid,name,datetime_iso,lat,lon,created_at) VALUES(?,?,?,0,0,?)", (uid, chart.name, chart.dt.isoformat(), chart.dt.isoformat()))
    conn.close()
    monkeypatch.setattr(db, "load_charts_by_uids", lambda uids: {uid: charts[uid] for uid in uids})
    monkeypatch.setattr(runtime, "calculate_trait_likelihoods", lambda chart, items, **kwargs: {"T": chart.score})
    owner = rankings.RankingsPanelMixin()
    release = threading.Event()
    saved = []

    def query(progress, cancelled):
        release.wait(2)
        return owner.trait_accuracy_rankings(
            {"name": "T", "profile": {}}, progress, cancelled,
        )

    dialog = ui.RateAccuracyDialog(
        trait_name="T", entries=[], query=query, save=lambda entries: saved.append(copy.deepcopy(entries)),
        trait_profile={"sample_uids": ["REVWUID0000000"], "antisample_uids": ["REVWUID0000001"]},
    )
    dialog.show()
    app.processEvents()
    assert not dialog.inputs
    release.set()
    finish_query(app, dialog)
    wait_until(app, lambda: dialog._ready)
    app.processEvents()
    assert len(dialog.inputs) == 40
    assert all(field.isVisible() and field.width() == 38 for field in dialog.inputs.values())
    assert all(label.isVisible() for label in dialog._labels.values())
    field = dialog.inputs["REVWUID0000000"]
    label = dialog._labels["REVWUID0000000"]
    assert label.geometry().left() - (field.geometry().right() + 1) == 6
    assert label.alignment() & Qt.AlignLeft
    assert label.text() == "🧚 Chart 0"
    assert dialog._labels["REVWUID0000001"].text() == "👹 Chart 1"
    assert dialog._labels["REVWUID0000002"].text() == "Chart 2"
    scroll = dialog.findChild(QScrollArea)
    assert scroll.widget().height() >= dialog._rows_layout.minimumSize().height()
    assert scroll.verticalScrollBar().maximum() > 0
    assert not saved  # No close/reopen was needed to see the results.
    dialog.close()
    assert saved[0][0]["name"] == "Chart 0"  # Prefixes stay display-only.


def test_progress_is_throttled_and_never_completes_before_rows_arrive(app):
    progress_events = []
    completed = []

    def query(progress, cancelled):
        for index in range(10001):
            progress(index / 100.0)
        return [{"chart_uid": "A", "name": "Chart"}]

    worker = ui._AccuracyRankingWorker(query, [])
    worker.progress.connect(progress_events.append)
    worker.result_ready.connect(lambda rows, names: completed.append(rows))
    worker.run()
    assert len(progress_events) == 100
    assert max(progress_events) == 99
    assert completed[0][0]["chart_uid"] == "A"


def test_missing_sample_provenance_uses_question_mark(app):
    dialog = ui.RateAccuracyDialog(
        trait_name="Legacy", entries=[], query=lambda progress, cancelled: [{"chart_uid": "A", "name": "Chart"}],
        save=lambda entries: None,
    )
    dialog.show()
    finish_query(app, dialog)
    assert dialog._labels["A"].text() == "❓ Chart"
    dialog.close()


def test_repeated_query_success_and_failure_close_cleanly(app):
    for index in range(12):
        def query(progress, cancelled):
            if index % 2:
                raise ValueError("Stored norm unavailable")
            return [{"chart_uid": "A", "name": "Chart"}]

        dialog = ui.RateAccuracyDialog(trait_name="T", entries=[], query=query, save=lambda entries: None)
        dialog.show()
        finish_query(app, dialog)
        if index % 2:
            assert "Stored norm unavailable" in dialog.status_label.text()
        else:
            wait_until(app, lambda: dialog.inputs["A"].isVisible())
        dialog.close()
        assert dialog._thread.isFinished()
        dialog.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
