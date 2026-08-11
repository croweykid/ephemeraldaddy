from pathlib import Path


SOURCE = Path(
    "ephemeraldaddy/gui/features/charts/time_sensitivity_panel.py"
).read_text(encoding="utf-8")


def test_fine_tune_controls_appear_only_after_a_broad_result():
    assert 'self.fine_tune_module.hide()' in SOURCE
    assert 'self._set_fine_tune_available(saved)' in SOURCE
    assert 'self._set_fine_tune_available(self._last_result)' in SOURCE
    assert 'self.fine_tune_module.setVisible(available)' in SOURCE
    assert 'fine_tune_calculation_signature(chart)' in SOURCE
    assert 'refresh_key = (chart_uid, date_key, config_items, calculation_signature)' in SOURCE


def test_fine_tune_panel_uses_chart_editor_controller_and_requested_options():
    assert 'FineTuneHourlyScanController(parent=self)' in SOURCE
    assert 'title="Fine Tune Hourly Scan"' in SOURCE
    assert 'self.fine_tune_mode_combo.addItem("Fine Tune Hourly Scan", None)' not in SOURCE
    assert 'self.fine_tune_mode_combo.addItem("5-minute steps", 5)' in SOURCE
    assert 'self.fine_tune_mode_combo.addItem("1-minute steps", 1)' in SOURCE
    assert 'self._fine_tune_controller.invalidate()' in SOURCE


def test_fine_tune_controls_are_a_collapsed_section_below_summary():
    assert 'self.fine_tune_toggle' in SOURCE
    assert 'expanded=False' in SOURCE
    assert 'self._charts_layout.insertWidget(1, self.fine_tune_module)' in SOURCE


def test_fine_tune_output_is_inserted_above_broad_detail_sections():
    assert '"fine_tune_hourly"' in SOURCE
    assert 'format_fine_tune_hourly_scan_html(result)' in SOURCE
    assert 'position=2' in SOURCE


def test_pure_package_does_not_reexport_qt_controller():
    package_source = Path(
        "ephemeraldaddy/gui/features/chart_editor/time_sensitivity/__init__.py"
    ).read_text(encoding="utf-8")
    assert "from .controller import" not in package_source
    assert "from .formatting import" not in package_source
