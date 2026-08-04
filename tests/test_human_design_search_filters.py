def test_human_design_search_uses_tri_state_widgets_and_logic_toggles():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/dbv_search_panel.py"
    ).read_text(encoding="utf-8")

    assert 'add_hd_tri_state_filter(' in source
    assert '"human_design_type"' in source
    assert '"human_design_profile"' in source
    assert 'and_button = QRadioButton("&&")' in source
    assert 'or_button = QRadioButton("OR")' in source
    assert "and_button.setChecked(True)" in source
