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


def test_chart_data_section_header_style_is_appwide_visible_width_overlay():
    assert "CHART_DATA_SECTION_HEADER_STYLE = {" in STYLE_SOURCE
    assert '"background_color": COLOR_BG_ELEVATED' in STYLE_SOURCE
    assert '"text_color": COLOR_TEXT_PRIMARY' in STYLE_SOURCE
    assert "def _normalized_chart_data_text" in CHART_DATA_OUTPUT_SOURCE
    assert "Blank legacy ASCII divider rows around appwide section headers without changing line maps." in CHART_DATA_OUTPUT_SOURCE
    assert 'normalized.append("")' in CHART_DATA_OUTPUT_SOURCE
    assert "def _paint_chart_data_section_headers" in CHART_DATA_OUTPUT_SOURCE
    assert "viewport_width = output_widget.viewport().width()" in CHART_DATA_OUTPUT_SOURCE
    assert "rect.setX(0)" in CHART_DATA_OUTPUT_SOURCE
    assert "rect.setWidth(viewport_width)" in CHART_DATA_OUTPUT_SOURCE
    assert "painter.drawText(rect, Qt.AlignCenter, text)" in CHART_DATA_OUTPUT_SOURCE


def test_chart_data_table_header_tokens_are_colored_without_bold():
    assert "self._table_header_format = QTextCharFormat()" in CHART_DATA_OUTPUT_SOURCE
    assert "self._table_header_format.setForeground(QColor(CHART_DATA_HIGHLIGHT_COLOR))" in CHART_DATA_OUTPUT_SOURCE
    assert "self._table_header_format.setFontWeight(QFont.Normal)" in CHART_DATA_OUTPUT_SOURCE
    assert "self._qt_len(header_token),\n                            self._table_header_format," in CHART_DATA_OUTPUT_SOURCE
    assert "if _is_chart_data_table_header_line(text):\n            self.setFormat(0, self._qt_len(text), self._table_header_format)" in CHART_DATA_OUTPUT_SOURCE
    assert "if _is_chart_data_table_header_line(text):\n            self.setFormat(0, self._qt_len(text), self._plain_bold_format)" not in CHART_DATA_OUTPUT_SOURCE


def test_chart_data_outputs_use_visual_only_whitespace_separators():
    assert "SEPARATOR_STYLE," in CHART_DATA_OUTPUT_SOURCE
    assert 'SEPARATOR_STYLE["character"]' in CHART_DATA_OUTPUT_SOURCE
    assert 'SEPARATOR_STYLE["color"]' in CHART_DATA_OUTPUT_SOURCE
    assert 'SEPARATOR_STYLE["minimum_space_run"]' in CHART_DATA_OUTPUT_SOURCE
    assert "def _qt_text_offset" in CHART_DATA_OUTPUT_SOURCE
    assert 'encode("utf-16-le")' in CHART_DATA_OUTPUT_SOURCE
    assert "block_position + _qt_text_offset(text, column)" in CHART_DATA_OUTPUT_SOURCE
    assert "def _paint_chart_data_separators" in CHART_DATA_OUTPUT_SOURCE
    assert "def _is_chart_data_table_header_line" in CHART_DATA_OUTPUT_SOURCE
    assert "if _is_chart_data_table_header_line(text):" in CHART_DATA_OUTPUT_SOURCE
    assert "block = block.next()" in CHART_DATA_OUTPUT_SOURCE
    assert "def paintEvent" in CHART_DATA_OUTPUT_SOURCE
    assert "(?<=\\S)" in CHART_DATA_OUTPUT_SOURCE
    assert "(?=\\S)" in CHART_DATA_OUTPUT_SOURCE


def test_human_design_chart_data_outputs_use_shared_table_widget():
    assert "summary_output = ChartDataTableOutput()" in APP_SOURCE
    assert "build_human_design_chart_data_output(" in APP_SOURCE
    assert "summary_output = ChartDataTableOutput(human_design_synastry_mode=True)" in HD_SYNASTRY_SOURCE
    assert "build_human_design_synastry_data_output(" in HD_SYNASTRY_SOURCE


def test_human_design_synastry_header_shows_electrochemistry_score_before_gate_note():
    score = HD_SYNASTRY_SOURCE.index("Electrochemistry Score:")
    shared_gate_note = HD_SYNASTRY_SOURCE.index("Shared gates are drawn as striped segments.")

    assert score < shared_gate_note


def test_chart_data_separator_skips_padded_table_headers():
    assert '"Body",' in CHART_DATA_OUTPUT_SOURCE
    assert '"Sign(s)",' in CHART_DATA_OUTPUT_SOURCE
    assert '"Nakshatra",' in CHART_DATA_OUTPUT_SOURCE
    assert '"G.L",' in CHART_DATA_OUTPUT_SOURCE
    assert 're.split(r"\\s{2,}", stripped)' in CHART_DATA_OUTPUT_SOURCE
    assert 'return all(token.strip() in known_header_tokens for token in header_tokens)' in CHART_DATA_OUTPUT_SOURCE
