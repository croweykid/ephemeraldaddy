from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py")
CONTROLLER_SOURCE = Path("ephemeraldaddy/gui/features/charts/similarities/controller.py")


def test_manage_charts_delegates_similarities_panel_construction_to_controller():
    app_source = APP_SOURCE.read_text(encoding="utf-8")
    controller_source = CONTROLLER_SOURCE.read_text(encoding="utf-8")

    assert "def _build_similarities_analysis_panel_contents" not in app_source
    app_panel_method = app_source.split("def _build_similarities_analysis_panel", 1)[1].split(
        "def _set_similarities_db_info_panel_visible", 1
    )[0]
    assert "return self.similarities_controller.build_panel()" in app_panel_method
    assert "title = QLabel(\"Similarities Analysis\")" in controller_source
    assert "DBInfoPanel(panel)" in controller_source


def test_manage_charts_routes_similarity_state_lifecycle_through_controller():
    app_source = APP_SOURCE.read_text(encoding="utf-8")
    manage_charts_source = app_source.split("class ManageChartsDialog", 1)[1].split(
        "class MainWindow", 1
    )[0]

    direct_state_initializers = (
        "self._similarities_export_sections: list[",
        "self._similarities_pair_button: QPushButton | None = None",
        "self._similarities_chart_lookup: dict[str, int] = {}",
        "self._similarities_db_baseline_cache = SimilaritiesDbBaselineCache()",
    )
    for initializer in direct_state_initializers:
        assert initializer not in manage_charts_source

    assert "self.similarities_controller.set_export_sections(" in manage_charts_source
    assert "self.similarities_controller.set_chart_lookup(chart_lookup)" in manage_charts_source
    assert "self.similarities_controller.clear_db_baseline_cache()" in manage_charts_source


def test_use_this_checkbox_only_appears_for_nonempty_chart_input():
    controller_source = CONTROLLER_SOURCE.read_text(encoding="utf-8")

    assert "use_checkbox.setVisible(False)" in controller_source
    assert "has_chart_name = bool(text.strip())" in controller_source
    assert "checkbox.setChecked(False)" in controller_source
    assert "checkbox.setVisible(has_chart_name)" in controller_source
