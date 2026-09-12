import datetime
from types import SimpleNamespace

import pytest

from ephemeraldaddy.gui.features.transits.personal_timeline_generation import (
    PersonalTimelineWindow,
    TimelineTransitDefinition,
    _build_personal_transit_range_definitions,
    generate_personal_transit_range,
)
from ephemeraldaddy.gui.features.transits.theme_view import (
    format_global_transit_theme_view,
    format_transit_range_table,
    format_transit_theme_view,
    themes_for_aspect_bodies,
)


UTC = datetime.timezone.utc


def test_theme_view_groups_aspect_under_reference_theme_with_dates():
    definition = TimelineTransitDefinition("Saturn", "Sun", 10.0, "square", 90.0, 3.0)
    window = PersonalTimelineWindow(
        "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        definition,
        datetime.datetime(2026, 8, 13, tzinfo=UTC),
        datetime.datetime(2026, 9, 20, tzinfo=UTC),
    )

    text = format_transit_theme_view([window])

    assert "2026-08-13 – 2026-09-20" in text
    assert "Saturn square natal Sun" in text
    assert themes_for_aspect_bodies("Saturn", "Sun")
    assert "SURROUNDING MAJOR TRANSITS (±30 DAYS)" in format_transit_range_table([window])


def test_global_theme_view_groups_aspects_for_chart_date():
    aspect = {"p1": "Saturn", "p2": "Sun", "type": "square"}

    text = format_global_transit_theme_view(
        [aspect], datetime.datetime(2026, 9, 12, tzinfo=UTC)
    )

    assert "2026-09-12  Saturn square Sun" in text


def test_truncated_personal_windows_do_not_claim_clipped_dates_are_boundaries():
    definition = TimelineTransitDefinition("Pluto", "Sun", 10.0, "square", 90.0, 3.0)
    window = PersonalTimelineWindow(
        "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        definition,
        datetime.datetime(2026, 8, 13, tzinfo=UTC),
        datetime.datetime(2026, 10, 12, tzinfo=UTC),
        start_truncated=True,
        end_truncated=True,
    )

    theme_text = format_transit_theme_view([window])
    table_text = format_transit_range_table([window])

    assert "before 2026-08-13 – after 2026-10-12" in theme_text
    assert "before 2026-08-13 – after 2026-10-12" in table_text


def test_transit_views_convert_dates_to_display_timezone():
    display_tz = datetime.timezone(datetime.timedelta(hours=-5))
    definition = TimelineTransitDefinition("Pluto", "Sun", 10.0, "square", 90.0, 3.0)
    window = PersonalTimelineWindow(
        "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        definition,
        datetime.datetime(2026, 9, 12, 0, 30, tzinfo=UTC),
        datetime.datetime(2026, 9, 13, 0, 30, tzinfo=UTC),
    )

    table_text = format_transit_range_table([window], display_timezone=display_tz)
    global_text = format_global_transit_theme_view(
        [{"p1": "Pluto", "p2": "Sun", "type": "square"}],
        datetime.datetime(2026, 9, 12, 0, 30, tzinfo=UTC),
        display_timezone=display_tz,
    )

    assert "2026-09-11 – 2026-09-12" in table_text
    assert "2026-09-11  Pluto square Sun" in global_text


def test_short_range_candidates_match_personal_transit_mode_rules():
    definitions = _build_personal_transit_range_definitions(
        SimpleNamespace(positions={"Sun": 0.0, "Pluto": 10.0})
    )
    keys = {definition.key for definition in definitions}

    assert ("Sun", "Sun", "square") in keys  # Daily Vibe fast-body major aspect.
    assert ("Pluto", "Sun", "quincunx") in keys  # Allowed Life Forecast minor aspect.
    assert ("Ceres", "Pluto", "quincunx") not in keys


def test_short_range_generator_includes_approaching_and_recent_windows(monkeypatch):
    chart = SimpleNamespace(positions={"Sun": 0.0})
    start = datetime.datetime(2026, 8, 13, tzinfo=UTC)
    end = datetime.datetime(2026, 10, 12, tzinfo=UTC)

    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.transits.personal_timeline_generation._build_personal_transit_range_definitions",
        lambda _chart: (TimelineTransitDefinition("Saturn", "Sun", 0.0, "conjunction", 0.0, 1.0),),
    )
    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.transits.personal_timeline_generation.planetary_longitude",
        lambda when, _body: 0.0 if 10 <= (when - start).days <= 50 else 20.0,
    )

    windows = generate_personal_transit_range(
        "01ARZ3NDEKTSV4RRFFQ69G5FAV", chart, start=start, end=end
    )

    assert len(windows) == 1
    assert start < windows[0].start < datetime.datetime(2026, 9, 12, tzinfo=UTC)
    assert datetime.datetime(2026, 9, 12, tzinfo=UTC) < windows[0].end < end


def test_short_range_generator_reuses_longitudes_during_boundary_refinement(monkeypatch):
    start = datetime.datetime(2026, 9, 1, tzinfo=UTC)
    definitions = tuple(
        TimelineTransitDefinition("Saturn", natal, 0.0, "conjunction", 0.0, 1.0)
        for natal in ("Sun", "Moon")
    )
    calls = 0

    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.transits.personal_timeline_generation._build_personal_transit_range_definitions",
        lambda _chart: definitions,
    )

    def longitude(when, _body):
        nonlocal calls
        calls += 1
        elapsed_hours = (when - start).total_seconds() / 3600.0
        return 0.0 if 6.0 <= elapsed_hours <= 12.0 else 20.0

    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.transits.personal_timeline_generation.planetary_longitude",
        longitude,
    )

    windows = generate_personal_transit_range(
        "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        SimpleNamespace(positions={"Sun": 0.0, "Moon": 0.0}),
        start=start,
        end=start + datetime.timedelta(hours=18),
    )

    assert len(windows) == 2
    assert calls <= 36  # Shared body/timestamp probes are calculated only once.


def test_short_range_generator_honors_cancellation(monkeypatch):
    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.transits.personal_timeline_generation._build_personal_transit_range_definitions",
        lambda _chart: (
            TimelineTransitDefinition("Saturn", "Sun", 0.0, "conjunction", 0.0, 1.0),
        ),
    )
    calls = 0

    def cancelled():
        nonlocal calls
        calls += 1
        return calls > 1

    windows = generate_personal_transit_range(
        "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        SimpleNamespace(positions={"Sun": 0.0}),
        start=datetime.datetime(2026, 9, 1, tzinfo=UTC),
        end=datetime.datetime(2026, 10, 1, tzinfo=UTC),
        cancelled=cancelled,
    )

    assert windows == []
    assert calls == 2


@pytest.mark.parametrize("chart_uid", ["", "   "])
def test_short_range_generator_requires_permanent_chart_uid(chart_uid):
    with pytest.raises(ValueError, match="Chart UID"):
        generate_personal_transit_range(
            chart_uid,
            SimpleNamespace(positions={}),
            start=datetime.datetime(2026, 8, 13, tzinfo=UTC),
            end=datetime.datetime(2026, 10, 12, tzinfo=UTC),
        )
