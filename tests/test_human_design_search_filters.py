from ephemeraldaddy.gui.dbv_search_panel import scalar_value_matches_tri_state_filters


def test_human_design_scalar_filter_or_allows_multiple_inclusions():
    assert scalar_value_matches_tri_state_filters(
        "Projector",
        included={"Projector", "Manifestor"},
        excluded=set(),
        require_all=False,
    )


def test_human_design_scalar_filter_enforces_exclusions():
    assert not scalar_value_matches_tri_state_filters(
        "Projector",
        included=set(),
        excluded={"Projector"},
        require_all=False,
    )


def test_human_design_scalar_filter_and_is_strict_for_multiple_values():
    assert not scalar_value_matches_tri_state_filters(
        "Projector",
        included={"Projector", "Manifestor"},
        excluded=set(),
        require_all=True,
    )


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
