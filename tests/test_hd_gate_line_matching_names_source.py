from pathlib import Path


def test_similarity_matching_chart_names_handles_gate_lines():
    source = Path("ephemeraldaddy/gui/app.py").read_text()

    assert 'elif section_title == "Gate Lines in common":' in source
    assert 'getattr(chart, "human_design_gate_lines", ())' in source
    assert '"Gate Lines in common",\n                                label,' in source
