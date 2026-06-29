from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STYLE_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text(encoding="utf-8")
CHART_DATA_OUTPUT_SOURCE = (
    REPO_ROOT / "ephemeraldaddy/gui/features/charts/chart_data_output.py"
).read_text(encoding="utf-8")


def test_chart_data_separator_style_is_appwide_style_constant():
    assert "SEPARATOR_STYLE = {" in STYLE_SOURCE
    assert '"color": "#555555"' in STYLE_SOURCE
    assert '"minimum_space_run": 2' in STYLE_SOURCE


def test_chart_data_outputs_use_visual_only_whitespace_separators():
    assert "SEPARATOR_STYLE," in CHART_DATA_OUTPUT_SOURCE
    assert '"ShowTabsAndSpaces"' in CHART_DATA_OUTPUT_SOURCE
    assert "def _apply_separator_style" in CHART_DATA_OUTPUT_SOURCE
    assert "(?<=\\S)" in CHART_DATA_OUTPUT_SOURCE
    assert "(?=\\S)" in CHART_DATA_OUTPUT_SOURCE
