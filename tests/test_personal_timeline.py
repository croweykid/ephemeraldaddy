from __future__ import annotations

import datetime
from types import SimpleNamespace

import pytest

from ephemeraldaddy.gui.features.transits import personal_timeline as timeline


UTC = datetime.timezone.utc


def test_database_selection_uid_is_authoritative() -> None:
    owner = SimpleNamespace(
        _selected_chart_uids=lambda: ["abc12345def67890"],
        _latest_chart=SimpleNamespace(chart_uid="SHOULDNOTWIN1234"),
    )

    assert timeline._selected_chart_uid_for_owner(owner) == "ABC12345DEF67890"


def test_database_selection_requires_exactly_one_uid() -> None:
    owner = SimpleNamespace(
        _selected_chart_uids=lambda: ["AAAAAAAABBBBBBBB", "CCCCCCCCDDDDDDDD"]
    )

    with pytest.raises(timeline.PersonalTimelineSelectionError):
        timeline._selected_chart_uid_for_owner(owner)


def test_definitions_include_saturn_return() -> None:
    chart = SimpleNamespace(positions={"Saturn": 17.0})

    definitions = timeline._build_transit_definitions(chart)

    assert any(
        definition.transiting_body == "Saturn"
        and definition.natal_body == "Saturn"
        and definition.aspect_name == "conjunction"
        for definition in definitions
    )


def test_generate_personal_timeline_refines_continuous_window(monkeypatch) -> None:
    birth = datetime.datetime(2000, 1, 1, 12, tzinfo=UTC)
    chart = SimpleNamespace(
        dt=birth,
        positions={"Sun": 0.0},
        is_deceased=False,
    )
    definition = timeline.TimelineTransitDefinition(
        transiting_body="Saturn",
        natal_body="Sun",
        natal_longitude=0.0,
        aspect_name="conjunction",
        aspect_angle=0.0,
        orb_deg=3.0,
    )

    monkeypatch.setattr(timeline, "_build_transit_definitions", lambda _chart: (definition,))
    monkeypatch.setattr(
        timeline,
        "_timeline_bounds",
        lambda _chart, _birth, _years: (
            birth,
            birth + datetime.timedelta(days=10),
        ),
    )

    # Linear longitude puts Saturn within 3 degrees of 0 from day 2 through day 8.
    def fake_longitude(when: datetime.datetime, body_name: str) -> float | None:
        assert body_name == "Saturn"
        elapsed_days = (when - birth).total_seconds() / 86400.0
        return elapsed_days - 5.0

    monkeypatch.setattr(timeline, "planetary_longitude", fake_longitude)

    windows = timeline.generate_personal_timeline(
        "abcdef1234567890",
        chart,
        years=1,
        step_days=1,
    )

    assert len(windows) == 1
    window = windows[0]
    assert window.chart_uid == "ABCDEF1234567890"
    expected_start = birth + datetime.timedelta(days=2)
    expected_end = birth + datetime.timedelta(days=8)
    assert abs((window.start - expected_start).total_seconds()) <= 120
    assert abs((window.end - expected_end).total_seconds()) <= 120


def test_known_death_year_without_month_caps_at_year_end() -> None:
    chart = SimpleNamespace(
        is_deceased=True,
        death_year=2042,
        death_month=0,
        death_day=0,
    )

    death = timeline._known_death_datetime(chart, UTC)

    assert death == datetime.datetime(2042, 12, 31, 23, 59, 59, tzinfo=UTC)
