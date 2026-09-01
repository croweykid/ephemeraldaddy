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


def test_chart_switch_clears_stale_chart_information_target():
    method = APP_SOURCE.split("def _set_current_chart_uid", 1)[1].split(
        "def _clear_current_chart_uid", 1
    )[0]
    assert "refresh_perceived_accuracy_controls(self, clear_property=True)" in method


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
