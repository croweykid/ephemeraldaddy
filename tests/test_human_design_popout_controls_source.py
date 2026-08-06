from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_human_design_popout_defaults_to_circuits_without_a_header_label():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/aspect_weight_graphs.py").read_text()

    circuits_item = 'analytics_view_dropdown.addItem("CIRCUITS", "circuits")'
    streams_item = 'analytics_view_dropdown.addItem("AWARENESS STREAMS", "awareness_streams")'
    assert source.index(circuits_item) < source.index(streams_item)
    assert 'QLabel("Awareness Streams"' not in source
    assert 'QPushButton("Synastry Chart")' in source


def test_human_design_popout_synastry_uses_current_chart_uid_as_first_chart():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "open_hd_synastry=lambda: self._open_human_design_synastry_for_chart_uid(" in source
    assert "get_chart_id_by_uid(first_chart_uid)" in source
    assert "focus_second_input=True" in source
