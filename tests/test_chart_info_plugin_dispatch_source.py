from pathlib import Path

from ephemeraldaddy.gui.features.chart_information import plugin_context


def test_generic_hook_dispatch_is_after_native_position_info_and_main_target_only():
    source = (
        Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py"
    ).read_text(encoding="utf-8")
    method = source.split("    def _handle_summary_info_click(", 1)[1].split(
        "    def _run_with_chart_info_output(", 1
    )[0]
    assert "targets_main_chart_info = target_info_widget is self.chart_info_output" in method
    dispatch_guard = method.rsplit("if targets_main_chart_info:", 1)[1]
    assert "position_plugin_paragraphs(" in dispatch_guard
    assert "append_plugin_paragraphs(self.chart_info_output, paragraphs)" in dispatch_guard
    assert method.index("self._show_position_info(body, sign, house_num)") < method.index(
        "position_plugin_paragraphs("
    )


def test_app_uses_generic_plugin_ownership_and_python_upload_filter():
    source = (
        Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py"
    ).read_text(encoding="utf-8")
    assert "from ephemeraldaddy.analysis.plugins import (" in source
    generic_import = source.split("from ephemeraldaddy.analysis.plugins import (", 1)[1].split(")", 1)[0]
    for name in (
        "install_plugin_file",
        "installed_plugin_names",
        "recognized_plugin_names",
    ):
        assert name in generic_import
    assert "from ephemeraldaddy.gui.features.chart_information.plugin_context import (" in source
    assert "from ephemeraldaddy.gui.features.chart_information.plugin_renderer import (" in source
    assert "Plugin files (*.json *.py)" in source


def test_position_context_is_built_without_a_window_or_qt(monkeypatch):
    captured = None

    def capture(context):
        nonlocal captured
        captured = context
        return [[{"text": "supplement"}]]

    monkeypatch.setattr(plugin_context, "chart_info_plugin_paragraphs", capture)
    result = plugin_context.position_plugin_paragraphs(
        body="Sun",
        sign="Aries",
        house_num=None,
        chart_positions={"Sun": 5.0, "Moon": 45.0},
        position_info_map={},
        sign_for_longitude=lambda longitude: "Aries" if longitude < 30 else "Taurus",
    )
    assert result == [[{"text": "supplement"}]]
    assert captured == {
        "target": "position",
        "body": "Sun",
        "sign": "Aries",
        "house_num": None,
        "chart_uses_houses": False,
        "chart_signs": {"Sun": "Aries", "Moon": "Taurus"},
        "chart_sign_options": {"Sun": ("Aries",), "Moon": ("Taurus",)},
    }


def test_position_context_ignores_missing_or_invalid_luminary_positions(monkeypatch):
    captured = None

    def capture(context):
        nonlocal captured
        captured = context
        return []

    monkeypatch.setattr(plugin_context, "chart_info_plugin_paragraphs", capture)
    plugin_context.position_plugin_paragraphs(
        body="Mars",
        sign="Gemini",
        house_num=3,
        chart_positions={"Sun": "invalid"},
        position_info_map={},
        sign_for_longitude=lambda longitude: "unused",
    )
    assert captured["chart_signs"] == {}
    assert captured["chart_sign_options"] == {}
    assert captured["chart_uses_houses"] is True


def test_position_context_preserves_all_uncertain_luminary_signs(monkeypatch):
    captured = None

    def capture(context):
        nonlocal captured
        captured = context
        return []

    monkeypatch.setattr(plugin_context, "chart_info_plugin_paragraphs", capture)
    plugin_context.position_plugin_paragraphs(
        body="Moon",
        sign="Cancer",
        house_num=None,
        chart_positions={"Sun": 15.0, "Moon": 75.0},
        position_info_map={
            10: [
                {"body": "Sun", "sign": "Aries", "icon_index": 12},
                {"body": "Sun", "sign": "Taurus", "icon_index": 34},
            ],
            11: [
                {"body": "Moon", "sign": "Gemini", "icon_index": 12},
                {"body": "Moon", "sign": "Cancer", "icon_index": 34},
            ],
        },
        sign_for_longitude=lambda longitude: "provisional",
    )
    assert captured["chart_signs"] == {"Sun": "Aries", "Moon": "Cancer"}
    assert captured["chart_sign_options"] == {
        "Sun": ("Aries", "Taurus"),
        "Moon": ("Cancer", "Gemini"),
    }
