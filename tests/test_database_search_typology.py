from types import SimpleNamespace

from ephemeraldaddy.gui.dbv_search_panel import chart_matches_typology_filters


def _chart(**overrides):
    values = {
        "enneagram_type": [5, 4],
        "tritype": [5, 9, 2],
        "mbti": ["I", "N", "T", "P"],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_typology_filters_allow_partial_assigned_metadata_searches():
    chart = _chart()

    assert chart_matches_typology_filters(chart, enneagram_type=5)
    assert chart_matches_typology_filters(chart, enneagram_wing=4)
    assert chart_matches_typology_filters(chart, tritype_types=frozenset({9, 2}))
    assert chart_matches_typology_filters(
        chart,
        mbti_letters=("I", None, "T", None),
    )


def test_typology_filters_reject_any_mismatched_requested_component():
    chart = _chart()

    assert not chart_matches_typology_filters(chart, enneagram_type=6)
    assert not chart_matches_typology_filters(chart, enneagram_wing=6)
    assert not chart_matches_typology_filters(chart, tritype_types=frozenset({5, 8}))
    assert not chart_matches_typology_filters(
        chart,
        mbti_letters=(None, "S", None, None),
    )


def test_typology_filters_treat_placeholder_values_as_unassigned():
    chart = _chart(
        enneagram_type=[0, 0],
        tritype=[0, 0, 0],
        mbti=["?", "?", "?", "?"],
    )

    assert chart_matches_typology_filters(chart)
    assert not chart_matches_typology_filters(chart, enneagram_type=1)
    assert not chart_matches_typology_filters(chart, tritype_types=frozenset({1}))
    assert not chart_matches_typology_filters(
        chart,
        mbti_letters=("E", None, None, None),
    )


def test_typology_filters_match_mbti_letters_case_insensitively():
    chart = _chart(mbti=["i", "n", "t", "p"])

    assert chart_matches_typology_filters(chart, mbti_letters=("I", "N", "T", "P"))


def test_typology_filters_optionally_match_x_in_each_requested_position():
    for mbti in (
        ["I", "x", "T", "J"],
        ["x", "S", "T", "J"],
        ["I", "S", "x", "x"],
    ):
        chart = _chart(mbti=mbti)
        assert not chart_matches_typology_filters(
            chart, mbti_letters=("I", "S", "T", "J")
        )
        assert chart_matches_typology_filters(
            chart,
            mbti_letters=("I", "S", "T", "J"),
            include_x_values=True,
        )
