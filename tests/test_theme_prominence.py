from __future__ import annotations

import math

import pytest

from ephemeraldaddy.analysis import theme_prominence as themes


def _reference_context(*, houses_available: bool = True):
    return {
        "signs": {"Aries": 1.0},
        "bodies": {},
        "houses": {1: 1.0} if houses_available else {},
        "houses_available": houses_available,
        "elements": {},
        "modes": {},
        "nakshatras": {},
        "bazisigns": {},
        "bazi_available": False,
        "hd": {
            "gates": {1},
            "channels": set(),
            "centers": set(),
            "profile": "",
            "authority": "",
            "cross": "",
            "available": True,
        },
    }


def test_subtheme_scoring_averages_categories_before_combining(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        themes,
        "THEMES",
        {
            "sample": {
                "family": "family",
                "signs": ["Aries"],
                "gates": [1, 2, 3, 4],
            }
        },
    )
    monkeypatch.setattr(themes, "WEIGHTED_THEME_PROPERTIES", ("signs", "gates"))
    monkeypatch.setattr(themes, "theme_item_weight", lambda *_args: 1.0)
    monkeypatch.setattr(themes, "_activation_context", lambda _chart: _reference_context())

    scores = themes.calculate_theme_subtheme_scores(object())

    # Signs score 1.0; gates score 0.25. Categories receive equal influence,
    # instead of the four-gate list swamping the one-sign list.
    assert scores["sample"] == pytest.approx(62.5)


def test_unavailable_houses_are_skipped_not_scored_as_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        themes,
        "THEMES",
        {
            "sample": {
                "family": "family",
                "signs": ["Aries"],
                "houses": [1],
            }
        },
    )
    monkeypatch.setattr(themes, "WEIGHTED_THEME_PROPERTIES", ("signs", "houses"))
    monkeypatch.setattr(themes, "theme_item_weight", lambda *_args: 1.0)
    monkeypatch.setattr(
        themes,
        "_activation_context",
        lambda _chart: _reference_context(houses_available=False),
    )

    scores = themes.calculate_theme_subtheme_scores(object())

    assert scores["sample"] == pytest.approx(100.0)


def test_family_scores_average_only_scorable_subthemes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        themes,
        "THEME_FAMILIES",
        {"family": {"label": "Family"}},
    )
    monkeypatch.setattr(
        themes,
        "themes_in_family",
        lambda family_key: ["one", "two", "unscorable"] if family_key == "family" else [],
    )

    result = themes.calculate_theme_family_scores(
        object(),
        subtheme_scores={"one": 20.0, "two": 80.0},
    )

    assert result == {"family": pytest.approx(50.0)}


def test_database_theme_averages_ignore_failed_charts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(themes, "THEME_FAMILIES", {"family": {"label": "Family"}})

    def score(chart: object):
        if chart == "bad":
            raise RuntimeError("unscoreable")
        return {"family": 25.0 if chart == "a" else 75.0}

    monkeypatch.setattr(themes, "calculate_theme_family_scores", score)

    assert themes.calculate_database_theme_family_averages(["a", "bad", "b"]) == {
        "family": pytest.approx(50.0)
    }


def test_snapshot_requires_complete_current_definition(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        themes,
        "THEME_FAMILIES",
        {"first": {"label": "First"}, "second": {"label": "Second"}},
    )
    monkeypatch.setattr(themes, "theme_definition_signature", lambda: "current")

    assert themes.theme_family_snapshot_averages(
        {
            "theme_family_definition_signature": "current",
            "theme_family_raw_averages": {"first": 10.0, "second": 20.0},
        }
    ) == {"first": 10.0, "second": 20.0}

    assert themes.theme_family_snapshot_averages(
        {
            "theme_family_definition_signature": "old",
            "theme_family_raw_averages": {"first": 10.0, "second": 20.0},
        }
    ) == {}
    assert themes.theme_family_snapshot_averages(
        {
            "theme_family_definition_signature": "current",
            "theme_family_raw_averages": {"first": 10.0},
        }
    ) == {}


def test_public_family_scores_are_finite_percentages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        themes,
        "THEME_FAMILIES",
        {"family": {"label": "Family"}},
    )
    monkeypatch.setattr(themes, "themes_in_family", lambda _family_key: ["one"])

    result = themes.calculate_theme_family_scores(object(), subtheme_scores={"one": 37.5})

    assert math.isfinite(result["family"])
    assert 0.0 <= result["family"] <= 100.0
