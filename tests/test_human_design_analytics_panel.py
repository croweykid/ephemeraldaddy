from __future__ import annotations

from pathlib import Path


SOURCE_PATH = Path("ephemeraldaddy/gui/features/charts/human_design_analytics_panel.py")


def test_line_distribution_stars_profile_line_bars_from_profile() -> None:
    source = SOURCE_PATH.read_text()
    line_chart_start = source.index("    line_numbers = list(range(1, 7))")
    line_chart_end = source.index("    hd_line_chart_figure.subplots_adjust", line_chart_start)
    line_chart_block = source[line_chart_start:line_chart_end]

    assert "profile_line_numbers = _profile_line_numbers(hd_result.profile)" in line_chart_block
    assert "int(line_value) in profile_line_numbers" in line_chart_block
    assert "AnnotationBbox" in line_chart_block
    assert "hd_line_chart_ax.add_artist(star_artist)" in line_chart_block


def test_profile_line_parser_keeps_only_valid_hd_lines() -> None:
    source = SOURCE_PATH.read_text()
    parser_start = source.index("def _profile_line_numbers")
    parser_end = source.index("def _glowing_star_image", parser_start)
    parser_block = source[parser_start:parser_end]

    assert "profile_text.replace(\"-\", \"/\").split(\"/\")" in parser_block
    assert "line_number = int(raw_part)" in parser_block
    assert "if 1 <= line_number <= 6:" in parser_block
    assert "line_numbers.add(line_number)" in parser_block


def test_popout_right_panel_toggle_arrows_point_toward_action() -> None:
    source = SOURCE_PATH.read_text()
    expanded_start = source.index("    def _set_hd_analytics_expanded")
    expanded_end = source.index("    hd_analytics_toggle.toggled.connect", expanded_start)
    expanded_block = source[expanded_start:expanded_end]

    assert "hd_analytics_toggle.setArrowType(Qt.RightArrow)" in expanded_block.split("return", 1)[0]
    assert 'hd_analytics_toggle.setToolTip("Collapse HD analytics panel")' in expanded_block.split("return", 1)[0]
    assert "hd_analytics_toggle.setArrowType(Qt.LeftArrow)" in expanded_block.split("return", 1)[1]
    assert 'hd_analytics_toggle.setToolTip("Expand HD analytics panel")' in expanded_block.split("return", 1)[1]
