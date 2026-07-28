from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def test_birth_date_captions_have_no_layout_gap_and_peer_inputs_align_below() -> None:
    assert "layout.setSpacing(0)" in APP_SOURCE
    assert "self.time_edit, 0, Qt.AlignBottom" in APP_SOURCE
    assert "self.time_unknown_checkbox, 0, Qt.AlignBottom" in APP_SOURCE


def test_compact_metadata_labels_are_multiline_and_vertically_centered() -> None:
    assert 'QLabel("Chart\\nType:")' in APP_SOURCE
    assert 'QLabel("Data\\nQuality:")' in APP_SOURCE
    assert 'QCheckBox("no\\ndata")' in APP_SOURCE
    assert "self.chart_source_combo, 0, Qt.AlignVCenter" in APP_SOURCE
    assert "self.data_rating_combo, 0, Qt.AlignVCenter" in APP_SOURCE
