from types import SimpleNamespace

from ephemeraldaddy.core import db


def test_body_dynamics_roles_normalize_ui_labels():
    raw_roles = {
        "Sun": "enabler",
        "Moon": "antagonizer",
        "Saturn": "escalating antagonist",
        "Pluto": "escalating enabler",
        "NotAPlanet": "enabler",
    }

    assert db._parse_body_dynamics_roles(raw_roles) == {
        "Sun": "enabler",
        "Moon": "antagonist",
        "Saturn": "escalator",
        "Pluto": "escalator",
    }


def test_resolves_body_dynamics_roles_from_chart_analytics_scores(monkeypatch):
    def fake_scores(_chart):
        return {
            "Sun": {"enabling": 3.0, "antagonizing": 1.0, "escalating": 2.0},
            "Moon": {"enabling": 1.0, "antagonizing": 4.0, "escalating": 2.0},
            "Saturn": {"enabling": 2.0, "antagonizing": 1.0, "escalating": 3.0},
        }

    import ephemeraldaddy.analysis.body_dynamics_reworked as body_dynamics

    monkeypatch.setattr(body_dynamics, "calculate_planet_dynamics_scores", fake_scores)
    chart = SimpleNamespace(positions={"Sun": 0.0, "Moon": 1.0, "Saturn": 2.0})

    roles = db._resolve_body_dynamics_roles(chart)

    assert roles == {
        "Sun": "enabler",
        "Moon": "antagonist",
        "Saturn": "escalator",
    }
    assert chart.body_dynamics_roles == roles


class _FakeCombo:
    def __init__(self, value):
        self.value = value
        self.reset_count = 0

    def currentData(self):
        return self.value

    def setCurrentIndex(self, index):
        self.reset_count += 1
        if index == 0:
            self.value = "Any"


class _FakeRadio:
    def __init__(self, checked=False):
        self.checked = checked

    def isChecked(self):
        return self.checked

    def setChecked(self, checked):
        self.checked = checked


def _body_dynamics_filter(body, role, mode="and"):
    return {
        "body": _FakeCombo(body),
        "role": _FakeCombo(role),
        "and": _FakeRadio(mode == "and"),
        "or": _FakeRadio(mode == "or"),
        "exclude": _FakeRadio(mode == "exclude"),
    }


def test_database_view_body_dynamics_filter_modes():
    from ephemeraldaddy.gui.dbv_search_panel import chart_matches_body_dynamics_filters

    window = SimpleNamespace(_body_dynamics_filters=[])
    chart = SimpleNamespace(
        body_dynamics_roles={
            "Saturn": "antagonist",
            "Sun": "enabler",
            "Mars": "escalator",
        }
    )

    assert chart_matches_body_dynamics_filters(
        window,
        chart,
        [_body_dynamics_filter("Saturn", "antagonist", "and")],
    )
    assert chart_matches_body_dynamics_filters(
        window,
        chart,
        [
            _body_dynamics_filter("Moon", "enabler", "or"),
            _body_dynamics_filter("Mars", "escalator", "or"),
        ],
    )
    assert not chart_matches_body_dynamics_filters(
        window,
        chart,
        [_body_dynamics_filter("Sun", "enabler", "exclude")],
    )



def test_body_dynamics_role_metadata_round_trips_with_lilith_mode(monkeypatch):
    import json

    monkeypatch.setattr(db, "load_lilith_mode", lambda: "Natural Lilith")
    payload = db._serialize_body_dynamics_roles({"Sun": "enabler", "Moon": "antagonist"})
    assert json.loads(payload)["__lilith_mode"] == "Natural Lilith"
    assert db._body_dynamics_roles_mode_from_payload(payload) == "Natural Lilith"
    assert db._parse_body_dynamics_roles(payload) == {"Sun": "enabler", "Moon": "antagonist"}
    assert db._body_dynamics_roles_mode_from_payload('{"Sun":"enabler"}') is None


def test_body_dynamics_metadata_recalculates_for_current_lilith_mode(monkeypatch):
    from ephemeraldaddy.analysis import body_dynamics_reworked
    from ephemeraldaddy.gui.features.charts.chart_analytics_panel import (
        body_dynamics_roles_for_chart,
    )
    from ephemeraldaddy.gui.dbv_search_panel import _body_dynamics_filter_matches

    mode = {"selected": "Osculating Lilith"}
    calls = []
    monkeypatch.setattr(db, "load_lilith_mode", lambda: mode["selected"])

    def calculate(chart):
        calls.append(mode["selected"])
        if mode["selected"] == "Osculating Lilith":
            return {"Sun": {"enabling": 5.0, "antagonizing": 1.0, "escalating": 0.0}}
        return {"Sun": {"enabling": 1.0, "antagonizing": 5.0, "escalating": 0.0}}

    monkeypatch.setattr(body_dynamics_reworked, "calculate_planet_dynamics_scores", calculate)
    chart = SimpleNamespace(
        positions={"Sun": 25.0},
        body_dynamics_roles={"Sun": "antagonist"},
        _body_dynamics_roles_lilith_mode="Mean Lilith",
        planet_dynamics_scores={"Sun": {"enabling": 0.0, "antagonizing": 99.0}},
    )
    assert body_dynamics_roles_for_chart(chart) == {"Sun": "enabler"}
    assert chart._body_dynamics_roles_lilith_mode == "Osculating Lilith"
    assert calls == ["Osculating Lilith"]
    assert _body_dynamics_filter_matches(chart, _body_dynamics_filter("Sun", "enabler"))
    assert calls == ["Osculating Lilith"]  # Reuse mode-current metadata cheaply.

    mode["selected"] = "Natural Lilith"
    assert not _body_dynamics_filter_matches(chart, _body_dynamics_filter("Sun", "enabler"))
    assert chart.body_dynamics_roles == {"Sun": "antagonist"}
    assert chart._body_dynamics_roles_lilith_mode == "Natural Lilith"
    assert calls == ["Osculating Lilith", "Natural Lilith"]
    assert body_dynamics_roles_for_chart(chart) == {"Sun": "antagonist"}


def test_legacy_unversioned_roles_are_not_trusted_for_real_chart(monkeypatch):
    from ephemeraldaddy.analysis import body_dynamics_reworked

    monkeypatch.setattr(db, "load_lilith_mode", lambda: "Osculating Lilith")
    monkeypatch.setattr(
        body_dynamics_reworked,
        "calculate_planet_dynamics_scores",
        lambda chart: {"Sun": {"enabling": 3.0, "antagonizing": 0.0, "escalating": 0.0}},
    )
    chart = SimpleNamespace(
        positions={"Sun": 15.0},
        body_dynamics_roles={"Sun": "antagonist"},
    )
    assert db.current_body_dynamics_roles_for_chart(chart) == {"Sun": "enabler"}
    assert chart._body_dynamics_roles_lilith_mode == "Osculating Lilith"
