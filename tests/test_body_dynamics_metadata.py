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
