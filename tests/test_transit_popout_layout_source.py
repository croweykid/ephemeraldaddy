from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_both_transit_popouts_use_shared_scaffolding():
    app_source = (ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    source = (
        ROOT / "ephemeraldaddy/gui/features/transits/popout_windows.py"
    ).read_text(encoding="utf-8")
    personal = source.split("def show_personal_transit_chart_popout", 1)[1].split(
        "def show_transit_chart_popout", 1
    )[0]
    global_transit = source.split("def show_transit_chart_popout", 1)[1].split(
        "\n    def ", 1
    )[0]

    assert "build_transit_popout_scaffold(layout)" in personal
    assert "build_transit_popout_scaffold(layout)" in global_transit
    assert "transit_scaffold.chart_drawing_layout.addWidget(canvas" in personal
    assert "transit_scaffold.chart_drawing_layout.addWidget(canvas" in global_transit
    assert "def _show_personal_transit_chart_popout" not in app_source
    assert "def _show_transit_chart_popout" not in app_source
    assert "TransitPopoutMixin" not in app_source
    assert "TransitPopoutController(self)" in app_source
    assert "class TransitPopoutHost(Protocol)" in source
    assert "class TransitPopoutController" in source
    assert "self.transit_popout_controller.show_transit_chart_popout(chart)" in app_source


def test_shared_scaffolding_owns_requested_tabs_and_defaults():
    source = (
        ROOT / "ephemeraldaddy/gui/features/transits/popout_layout.py"
    ).read_text(encoding="utf-8")

    assert '("Chart Drawing", "Aspects")' in source
    assert '("Table View", "Theme View")' in source
    assert "default_index=1" in source


def test_personal_range_runs_in_cancellable_worker_not_gui_thread():
    windows_source = (
        ROOT / "ephemeraldaddy/gui/features/transits/popout_windows.py"
    ).read_text(encoding="utf-8")
    worker_source = (
        ROOT / "ephemeraldaddy/gui/features/transits/range_worker.py"
    ).read_text(encoding="utf-8")

    assert "PersonalTransitRangeWorker(" in windows_source
    assert "worker.moveToThread(thread)" in windows_source
    assert "thread.requestInterruption()" in windows_source
    assert "cancelled=thread.isInterruptionRequested" in worker_source
    assert "summary_share_button.setEnabled(False)" in windows_source
    assert "elif range_error:" in windows_source
    assert 'f"- Unavailable ({range_error})"' in windows_source
