from types import SimpleNamespace

import pytest

from ephemeraldaddy.gui.features.database_view.analytics.name_search import (
    analyze_names,
    extract_name_tokens,
)


def chart(uid, name, alias="", alignment=None):
    return SimpleNamespace(chart_uid=uid, name=name, alias=alias, alignment_score=alignment)


def test_extracts_whitespace_tokens_without_substring_matching():
    assert extract_name_tokens("Barbara", "Danny, Daniel Dan-the-man") == (
        "Barbara", "Danny", "Daniel", "Dan-the-man"
    )


def test_filters_alias_detritus_and_deduplicates_each_chart_case_insensitively():
    assert extract_name_tokens("Bob Bob", "mom and BOB") == ("Bob",)


def test_aggregates_distinct_uid_frequency_and_alignment_statistics():
    charts = [
        chart("a", "Danny", alignment=2),
        chart("b", "Daniel", "Danny", 4),
        chart("c", "Danny", alignment=4),
        chart("d", "Other", "Danny", None),
        chart("e", "Barbara", "Barb", 10),
    ]
    result = analyze_names(charts)
    assert [item.name for item in result] == ["Danny"]
    danny = result[0]
    assert danny.chart_uids == ("A", "B", "C", "D")
    assert danny.frequency == 4
    assert danny.alignment_count == 3
    assert danny.mean_alignment == pytest.approx(10 / 3)
    assert danny.median_alignment == 4
    assert danny.mode_alignment == (4.0,)


def test_multimodal_alignment_has_no_single_mode_value():
    result = analyze_names(
        [chart(str(index), "Sam", alignment=value) for index, value in enumerate((1, 1, 2, 2))]
    )[0]
    assert result.mode_alignment == (1.0, 2.0)
    assert result.value_for("mode_alignment") is None


def test_rejects_invalid_minimum_frequency():
    with pytest.raises(ValueError):
        analyze_names([], minimum_frequency=0)
