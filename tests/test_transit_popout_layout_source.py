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
    assert "default_index=0" in source
    assert "QSplitter(Qt.Horizontal)" in source
    assert "QSplitter(Qt.Vertical)" in source
    assert "chart_info_layout" in source


def test_theme_view_uses_clickable_per_theme_tabs_and_persistent_chart_info():
    source = (
        ROOT / "ephemeraldaddy/gui/features/transits/popout_windows.py"
    ).read_text(encoding="utf-8")

    assert "def _set_personal_theme_tabs" in source
    assert "def _set_global_theme_tabs" in source
    assert "QTabWidget()" in source
    assert '("past", "🌖Past")' in source
    assert '("present", "🌕Present")' in source
    assert '("future", "🌒Future")' in source
    assert "build_theme_aspect_table(" in source
    assert "row_activated=lambda entry" in source
    assert "def _show_theme_aspect_info" in source
    assert "chart_info_layout=transit_scaffold.chart_info_layout" in source


def test_theme_tabs_use_rich_row_selectable_tables_with_semantic_colors():
    source = (
        ROOT / "ephemeraldaddy/gui/features/transits/theme_table.py"
    ).read_text(encoding="utf-8")

    assert "QTableWidget(0, 3)" in source
    assert '("Aspect Name", "Aspect", "Date Range")' in source
    assert "QAbstractItemView.SelectRows" in source
    assert "table.cellClicked.connect(_activate)" in source
    assert "PLANET_COLORS.get(" in source
    assert "ASPECT_COLORS.get(" in source
    assert "RELATIVE_YEAR_COLORS[label]" in source
    assert "Qt.RichText" in source
    assert "TRANSIT_THEME_TABLE_STYLE" in source
    assert "table.setStyleSheet(TRANSIT_THEME_TABLE_STYLE)" in source


def test_global_theme_rows_preserve_actual_aspect_geometry():
    source = (
        ROOT / "ephemeraldaddy/gui/features/transits/popout_windows.py"
    ).read_text(encoding="utf-8")

    assert 'angle = float(aspect.get("angle", exact_angle))' in source
    assert 'delta = float(aspect.get("delta", angle - exact_angle))' in source
    assert 'float(entry.get("angle", definition.get("angle", 0.0)))' in source
    assert 'float(entry.get("delta", 0.0))' in source


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
    assert "if range_error:" in windows_source
    assert 'f"- Unavailable ({range_error})"' in windows_source
    assert 'lines.extend(["", _range_status_text()])' in windows_source
    assert "transit_location," in windows_source
    assert "transit_location=self._transit_location" in worker_source


def test_failed_chart_update_does_not_cancel_the_current_range_worker():
    source = (
        ROOT / "ephemeraldaddy/gui/features/transits/popout_windows.py"
    ).read_text(encoding="utf-8")
    update_handler = source.split("def _on_update_chart()", 1)[1].split(
        'popout_context["custom_click_handler"]', 1
    )[0]

    assert update_handler.index("recalculate_personal_transit(") < update_handler.index(
        "_arrest_transit_window_loads_for_update()"
    )
