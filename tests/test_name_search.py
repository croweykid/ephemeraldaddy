from types import SimpleNamespace

import pytest

from ephemeraldaddy.gui.features.database_view.analytics.name_search import (
    analyze_names,
    chart_has_name_token,
    extract_name_tokens,
    load_name_suppressions,
    suppress_name_tokens,
)


def chart(uid, name, alias="", alignment=None):
    return SimpleNamespace(chart_uid=uid, name=name, alias=alias, alignment_score=alignment)


@pytest.fixture(autouse=True)
def isolated_name_suppressions(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "EPHEMERALDADDY_NAME_SUPPRESSIONS_PATH",
        str(tmp_path / "name_suppressions.json"),
    )


def test_extracts_whitespace_tokens_without_substring_matching():
    assert extract_name_tokens("Barbara", "Danny, Daniel Dan-the-man") == (
        "Barbara", "Danny", "Daniel", "Dan-the-man"
    )


def test_filters_alias_detritus_and_deduplicates_each_chart_case_insensitively():
    assert extract_name_tokens("Bob Bob", "mom and BOB") == ("Bob",)


def test_chart_name_token_match_uses_exact_shared_extraction_rules():
    subject = chart("uid", "Barbara", "Danny, Daniel Dan-the-man")
    assert chart_has_name_token(subject, "Danny")
    assert chart_has_name_token(subject, "dan-the-man")
    assert not chart_has_name_token(subject, "Barb")


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


def test_persisted_suppression_removes_name_without_editing_charts(tmp_path):
    path = tmp_path / "suppressions.json"
    charts = [chart(str(index), "Sam") for index in range(4)]
    assert suppress_name_tokens(["SAM"], path) == 1
    assert suppress_name_tokens(["sam"], path) == 0
    assert load_name_suppressions(path) == frozenset({"sam"})
    assert analyze_names(charts, stopwords=load_name_suppressions(path)) == []


def test_suppression_file_is_versioned_and_sorted(tmp_path):
    path = tmp_path / "suppressions.json"
    suppress_name_tokens(["Zed", "Amy"], path)
    assert path.read_text(encoding="utf-8") == (
        '{\n  "schema_version": 1,\n  "suppressed_names": [\n'
        '    "amy",\n    "zed"\n  ]\n}\n'
    )
