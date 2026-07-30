import datetime as dt

from ephemeraldaddy.core import retcon


def test_rectification_bodies_replace_ketu_with_chart_angles():
    assert "Ketu" not in retcon.RETCON_BODIES
    assert "Ascendant" in retcon.RETCON_BODIES
    assert "MC" in retcon.RETCON_BODIES


def test_search_can_match_ascendant_and_midheaven(monkeypatch):
    moment = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)
    monkeypatch.setattr(retcon, "planetary_positions", lambda *_args: {"Sun": 5.0})
    monkeypatch.setattr(
        retcon,
        "placidus_axes",
        lambda *_args: {"AS": 35.0, "MC": 275.0},
    )

    matches = retcon.search_retcon_candidates(
        {"Ascendant": "Taurus", "MC": "Capricorn"},
        moment,
        moment,
        41.8,
        -87.6,
    )

    assert len(matches) == 1
    assert matches[0]["positions"] == {"Ascendant": 35.0, "MC": 275.0}


def test_planet_only_search_skips_chart_angle_calculation(monkeypatch):
    moment = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)
    monkeypatch.setattr(retcon, "planetary_positions", lambda *_args: {"Sun": 5.0})

    def unexpected_axes(*_args):
        raise AssertionError("planet-only searches should not calculate chart angles")

    monkeypatch.setattr(retcon, "placidus_axes", unexpected_axes)

    matches = retcon.search_retcon_candidates(
        {"Sun": "Aries"}, moment, moment, 41.8, -87.6
    )

    assert len(matches) == 1
