from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py")
CONTROLLER_SOURCE = Path("ephemeraldaddy/gui/features/similarities/analysis/controller.py")
CALCULATIONS_SOURCE = Path(
    "ephemeraldaddy/gui/features/similarities/analysis/calculations.py"
)


def test_manage_charts_constructs_similarities_panel_through_canonical_controller():
    app_source = APP_SOURCE.read_text(encoding="utf-8")
    controller_source = CONTROLLER_SOURCE.read_text(encoding="utf-8")

    assert "def _build_similarities_analysis_panel_contents" not in app_source
    assert "def _build_similarities_analysis_panel(" not in app_source
    assert (
        "self.similarities_analysis_panel = self.similarities_controller.build_panel()"
        in app_source
    )
    assert "title = QLabel(\"Similarities Analysis\")" in controller_source
    assert "self.db_info_panel = DBInfoPanel()" in controller_source


def test_similarities_analysis_has_no_legacy_charts_package_owner():
    assert CONTROLLER_SOURCE.is_file()
    assert CALCULATIONS_SOURCE.is_file()
    assert not Path(
        "ephemeraldaddy/gui/features/charts/similarities_analysis.py"
    ).exists()
    assert not Path("ephemeraldaddy/gui/features/charts/similarities").exists()


def test_data_export_button_dispatches_through_cohort_aware_controller():
    controller_source = CONTROLLER_SOURCE.read_text(encoding="utf-8")
    build_panel = controller_source.split("def build_panel", 1)[1].split(
        "def set_panel_scroll", 1
    )[0]

    assert "json_export_button.clicked.connect(self.export_json)" in build_panel
    legacy_connection = (
        "json_export_button.clicked.connect("
        "self.host._export_similarities_analysis_json)"
    )
    assert legacy_connection not in build_panel


def test_similarities_chart_info_is_a_static_sibling_below_analysis_scroll():
    app_source = APP_SOURCE.read_text(encoding="utf-8")
    controller_source = CONTROLLER_SOURCE.read_text(encoding="utf-8")

    assert "build_left_rail(" in app_source
    assert '"similarities": self.similarities_left_rail' in app_source
    build_panel = controller_source.split("def build_panel", 1)[1].split(
        "def set_panel_scroll", 1
    )[0]
    assert "layout.addWidget(self.db_info_panel)" not in build_panel
    assert "rail_layout.addWidget(panel_scroll, 1)" in controller_source
    assert "rail_layout.addWidget(self.db_info_panel, 1)" in controller_source


def test_hd_similarity_targets_use_canonical_chart_info_renderers():
    controller_source = CONTROLLER_SOURCE.read_text(encoding="utf-8")

    assert '"_show_human_design_channel_info"' in controller_source
    assert '"_show_human_design_center_info"' in controller_source
    assert controller_source.count('"_show_human_design_property_info"') == 2
    assert 'target_key = normalized_target.casefold()' in controller_source
    assert 'label = normalized_target.split(":", 1)[1].strip()' in controller_source


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
