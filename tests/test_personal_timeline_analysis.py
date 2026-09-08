from __future__ import annotations

import datetime
import json
from pathlib import Path
from types import SimpleNamespace

from ephemeraldaddy.gui.features.transits import personal_timeline_analysis as analysis


UTC = datetime.timezone.utc


def _event_payload(
    event_id: str,
    name: str,
    *,
    begin: tuple[str, str, str] | None = None,
    peak: tuple[str, str, str] | None = None,
) -> dict:
    def event_date(value):
        if value is None:
            return {"unknown": False, "ongoing": False, "value": None}
        earliest, latest, precision = value
        return {
            "unknown": False,
            "ongoing": False,
            "value": {
                "raw": earliest[:10],
                "precision": precision,
                "weekday": None,
                "earliest": earliest,
                "latest": latest,
            },
        }

    return {
        "id": event_id,
        "name": name,
        "begin": event_date(begin),
        "peak": event_date(peak),
        "end": {"unknown": True, "ongoing": False, "value": None},
    }


def test_load_library_of_ghosts_json_preserves_explicit_date_interval(tmp_path: Path) -> None:
    payload = {
        "schema": analysis.LIBRARY_OF_GHOSTS_SCHEMA,
        "schema_version": 1,
        "events": [
            _event_payload(
                "event-1",
                "Moved",
                begin=(
                    "1998-03-01T00:00:00",
                    "1998-03-31T23:59:59.999999",
                    "month",
                ),
            )
        ],
    }
    path = tmp_path / "timeline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    events = analysis.load_life_event_json(path, UTC)

    assert len(events) == 1
    assert events[0].precision == "month"
    assert events[0].start == datetime.datetime(1998, 3, 1, tzinfo=UTC)
    assert events[0].end == datetime.datetime(
        1998, 3, 31, 23, 59, 59, 999999, tzinfo=UTC
    )


def test_event_anchor_prefers_peak_over_broad_begin_interval() -> None:
    event = _event_payload(
        "event-1",
        "Turning point",
        begin=("1998-01-01T00:00:00", "1998-12-31T23:59:59", "year"),
        peak=("1998-06-14T12:00:00", "1998-06-14T12:00:00", "minute"),
    )

    anchor = analysis.event_anchor_from_dict(event, UTC)

    assert anchor is not None
    assert anchor.source_field == "peak"
    assert anchor.start == datetime.datetime(1998, 6, 14, 12, tzinfo=UTC)
    assert anchor.end == anchor.start


def test_merged_transit_intervals_remove_double_counted_exposure() -> None:
    start = datetime.datetime(2000, 1, 1, tzinfo=UTC)
    windows = [
        SimpleNamespace(start=start, end=start + datetime.timedelta(days=10)),
        SimpleNamespace(
            start=start + datetime.timedelta(days=5),
            end=start + datetime.timedelta(days=15),
        ),
    ]

    merged = analysis.merged_transit_intervals(
        windows,
        start,
        start + datetime.timedelta(days=30),
    )

    assert merged == [(start, start + datetime.timedelta(days=15))]
    assert analysis.covered_fraction(
        merged,
        start,
        start + datetime.timedelta(days=30),
    ) == 0.5


def test_analyze_reports_overlap_exposure_and_random_expectation(monkeypatch) -> None:
    birth = datetime.datetime(2000, 1, 1, tzinfo=UTC)
    chart = SimpleNamespace(
        dt=birth,
        is_deceased=True,
        death_year=2000,
        death_month=4,
        death_day=10,
    )
    transit = SimpleNamespace(
        label="Saturn square natal Sun",
        transiting_body="Saturn",
        natal_body="Sun",
        natal_longitude=0.0,
        aspect_angle=90.0,
    )
    windows = [
        SimpleNamespace(
            transit=transit,
            start=birth + datetime.timedelta(days=10),
            end=birth + datetime.timedelta(days=20),
        )
    ]
    events = [
        analysis.LifeEventAnchor(
            "one",
            "Hit",
            birth + datetime.timedelta(days=15),
            birth + datetime.timedelta(days=15),
            "peak",
            "minute",
        ),
        analysis.LifeEventAnchor(
            "two",
            "Miss",
            birth + datetime.timedelta(days=50),
            birth + datetime.timedelta(days=50),
            "peak",
            "minute",
        ),
    ]
    monkeypatch.setattr(
        analysis,
        "event_has_exact_hit_nearby",
        lambda event, windows, proximity_days: event.event_id == "one",
    )

    result = analysis.analyze_personal_timeline(
        "ABC",
        chart,
        windows,
        events,
        randomization_trials=200,
    )

    assert result.event_count == 2
    assert result.observed_hits == 1
    assert result.observed_rate == 0.5
    assert result.exact_proximity_hits == 1
    assert 0.09 < result.background_exposure < 0.11
    assert 0.0 <= result.random_expected_hits <= 2.0
    assert result.lift_vs_background is not None
    assert result.lift_vs_background > 4.0


def test_exact_hit_detection_handles_crossing(monkeypatch) -> None:
    start = datetime.datetime(2000, 1, 1, tzinfo=UTC)
    transit = SimpleNamespace(
        transiting_body="Saturn",
        natal_longitude=0.0,
        aspect_angle=0.0,
    )
    window = SimpleNamespace(
        transit=transit,
        start=start,
        end=start + datetime.timedelta(days=10),
    )

    def fake_longitude(when: datetime.datetime, body: str) -> float:
        assert body == "Saturn"
        elapsed = (when - start).total_seconds() / 86400.0
        return elapsed - 5.0

    monkeypatch.setattr(analysis, "planetary_longitude", fake_longitude)

    assert analysis.window_has_exact_hit_between(
        window,
        start + datetime.timedelta(days=4),
        start + datetime.timedelta(days=6),
    )
