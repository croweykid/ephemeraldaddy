from types import SimpleNamespace

from ephemeraldaddy.core.db import SOURCE_HYPOTHETICAL, SOURCE_PUBLIC_DB
from ephemeraldaddy.gui.features.charts.provenance import (
    chart_is_hypothetical,
    chart_is_non_aggregable,
    chart_is_placeholder,
    chart_is_similarity_participant,
    chart_row_is_hypothetical,
    chart_row_is_non_aggregable,
    chart_row_is_placeholder,
    chart_row_is_similarity_participant,
)


def _row(chart_id: int, chart_type: str, is_placeholder: int = 0) -> tuple:
    return (
        chart_id,
        f"Chart {chart_id}",
        None,
        None,
        "2000-01-01T00:00:00",
        None,
        "created",
        0,
        0,
        0,
        None,
        0,
        None,
        0,
        chart_type,
        is_placeholder,
        0,
        1,
        1,
        2000,
    )


def test_hypothetical_and_placeholder_are_distinct_chart_states():
    hypothetical = SimpleNamespace(chart_type=SOURCE_HYPOTHETICAL, is_placeholder=False)
    placeholder = SimpleNamespace(chart_type=SOURCE_PUBLIC_DB, is_placeholder=True)
    canonical = SimpleNamespace(chart_type=SOURCE_PUBLIC_DB, is_placeholder=False)

    assert chart_is_hypothetical(hypothetical)
    assert not chart_is_placeholder(hypothetical)
    assert chart_is_non_aggregable(hypothetical)

    assert chart_is_placeholder(placeholder)
    assert not chart_is_hypothetical(placeholder)
    assert chart_is_non_aggregable(placeholder)

    assert not chart_is_hypothetical(canonical)
    assert not chart_is_placeholder(canonical)
    assert not chart_is_non_aggregable(canonical)


def test_hypothetical_rows_are_excluded_as_candidates_but_not_placeholders():
    hypothetical_row = _row(1, SOURCE_HYPOTHETICAL)
    placeholder_row = _row(2, SOURCE_PUBLIC_DB, is_placeholder=1)
    canonical_row = _row(3, SOURCE_PUBLIC_DB)

    assert chart_row_is_hypothetical(hypothetical_row)
    assert not chart_row_is_placeholder(hypothetical_row)
    assert chart_row_is_non_aggregable(hypothetical_row)

    assert chart_row_is_placeholder(placeholder_row)
    assert not chart_row_is_hypothetical(placeholder_row)
    assert chart_row_is_non_aggregable(placeholder_row)

    assert not chart_row_is_placeholder(canonical_row)
    assert not chart_row_is_hypothetical(canonical_row)
    assert not chart_row_is_non_aggregable(canonical_row)


def test_similarity_analysis_participants_include_hypothetical_charts():
    hypothetical = SimpleNamespace(chart_type=SOURCE_HYPOTHETICAL, is_placeholder=False)
    placeholder = SimpleNamespace(chart_type=SOURCE_PUBLIC_DB, is_placeholder=True)
    canonical = SimpleNamespace(chart_type=SOURCE_PUBLIC_DB, is_placeholder=False)

    assert chart_is_similarity_participant(hypothetical)
    assert not chart_is_similarity_participant(placeholder)
    assert chart_is_similarity_participant(canonical)


def test_similarity_analysis_rows_include_hypothetical_charts():
    hypothetical_row = _row(1, SOURCE_HYPOTHETICAL)
    placeholder_row = _row(2, SOURCE_PUBLIC_DB, is_placeholder=1)
    canonical_row = _row(3, SOURCE_PUBLIC_DB)

    assert chart_row_is_similarity_participant(hypothetical_row)
    assert not chart_row_is_similarity_participant(placeholder_row)
    assert chart_row_is_similarity_participant(canonical_row)
