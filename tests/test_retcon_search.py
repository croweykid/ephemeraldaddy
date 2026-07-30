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


def test_refinement_filters_only_existing_results_by_house(monkeypatch):
    first = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)
    second = first + dt.timedelta(hours=1)
    monkeypatch.setattr(retcon, "planetary_positions", lambda *_args: {"Sun": 5.0})
    monkeypatch.setattr(
        retcon,
        "placidus_houses_and_axes",
        lambda moment, *_args: (
            (
                [
                    0.0,
                    30.0,
                    60.0,
                    90.0,
                    120.0,
                    150.0,
                    180.0,
                    210.0,
                    240.0,
                    270.0,
                    300.0,
                    330.0,
                ]
                if moment == first
                else [
                    10.0,
                    40.0,
                    70.0,
                    100.0,
                    130.0,
                    160.0,
                    190.0,
                    220.0,
                    250.0,
                    280.0,
                    310.0,
                    340.0,
                ]
            ),
            {"AS": 0.0, "MC": 270.0},
        ),
    )

    matches = retcon.search_retcon_candidates(
        {"Sun": "Aries"},
        first,
        second,
        41.8,
        -87.6,
        required_houses={"Sun": 1},
        candidate_datetimes=[first, second],
    )

    assert [match["datetime"] for match in matches] == [first]


def test_default_criteria_bodies_exclude_timing_sensitive_angles():
    assert "Ascendant" not in retcon.RETCON_CRITERIA_BODIES
    assert "MC" not in retcon.RETCON_CRITERIA_BODIES
    assert "Ketu" not in retcon.RETCON_CRITERIA_BODIES
