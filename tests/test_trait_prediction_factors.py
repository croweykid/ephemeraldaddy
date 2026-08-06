from types import SimpleNamespace

from ephemeraldaddy.analysis import weighted_chart_predictor as predictor


def test_matched_weighted_criteria_reports_chart_positions_aspects_and_dominance(monkeypatch):
    monkeypatch.setattr(predictor, "default_chart_uses_houses", lambda _chart: False)
    monkeypatch.setattr(predictor, "calculate_dominant_sign_weights", lambda _chart: {"Aries": 10.0, "Cancer": 0.0})
    monkeypatch.setattr(predictor, "calculate_dominant_planet_weights", lambda _chart: {"Sun": 8.0, "Mars": 7.0, "Pluto": 6.0, "Mercury": 0.0})
    monkeypatch.setattr(predictor, "calculate_dominant_nakshatra_weights", lambda _chart: {})
    chart = SimpleNamespace(
        positions={"Sun": 5.0, "Mars": 10.0, "Pluto": 130.0},
        aspects=[{"p1": "Mars", "p2": "Pluto", "type": "trine", "delta": 1.0}],
        chart_uses_houses=False,
    )
    profile = {
        "signs": {"Aries": 2, "Cancer": 1},
        "positions": {"Sun in Aries": 4, "Sun in H1": 3},
        "aspects": {"Mars trine Pluto": 5, "Sun square Mars": 2},
        "antibodies": {"Pluto": 1},
    }

    matches = predictor.matched_weighted_criteria(chart, profile)

    assert matches == {
        "positive": ["Aries", "Sun in Aries", "Mars trine Pluto"],
        "negative": ["Pluto"],
    }


def test_matched_weighted_criteria_excludes_house_factors_without_reliable_time(monkeypatch):
    monkeypatch.setattr(predictor, "default_chart_uses_houses", lambda _chart: False)
    monkeypatch.setattr(predictor, "calculate_dominant_sign_weights", lambda _chart: {})
    monkeypatch.setattr(predictor, "calculate_dominant_planet_weights", lambda _chart: {})
    monkeypatch.setattr(predictor, "calculate_dominant_nakshatra_weights", lambda _chart: {})
    chart = SimpleNamespace(positions={}, aspects=[], chart_uses_houses=False)

    matches = predictor.matched_weighted_criteria(
        chart,
        {"houses": {1: 5}, "positions": {"Sun in H1": 4}, "aspects": {"AS trine Mars": 3}},
    )

    assert matches == {"positive": [], "negative": []}
