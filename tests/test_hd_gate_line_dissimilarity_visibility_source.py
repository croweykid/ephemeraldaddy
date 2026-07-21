from pathlib import Path


def test_gate_line_dissimilarity_visibility_uses_gate_line_matches():
    source = Path("ephemeraldaddy/gui/app.py").read_text()

    assert 'bool(section_matches.get("Gate Lines in contrast", []))' in source
    assert 'bool(section_matches.get("Gates in contrast", []))' not in source
