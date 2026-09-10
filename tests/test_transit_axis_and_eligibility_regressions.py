from __future__ import annotations

import datetime

from ephemeraldaddy.core.aspect_display import (
    aspect_axis_display_label,
    iter_displayable_aspects,
)
from ephemeraldaddy.core.composite import (
    PERSONAL_TRANSIT_MODE_DAILY_VIBE,
    PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
    BodyPosition,
    compute_aspects,
    personal_transit_rules_for_mode,
)
from ephemeraldaddy.gui.features.charts.presentation import format_transit_range
from ephemeraldaddy.gui.features.charts.text_summary import (
    _aspect_body_with_sign,
    _format_popout_aspect_endpoint,
)


def _position(name: str, longitude: float, *, layer: str) -> BodyPosition:
    return BodyPosition(name=name, lon_deg=longitude, layer=layer)


def _single_pair_hits(
    transit_name: str,
    transit_longitude: float,
    natal_name: str,
    natal_longitude: float,
    *,
    mode: str,
):
    return compute_aspects(
        [_position(transit_name, transit_longitude, layer="TRANSIT")],
        [_position(natal_name, natal_longitude, layer="NATAL")],
        personal_transit_rules_for_mode(mode),
    )


def test_life_forecast_restores_saturn_and_jupiter_structural_transits() -> None:
    cases = (
        ("Saturn", 90.0, "Mercury", 0.0, "square"),
        ("Saturn", 60.0, "Uranus", 0.0, "sextile"),
        ("Saturn", 120.0, "Pluto", 0.0, "trine"),
        ("Jupiter", 60.0, "Uranus", 0.0, "sextile"),
    )

    for transit_name, transit_lon, natal_name, natal_lon, expected_aspect in cases:
        hits = _single_pair_hits(
            transit_name,
            transit_lon,
            natal_name,
            natal_lon,
            mode=PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
        )
        assert [(hit.a.name, hit.aspect, hit.b.name) for hit in hits] == [
            (transit_name, expected_aspect, natal_name)
        ]


def test_saturn_does_not_leak_back_into_daily_vibe_at_exact_zero_orb() -> None:
    hits = _single_pair_hits(
        "Saturn",
        0.0,
        "Sun",
        0.0,
        mode=PERSONAL_TRANSIT_MODE_DAILY_VIBE,
    )
    assert hits == []


def test_chiron_is_restored_as_life_forecast_transit() -> None:
    cases = (
        ("Chiron", 90.0, "Sun", 0.0, "square"),
        ("Chiron", 120.0, "Moon", 0.0, "trine"),
        ("Chiron", 60.0, "Rahu", 0.0, "sextile"),
    )

    for transit_name, transit_lon, natal_name, natal_lon, expected_aspect in cases:
        hits = _single_pair_hits(
            transit_name,
            transit_lon,
            natal_name,
            natal_lon,
            mode=PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
        )
        assert [(hit.a.name, hit.aspect, hit.b.name) for hit in hits] == [
            (transit_name, expected_aspect, natal_name)
        ]


def test_chiron_is_available_as_daily_vibe_natal_target() -> None:
    mars_hits = _single_pair_hits(
        "Mars",
        90.0,
        "Chiron",
        0.0,
        mode=PERSONAL_TRANSIT_MODE_DAILY_VIBE,
    )
    ascendant_hits = _single_pair_hits(
        "AS",
        0.0,
        "Chiron",
        0.0,
        mode=PERSONAL_TRANSIT_MODE_DAILY_VIBE,
    )

    assert [(hit.a.name, hit.aspect, hit.b.name) for hit in mars_hits] == [
        ("Mars", "square", "Chiron")
    ]
    assert [(hit.a.name, hit.aspect, hit.b.name) for hit in ascendant_hits] == [
        ("AS", "conjunction", "Chiron")
    ]


def test_transit_aspect_hits_collapse_as_ds_axis_halves() -> None:
    hits = compute_aspects(
        [
            _position("AS", 0.0, layer="TRANSIT"),
            _position("DS", 180.0, layer="TRANSIT"),
        ],
        [_position("Saturn", 90.0, layer="NATAL")],
        personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_DAILY_VIBE),
    )

    assert len(hits) == 1
    assert hits[0].aspect == "square"
    assert hits[0].b.name == "Saturn"
    assert hits[0].a.name in {"AS", "DS"}


def test_transit_aspect_hits_collapse_rahu_ketu_halves() -> None:
    hits = compute_aspects(
        [
            _position("Rahu", 180.0, layer="TRANSIT"),
            _position("Ketu", 0.0, layer="TRANSIT"),
        ],
        [_position("Moon", 0.0, layer="NATAL")],
        personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_LIFE_FORECAST),
    )

    assert len(hits) == 1
    assert hits[0].b.name == "Moon"
    assert hits[0].a.name in {"Rahu", "Ketu"}
    assert hits[0].aspect in {"conjunction", "opposition"}


def test_shared_display_policy_collapses_complementary_axis_rows() -> None:
    aspects = [
        {"p1": "AS", "p2": "Saturn", "type": "square"},
        {"p1": "DS", "p2": "Saturn", "type": "square"},
        {"p1": "MC", "p2": "Venus", "type": "opposition"},
        {"p1": "IC", "p2": "Venus", "type": "conjunction"},
        {"p1": "Rahu", "p2": "Moon", "type": "opposition"},
        {"p1": "Ketu", "p2": "Moon", "type": "conjunction"},
        {"p1": "AS", "p2": "Jupiter", "type": "trine"},
        {"p1": "DS", "p2": "Jupiter", "type": "sextile"},
    ]
    known_positions = {
        "AS",
        "DS",
        "MC",
        "IC",
        "Rahu",
        "Ketu",
        "Saturn",
        "Venus",
        "Moon",
        "Jupiter",
    }

    visible = list(
        iter_displayable_aspects(
            aspects,
            use_houses=True,
            known_positions=known_positions,
        )
    )

    assert visible == [aspects[0], aspects[2], aspects[4], aspects[6]]


def test_axis_event_labels_are_shared_and_do_not_replace_raw_endpoints() -> None:
    assert aspect_axis_display_label("AS") == "AS–DS axis"
    assert aspect_axis_display_label("DS") == "AS–DS axis"
    assert aspect_axis_display_label("MC") == "MC–IC axis"
    assert aspect_axis_display_label("IC") == "MC–IC axis"
    assert aspect_axis_display_label("Rahu") == "Rahu–Ketu axis"
    assert aspect_axis_display_label("Ketu") == "Rahu–Ketu axis"
    assert aspect_axis_display_label("Saturn") is None

    representative = _position("AS", 0.0, layer="TRANSIT")
    assert representative.name == "AS"
    assert _format_popout_aspect_endpoint(representative, include_house=False) == "AS–DS axis"
    assert _aspect_body_with_sign("AS", {"AS": 0.0}) == "AS–DS axis"


def test_timed_transit_range_converts_utc_to_requested_display_timezone() -> None:
    edt = datetime.timezone(datetime.timedelta(hours=-4), name="EDT")
    start = datetime.datetime(2026, 9, 10, 13, 8, tzinfo=datetime.timezone.utc)
    end = datetime.datetime(2026, 9, 10, 13, 37, tzinfo=datetime.timezone.utc)

    assert format_transit_range(
        start,
        end,
        include_time=True,
        display_timezone=edt,
    ) == "09-10-2026 09:08 -> 09-10-2026 09:37"


def test_date_only_transit_range_keeps_existing_utc_date_semantics() -> None:
    edt = datetime.timezone(datetime.timedelta(hours=-4), name="EDT")
    start = datetime.datetime(2026, 9, 10, 1, 0, tzinfo=datetime.timezone.utc)
    end = datetime.datetime(2026, 9, 11, 1, 0, tzinfo=datetime.timezone.utc)

    assert format_transit_range(
        start,
        end,
        include_time=False,
        display_timezone=edt,
    ) == "09-10-2026 -> 09-11-2026"
