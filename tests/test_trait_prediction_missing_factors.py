from types import SimpleNamespace

from ephemeraldaddy.gui.features.predictions import trait_factor_explanations as explanations


def _chart() -> SimpleNamespace:
    return SimpleNamespace()


def test_matching_body_position_suppresses_alternate_positions_for_that_bucket(monkeypatch):
    monkeypatch.setattr(explanations, "chart_uses_houses", lambda _chart: False)
    profile = {
        "positions": {
            "Pluto in Cancer": 2,
            "Pluto in Taurus": 7,
            "Mars in Libra": 5,
            "Mars in Taurus": 4,
            "Mars in Virgo": 3,
        }
    }

    evidence = explanations.build_trait_factor_evidence(
        _chart(),
        profile,
        matches={"positive": ["Pluto in Cancer"], "negative": []},
    )

    assert evidence.supporting == ("Pluto in Cancer",)
    assert evidence.missing == ("Mars not in Libra, Taurus or Virgo",)
    assert "Pluto in Taurus" not in evidence.missing


def test_missing_gates_are_compacted_in_display_order(monkeypatch):
    monkeypatch.setattr(explanations, "chart_uses_houses", lambda _chart: False)
    profile = {"gates": {49: 5, 29: 4, 55: 3}}

    evidence = explanations.build_trait_factor_evidence(
        _chart(),
        profile,
        matches={"positive": ["Gate 49"], "negative": []},
    )

    assert evidence.missing == ("Missing Gates 29 & 55",)

    single = explanations.build_trait_factor_evidence(
        _chart(),
        {"gates": {49: 5, 29: 4}},
        matches={"positive": ["Gate 49"], "negative": []},
    )
    assert single.missing == ("Missing Gate 29",)


def test_missing_keeps_independent_positive_factors_and_excludes_anti_factors(monkeypatch):
    monkeypatch.setattr(explanations, "chart_uses_houses", lambda _chart: False)
    profile = {
        "signs": {"Libra": 5},
        "aspects": {"Jupiter trine Pallas": 4, "Pallas sextile Uranus": 3},
        "antiaspects": {"Mars square Saturn": 9},
        "antigates": {12: 8},
    }

    evidence = explanations.build_trait_factor_evidence(
        _chart(),
        profile,
        matches={"positive": ["Pallas sextile Uranus"], "negative": ["Mars square Saturn"]},
    )

    assert evidence.counter_factors == ("Mars square Saturn",)
    assert evidence.missing == (
        "Libra not above baseline in chart",
        "Jupiter trine Pallas",
    )
    assert all("Gate 12" not in row for row in evidence.missing)


def test_missing_uses_supporting_category_order_and_omits_house_dependent_candidates(monkeypatch):
    monkeypatch.setattr(explanations, "chart_uses_houses", lambda _chart: False)
    profile = {
        "signs": {"Libra": 5},
        "houses": {10: 9},
        "gates": {29: 4, 55: 3},
        "positions": {"Mars in Libra": 5, "Mars in Taurus": 4, "Sun in H10": 10},
        "aspects": {"Jupiter trine Pallas": 3, "AS trine Mars": 12},
    }

    evidence = explanations.build_trait_factor_evidence(
        _chart(),
        profile,
        matches={"positive": [], "negative": []},
    )

    assert evidence.missing == (
        "Libra not above baseline in chart",
        "Missing Gates 29 & 55",
        "Mars not in Libra or Taurus",
        "Jupiter trine Pallas",
    )
    assert all("House 10" not in row and "Sun in H10" not in row and "AS trine Mars" not in row for row in evidence.missing)


def test_missing_is_empty_when_every_eligible_positive_factor_matches(monkeypatch):
    monkeypatch.setattr(explanations, "chart_uses_houses", lambda _chart: False)
    profile = {
        "signs": {"Libra": 5},
        "gates": {49: 4},
        "positions": {"Pluto in Cancer": 3, "Pluto in Taurus": 2},
        "aspects": {"Jupiter trine Pallas": 1},
    }

    evidence = explanations.build_trait_factor_evidence(
        _chart(),
        profile,
        matches={
            "positive": ["Libra", "Gate 49", "Pluto in Cancer", "Jupiter trine Pallas"],
            "negative": [],
        },
    )

    assert evidence.missing == ()
