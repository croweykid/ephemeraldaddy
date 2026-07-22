from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_popout_chart_data_header_aligns_with_chart_info_title():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    method_start = source.index("    def on_popout_chart")
    method = source[method_start : source.index("    def on_get_human_design_info", method_start)]

    assert "Keep the Chart Data Output header row aligned" in method
    assert "summary_controls.setContentsMargins(0, 0, 0, 0)" in method
    assert "chart_data_header.setLayout(summary_controls)" in method
    assert "chart_data_header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)" in method
    assert "right_layout.addWidget(chart_data_header, 0)" in method
    assert "right_layout.addLayout(summary_controls)" not in method


def test_popout_chart_info_label_sits_immediately_above_info_panel():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/aspect_weight_graphs.py").read_text()
    label_index = source.index('chart_info_label = QLabel("Chart Info!")')
    output_index = source.index("chart_info_output = QPlainTextEdit()", label_index)

    assert label_index < output_index
    assert "left_panel_layout.addWidget(chart_info_label)" in source[label_index:output_index + 900]
    assert "left_panel_layout.addWidget(chart_info_output, 1)" in source[output_index:output_index + 800]
