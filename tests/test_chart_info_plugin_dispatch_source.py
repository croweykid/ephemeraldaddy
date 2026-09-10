from pathlib import Path


def test_generic_hook_dispatch_is_after_native_position_info_and_main_target_only():
    source = (
        Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py"
    ).read_text(encoding="utf-8")
    method = source.split("    def _handle_summary_info_click(", 1)[1].split(
        "    def _run_with_chart_info_output(", 1
    )[0]
    assert "targets_main_chart_info = target_info_widget is self.chart_info_output" in method
    dispatch_guard = method.rsplit("if targets_main_chart_info:", 1)[1]
    assert "chart_info_plugin_paragraphs(" in dispatch_guard
    assert method.index("self._show_position_info(body, sign, house_num)") < method.index(
        "chart_info_plugin_paragraphs("
    )


def test_app_uses_generic_plugin_ownership_and_python_upload_filter():
    source = (
        Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py"
    ).read_text(encoding="utf-8")
    assert "from ephemeraldaddy.analysis.plugins import (" in source
    generic_import = source.split("from ephemeraldaddy.analysis.plugins import (", 1)[1].split(")", 1)[0]
    for name in (
        "chart_info_plugin_paragraphs",
        "install_plugin_file",
        "installed_plugin_names",
        "recognized_plugin_names",
    ):
        assert name in generic_import
    assert "Plugin files (*.json *.py)" in source
