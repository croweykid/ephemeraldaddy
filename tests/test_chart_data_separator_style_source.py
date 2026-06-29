from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STYLE_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text(encoding="utf-8")
CHART_DATA_OUTPUT_SOURCE = (
    REPO_ROOT / "ephemeraldaddy/gui/features/charts/chart_data_output.py"
).read_text(encoding="utf-8")
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
HD_SYNASTRY_SOURCE = (
    REPO_ROOT / "ephemeraldaddy/gui/features/charts/human_design_synastry_window.py"
).read_text(encoding="utf-8")


def test_chart_data_separator_style_is_appwide_style_constant():
    assert "SEPARATOR_STYLE = {" in STYLE_SOURCE
    assert '"character": "."' in STYLE_SOURCE
    assert '"color": "#555555"' in STYLE_SOURCE
    assert '"minimum_space_run": 2' in STYLE_SOURCE


def test_chart_data_outputs_use_visual_only_whitespace_separators():
    assert "SEPARATOR_STYLE," in CHART_DATA_OUTPUT_SOURCE
    assert 'SEPARATOR_STYLE["character"]' in CHART_DATA_OUTPUT_SOURCE
    assert 'SEPARATOR_STYLE["color"]' in CHART_DATA_OUTPUT_SOURCE
    assert 'SEPARATOR_STYLE["minimum_space_run"]' in CHART_DATA_OUTPUT_SOURCE
    assert "def _paint_chart_data_separators" in CHART_DATA_OUTPUT_SOURCE
    assert "def paintEvent" in CHART_DATA_OUTPUT_SOURCE
    assert "(?<=\\S)" in CHART_DATA_OUTPUT_SOURCE
    assert "(?=\\S)" in CHART_DATA_OUTPUT_SOURCE


def test_human_design_chart_data_outputs_use_shared_table_widget():
    assert "summary_output = ChartDataTableOutput()" in APP_SOURCE
    assert "build_human_design_chart_data_output(" in APP_SOURCE
    assert "summary_output = ChartDataTableOutput(human_design_synastry_mode=True)" in HD_SYNASTRY_SOURCE
    assert "build_human_design_synastry_data_output(" in HD_SYNASTRY_SOURCE
