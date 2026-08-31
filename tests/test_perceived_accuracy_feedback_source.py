from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / "ephemeraldaddy/gui/app.py").read_text()
FEATURE_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/chart_information/perceived_accuracy.py"
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
    refresh = FEATURE_SOURCE.split("def refresh_perceived_accuracy_controls", 1)[1].split(
        "def install_chart_editor_module_controls", 1
    )[0]
    assert refresh.count("load_perceived_accuracy(") == 1
    assert "control.refresh_from_payload(payload)" in refresh
