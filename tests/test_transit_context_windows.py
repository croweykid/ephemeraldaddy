from __future__ import annotations

import datetime
from types import SimpleNamespace

from ephemeraldaddy.core.composite import AspectHit, BodyPosition
from ephemeraldaddy.gui.features.transits import context_windows, theme_view


UTC = datetime.timezone.utc


def _hit(transit: str, aspect: str, natal: str, *, exactness: float = 0.5) -> AspectHit:
    return AspectHit(
        a=BodyPosition(name=transit, lon_deg=0.0, layer="TRANSIT"),
        b=BodyPosition(
            name=natal,
            lon_deg=0.0,
            sign="Pisces",
            house=6,
            layer="NATAL",
        ),
        aspect=aspect,
        exactness=exactness,
        orb_deg=1.5,
        applying_separating=None,
        weight=1.0,
    )


def test_context_scanner_classifies_recent_active_and_upcoming(monkeypatch) -> None:
    center = datetime.datetime(2026, 10, 1, 12, tzinfo=UTC)
    recent_probe = center - datetime.timedelta(days=20)
    upcoming_probe = center + datetime.timedelta(days=10)

    recent_hit = _hit("Saturn", "square", "Mercury")
    active_hit = _hit("Pluto", "semisquare", "Sun", exactness=0.9)
    upcoming_hit = _hit("Jupiter", "opposition", "Moon")

    monkeypatch.setattr(context_windows, "_natal_targets", lambda _chart: ())
    monkeypatch.setattr(
        context_windows,
        "_probe_times",
        lambda *_args, **_kwargs: (recent_probe, center, upcoming_probe),
    )
    monkeypatch.setattr(
        context_windows,
        "_transiting_positions_at",
        lambda when, _location: (
            BodyPosition(name="Probe", lon_deg=(when - center).days, layer="TRANSIT"),
        ),
    )

    def fake_compute_aspects(transit_positions, _natal_targets, _rules):
        offset = int(transit_positions[0].lon_deg)
        if offset == -20:
            return [recent_hit]
        if offset == 0:
            return [active_hit]
        if offset == 10:
            return [upcoming_hit]
        return []

    monkeypatch.setattr(context_windows, "compute_aspects", fake_compute_aspects)

    def fake_window_result(_chart, _probe, _location, hit, _rules, **_kwargs):
        if hit is recent_hit:
            return SimpleNamespace(
                start=center - datetime.timedelta(days=50),
                end=center - datetime.timedelta(days=5),
                start_truncated_to_scope=False,
                end_truncated_to_scope=False,
            )
        if hit is active_hit:
            return SimpleNamespace(
                start=center - datetime.timedelta(days=100),
                end=center + datetime.timedelta(days=100),
                start_truncated_to_scope=False,
                end_truncated_to_scope=False,
            )
        return SimpleNamespace(
            start=center + datetime.timedelta(days=8),
            end=center + datetime.timedelta(days=20),
            start_truncated_to_scope=False,
            end_truncated_to_scope=False,
        )

    monkeypatch.setattr(
        context_windows,
        "find_transit_aspect_window_result",
        fake_window_result,
    )

    windows = context_windows.scan_personal_transit_context(
        SimpleNamespace(),
        center,
        (40.7, -74.0),
    )

    assert [(row.status, row.transiting_body, row.aspect_name, row.natal_body) for row in windows] == [
        (context_windows.STATUS_RECENT, "Saturn", "square", "Mercury"),
        (context_windows.STATUS_ACTIVE, "Pluto", "semisquare", "Sun"),
        (context_windows.STATUS_UPCOMING, "Jupiter", "opposition", "Moon"),
    ]


def test_context_scanner_keeps_outer_planet_minor_aspects_eligible() -> None:
    rules = context_windows.personal_transit_rules_for_mode(
        context_windows.PERSONAL_TRANSIT_MODE_LIFE_FORECAST
    )
    hits = context_windows.compute_aspects(
        [BodyPosition(name="Pluto", lon_deg=45.0, layer="TRANSIT")],
        [BodyPosition(name="Sun", lon_deg=0.0, layer="NATAL")],
        rules,
    )

    assert [(hit.a.name, hit.aspect, hit.b.name) for hit in hits] == [
        ("Pluto", "semisquare", "Sun")
    ]


def test_theme_grouping_is_nonexclusive_and_uses_factor_membership(monkeypatch) -> None:
    center = datetime.datetime(2026, 10, 1, 12, tzinfo=UTC)
    window = context_windows.TransitContextWindow(
        status=context_windows.STATUS_ACTIVE,
        transiting_body="Pluto",
        natal_body="Sun",
        aspect_name="semisquare",
        start=center - datetime.timedelta(days=10),
        end=center + datetime.timedelta(days=10),
        representative_hit=_hit("Pluto", "semisquare", "Sun"),
    )

    monkeypatch.setattr(
        theme_view,
        "THEMES",
        {
            "identity": {"label": "Identity"},
            "work": {"label": "Work"},
        },
    )

    def fake_weight(theme_key: str, property_name: str, item: object) -> float:
        memberships = {
            "identity": {("bodies", "Sun"), ("bodies", "Pluto")},
            "work": {("houses", 6)},
        }
        return 1.0 if (property_name, item) in memberships[theme_key] else 0.0

    monkeypatch.setattr(theme_view, "theme_item_weight", fake_weight)

    groups = theme_view.group_context_windows_by_theme([window])

    assert [group.theme_key for group in groups] == ["identity", "work"]
    assert all(group.windows == (window,) for group in groups)
    text = theme_view.format_theme_view_text([window])
    assert "Identity" in text
    assert "Work" in text
    assert "Pluto semisquare Sun" in text
    assert "09-21-2026 -> 10-11-2026" in text
