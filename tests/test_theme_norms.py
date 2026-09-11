from __future__ import annotations

import pytest

from ephemeraldaddy.analysis import theme_norms as norms


def test_chart_shares_are_additive_across_subthemes_and_families(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(norms.prominence, "THEMES", {"a": {}, "b": {}, "c": {}})
    monkeypatch.setattr(
        norms.prominence,
        "THEME_FAMILIES",
        {"first": {"label": "First"}, "second": {"label": "Second"}},
    )
    monkeypatch.setattr(
        norms.prominence,
        "themes_in_family",
        lambda family_key: ("a", "b") if family_key == "first" else ("c",),
    )

    subthemes, families = norms.calculate_theme_chart_shares(
        {"a": 20.0, "b": 30.0, "c": 50.0}
    )

    assert subthemes == pytest.approx({"a": 20.0, "b": 30.0, "c": 50.0})
    assert families == pytest.approx({"first": 50.0, "second": 50.0})
    assert sum(subthemes.values()) == pytest.approx(100.0)
    assert sum(families.values()) == pytest.approx(100.0)


def test_chart_shares_normalize_raw_prominence_instead_of_relabeling_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(norms.prominence, "THEMES", {"a": {}, "b": {}})
    monkeypatch.setattr(
        norms.prominence,
        "THEME_FAMILIES",
        {"family": {"label": "Family"}},
    )
    monkeypatch.setattr(norms.prominence, "themes_in_family", lambda _key: ("a", "b"))

    subthemes, families = norms.calculate_theme_chart_shares({"a": 80.0, "b": 20.0})

    assert subthemes["a"] == pytest.approx(80.0)
    assert subthemes["b"] == pytest.approx(20.0)
    assert families["family"] == pytest.approx(100.0)

    subthemes, _families = norms.calculate_theme_chart_shares({"a": 80.0, "b": 80.0})
    assert subthemes == pytest.approx({"a": 50.0, "b": 50.0})


def test_empirical_percentile_uses_midrank_for_ties() -> None:
    assert norms.empirical_percentile(50.0, [10.0, 50.0, 50.0, 90.0]) == pytest.approx(50.0)
    assert norms.empirical_percentile(100.0, [10.0, 50.0, 90.0]) == pytest.approx(100.0)
    assert norms.empirical_percentile(0.0, []) is None


def test_percentile_label_uses_ordinal_suffixes() -> None:
    assert norms.format_theme_percentile(1.0) == "1st p"
    assert norms.format_theme_percentile(2.0) == "2nd p"
    assert norms.format_theme_percentile(3.0) == "3rd p"
    assert norms.format_theme_percentile(11.0) == "11th p"
    assert norms.format_theme_percentile(94.0) == "94th p"
    assert norms.format_theme_percentile(None) == "—"


def test_extended_snapshot_fields_are_backward_compatible() -> None:
    extended = {
        "subtheme_share_averages_by_availability": {"houses:1|hd:1|bazi:0": {"a": 12.5}},
        "subtheme_share_values_by_availability": {"houses:1|hd:1|bazi:0": {"a": [10.0, 15.0]}},
        "family_share_averages_by_availability": {"houses:1|hd:1|bazi:0": {"family": 100.0}},
        "family_share_values_by_availability": {"houses:1|hd:1|bazi:0": {"family": [100.0, 100.0]}},
        "factor_activation_values_by_availability": {"houses:1|hd:1|bazi:0": {"[\"signs\",\"Aries\"]": [0.0, 1.0]}},
    }
    payload = norms.enrich_theme_snapshot_with_availability_baselines(
        {"existing": True},
        {"houses:1|hd:1|bazi:0": {"family": 42.0}},
        {"houses:1|hd:1|bazi:0": 2},
        extended_norms=extended,
    )

    assert payload["existing"] is True
    assert payload[norms.THEME_NORMS_AVAILABILITY_SCHEMA_FIELD] == 1
    assert payload[norms.THEME_CHART_SHARE_SCHEMA_FIELD] == 1
    assert payload[norms.THEME_FAMILY_AVAILABILITY_ROWS_FIELD]["houses:1|hd:1|bazi:0"]["family"] == 42.0
    assert payload[norms.THEME_SUBTHEME_SHARE_VALUES_FIELD]["houses:1|hd:1|bazi:0"]["a"] == [10.0, 15.0]
