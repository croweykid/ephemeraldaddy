import datetime
from types import SimpleNamespace

from ephemeraldaddy.gui.features.import_export.chart_markdown import (
    build_chart_export_markdown,
)


def _chart(**overrides):
    values = {
        "name": "Ada",
        "alias": "Countess",
        "dt": datetime.datetime(1815, 12, 10, 20, 15),
        "birth_place": "London",
        "lat": 51.5074,
        "lon": -0.1278,
        "birthtime_unknown": False,
        "retcon_time_used": False,
        "rectification_range_used": False,
        "is_placeholder": False,
        "positions": {"Sun": 258.5, "AS": 12.0},
        "houses": [float(index * 30) for index in range(12)],
        "aspects": [],
        "dominant_planet_weights": {"Sun": 1.0},
        "used_utc_fallback": False,
    }
    values.update(overrides)
    chart = SimpleNamespace(**values)
    chart.as_dict = lambda: {"name": chart.name, "positions": chart.positions}
    return chart


def test_markdown_export_contains_metadata_positions_houses_and_raw_data():
    markdown = build_chart_export_markdown(_chart())

    assert "# Chart Export: Ada" in markdown
    assert "| Alias | Countess |" in markdown
    assert "| 🐣Date | 1815-12-10 |" in markdown
    assert "| Sun | 18°30' Sagittarius | Sagittarius | 9 |" in markdown
    assert "## House Cusps" in markdown
    assert '"name": "Ada"' in markdown


def test_unknown_time_export_hides_angles_and_house_cusps():
    markdown = build_chart_export_markdown(
        _chart(birthtime_unknown=True, houses=None)
    )

    assert "| 🐣Time | Unknown |" in markdown
    assert "| AS | Unknown (🐣Time unknown) | Unknown | — |" in markdown
    assert "## House Cusps" not in markdown


def test_markdown_export_sorts_and_formats_aspects_without_window_state():
    chart = _chart(
        positions={"Sun": 10.0, "Moon": 11.0},
        dominant_planet_weights={"Sun": 2.0, "Moon": 1.0},
        aspects=[
            {
                "p1": "Sun",
                "p2": "Moon",
                "type": "conjunction",
                "angle": 1.0,
                "delta": -1.0,
            }
        ],
    )

    markdown = build_chart_export_markdown(chart)

    assert "| Sun | Conjunction | Moon | 01°00' | -01°00' |" in markdown
