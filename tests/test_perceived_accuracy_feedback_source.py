import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / "ephemeraldaddy/gui/app.py").read_text()
FEATURE_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/chart_information/perceived_accuracy.py"
).read_text()
HD_PANEL_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/charts/human_design_analytics_panel.py"
).read_text()
CHART_SECTIONS_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/controllers/main_window.py"
).read_text()
CHART_VIEW_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
).read_text()


def test_chart_identity_sync_clears_only_between_persisted_uids():
    method = APP_SOURCE.split("def _set_current_chart_uid", 1)[1].split(
        "def _clear_current_chart_uid", 1
    )[0]
    assert "clear_property=previous_uid is not None" in method
    same_uid_guard = method.index(
        "if normalized_uid == previous_uid:"
    )
    refresh = method.index("refresh_perceived_accuracy_controls(")
    assert "return" in method[same_uid_guard:refresh]


def test_module_installer_traverses_semantically_keyed_descendants():
    installer = FEATURE_SOURCE.split("def install_chart_editor_module_controls", 1)[1]
    assert "owner.findChildren(QToolButton)" in installer
    assert 'candidate.property("collapsibleSemanticKey")' in installer
    assert "vars(owner)" not in installer


def test_chart_refresh_loads_one_payload_before_rendering_module_controls():
    batch_refresh = FEATURE_SOURCE.split("def _refresh_controls_batched", 1)[1].split(
        "def set_chart_information_control_mode", 1
    )[0]
    assert batch_refresh.count("load_perceived_accuracy(") == 1
    assert "control.refresh_from_payload(payload)" in batch_refresh
    refresh = FEATURE_SOURCE.split("def refresh_perceived_accuracy_controls", 1)[1].split(
        "def install_chart_editor_module_controls", 1
    )[0]
    assert "_refresh_controls_batched(" in refresh


def test_human_design_popout_installs_controls_after_building_local_headers():
    assert "chart_uid: Callable[[], str | None] | None = None" in HD_PANEL_SOURCE
    install_position = HD_PANEL_SOURCE.rindex("install_chart_editor_module_controls(")
    return_position = HD_PANEL_SOURCE.rindex("return hd_analytics_container")
    assert install_position < return_position


def test_chart_info_mode_routes_property_control_visibility():
    method = APP_SOURCE.split("def _set_chart_info_panel_mode", 1)[1].split(
        "def _prepare_chart_info_replacement", 1
    )[0]
    assert "set_chart_information_panel_mode(" in method
    mode_helper = FEATURE_SOURCE.split("def set_chart_information_control_mode", 1)[1].split(
        "def refresh_perceived_accuracy_controls", 1
    )[0]
    assert "control.retarget(None)" not in mode_helper
    assert "control.set_context_visible(False" in mode_helper


def test_standard_chart_analysis_headers_forward_stable_section_keys():
    factory = CHART_SECTIONS_SOURCE.split("def add_collapsible_section", 1)[1].split(
        "def add_section", 1
    )[0]
    assert "semantic_key=section_key" in factory
    for section_key in (
        "ocean",
        "enneagram",
        "dnd_statblock",
        "dnd_species",
        "dnd_class",
        "dnd_alignment",
        "hd_electrochemistry",
    ):
        assert f'section_key="{section_key}"' in CHART_VIEW_SOURCE


def test_every_subjective_metric_section_call_has_stable_module_key():
    tree = ast.parse(CHART_VIEW_SOURCE)
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_build_subjective_notes_metric_section"
    ]
    assert len(calls) == 4
    keys = {
        keyword.value.value
        for call in calls
        for keyword in call.keywords
        if keyword.arg == "module_key" and isinstance(keyword.value, ast.Constant)
    }
    assert keys == {"emoji_portrait", "typology", "perceived_alignment", "sexiness"}


def test_every_main_chart_information_renderer_retargets_feedback():
    tree = ast.parse(APP_SOURCE)
    required_renderers = {
        "_show_position_info",
        "_show_decan_info",
        "_show_nakshatra_info",
        "_show_planet_keyword_info",
        "_show_sign_keyword_info",
        "_show_element_keyword_info",
        "_show_aspect_keyword_info",
        "_show_mode_keyword_info",
        "_show_house_keyword_info",
        "_show_human_design_gate_line_info",
        "_show_human_design_property_info",
        "_show_human_design_center_info",
        "_show_human_design_channel_info",
        "_show_human_design_color_info",
        "_show_human_design_tone_info",
        "_show_human_design_base_info",
        "_show_human_design_line_info",
        "_show_species_info",
        "_show_dnd_class_info",
        "_show_dnd_statblock_info",
        "_show_aspect_info",
    }
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in required_renderers
    }
    assert functions.keys() == required_renderers
    for name, function in functions.items():
        assert any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_retarget_chart_information"
            for node in ast.walk(function)
        ), name


def test_aspect_renderer_forwards_placement_context_to_rating_target():
    method = APP_SOURCE.split("def _show_aspect_info", 1)[1].split(
        "def _build_aspect_line_segments", 1
    )[0]
    for field in ("sign1", "sign2", "house1", "house2"):
        assert f'"{field}": {field}' in method


def test_chart_information_replacement_does_not_clear_before_a_match():
    prepare = APP_SOURCE.split("def _prepare_chart_info_replacement", 1)[1].split(
        "def _retarget_chart_information", 1
    )[0]
    assert "self._retarget_chart_information({})" not in prepare
    click_handler = APP_SOURCE.split("def _handle_summary_info_click", 1)[1].split(
        "def _run_with_chart_info_output", 1
    )[0]
    early_dispatch = click_handler.split("species_entries =", 1)[0]
    assert "self._prepare_chart_info_replacement()" not in early_dispatch.split(
        "def retarget", 1
    )[0]
    retarget_helper = early_dispatch.split("def retarget", 1)[1]
    assert "self._prepare_chart_info_replacement()" in retarget_helper


def test_direct_chart_information_routes_prepare_then_retarget():
    for handler_name, next_name in (
        ("_on_chart_analysis_above_average_link_activated", "_update_chart_analysis_above_average_links"),
        ("_on_distinguishing_factor_link_activated", "_enneagram_prediction_adapter"),
    ):
        handler = APP_SOURCE.split(f"def {handler_name}", 1)[1].split(
            f"def {next_name}", 1
        )[0]
        assert "self._prepare_chart_info_replacement()" in handler
        assert "self._retarget_chart_information(" in handler
