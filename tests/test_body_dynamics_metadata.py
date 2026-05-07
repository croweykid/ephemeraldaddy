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
