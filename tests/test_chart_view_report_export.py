"""Right-panel export rules: chart medians, both Traits directions, and routing."""

from types import ModuleType, SimpleNamespace
import sys

from ephemeraldaddy.gui.features.import_export import chart_view_report as report


def test_above_chart_median_is_strict_and_includes_zero_values():
    assert report.above_chart_median({"zero": 0, "one": 1, "two": 2, "three": 3}) == [
        ("three", 3.0), ("two", 2.0),
    ]
    assert report.above_chart_median({"one": 1, "two": 2, "three": 2, "four": 4}) == [
        ("four", 4.0),
    ]
    assert report.above_chart_median({"a": 0, "b": 0}) == []
    assert report.above_chart_median({"missing": None, "nan": float("nan")}) == []


def test_chart_analytics_reports_both_dropdown_modes_without_unreliable_houses(monkeypatch):
    from ephemeraldaddy.gui.features.charts import metrics

    for name in (
        "calculate_dominant_sign_weights", "calculate_sign_prevalence_counts",
        "calculate_dominant_planet_weights", "calculate_sidereal_planet_prevalence_counts",
        "calculate_dominant_element_weights", "calculate_element_prevalence_counts",
        "calculate_dominant_nakshatra_weights", "calculate_nakshatra_prevalence_counts",
        "calculate_mode_weights", "calculate_modal_prevalence_counts",
    ):
        monkeypatch.setattr(metrics, name, lambda _chart: {
            "Low": 0, "Middle A": 1, "Middle B": 1, "High": 3,
        })
    monkeypatch.setattr(metrics, "calculate_planet_dynamics_scores", lambda _chart: {})
    monkeypatch.setattr(report, "chart_uses_houses", lambda _chart: False)
    monkeypatch.setattr(report, "_factor_explanation", lambda kind, name, chart: f"Info for {kind}/{name}")
    from ephemeraldaddy.analysis import chart_type_identifier
    monkeypatch.setattr(
        chart_type_identifier, "chart_type_summary", lambda _chart: {"shape": "splash", "patterns": []},
    )

    markdown = report.build_chart_analytics_report(SimpleNamespace())

    assert "### Dominant Signs" in markdown and "### Sign Prevalence" in markdown
    assert "### Dominant Nakshatras" in markdown and "### Nakshatra Prevalence" in markdown
    assert "### Dominant Modes" in markdown and "### Modal Prevalence" in markdown
    assert "### Dominant Houses" not in markdown and "### Quadrant Prevalence" not in markdown
    assert markdown.count("**High** — 3.00") == 10
    assert "**Middle A**" not in markdown and "**Middle B**" not in markdown
    assert "Info for sign/High" in markdown
    assert "Houses and quadrants omitted" in markdown


def test_traits_export_includes_above_and_below_norms_independent_of_ui_filter(monkeypatch):
    from ephemeraldaddy.analysis import traits

    active = [
        {"name": "Kindness", "description": "Kindness description"},
        {"name": "Skepticism", "description": "Skepticism description"},
    ]
    monkeypatch.setattr(traits, "list_traits", lambda **kwargs: active)

    # Isolate the report contract from Qt table setup; real callers use the
    # same canonical rows helper that drives the ABOVE AVG / BELOW AVG views.
    fake_core = ModuleType("ephemeraldaddy.gui.features.charts.trait_predictions_core")
    fake_core._trait_prediction_rows_from_metadata = lambda items, metadata: [
        {"name": "Kindness", "likelihood": 77, "database_average": 53,
         "deviation": 24, "direction": "above"},
        {"name": "Skepticism", "likelihood": 16, "database_average": 51,
         "deviation": -35, "direction": "below"},
    ]
    fake_core._trait_info_html = lambda trait, chart, **kwargs: (
        f"<b>{trait['name']}</b>: {trait['description']}"
    )
    monkeypatch.setitem(sys.modules, fake_core.__name__, fake_core)

    lines = report._trait_rows_report(SimpleNamespace(name="Ada"), {"above": {"Kindness"}, "below": {"Skepticism"}})
    markdown = "\n".join(lines)

    assert "**Above DB norms**" in markdown and "**Below DB norms**" in markdown
    assert "Kindness" in markdown and "Skepticism" in markdown
    assert "predicted 77.0%; DB norm 53.0%; deviation +24.0" in markdown
    assert "predicted 16.0%; DB norm 51.0%; deviation -35.0" in markdown
    assert "Kindness description" in markdown and "Skepticism description" in markdown


def test_uncomputed_traits_do_not_misrepresent_results_as_empty():
    text = "\n".join(report._trait_rows_report(SimpleNamespace(), None))
    assert "Above DB norms: unavailable" in text
    assert "Below DB norms: unavailable" in text
    assert "Calculate Traits" in text


def test_primary_chart_export_inserts_right_panel_before_raw_data(monkeypatch):
    from ephemeraldaddy.gui.features.import_export import chart_markdown

    monkeypatch.setattr(report, "build_chart_view_report", lambda chart, **kwargs: (
        "## Chart Analytics\n\nAbove chart median: Sagittarius\n\n"
        "## Predictions\n\nAbove DB norms: Kindness\nBelow DB norms: Skepticism"
    ))
    chart = SimpleNamespace(
        name="Ada", dt=None, alias="", birth_place="", lat=0.0, lon=0.0,
        positions={}, aspects=[], houses=None, birthtime_unknown=True, retcon_time_used=False,
        as_dict=lambda: {"name": "Ada"},
    )
    markdown = chart_markdown.build_chart_export_markdown(chart)
    assert markdown.index("## Aspects") < markdown.index("## Chart Analytics")
    assert markdown.index("## Predictions") < markdown.index("## Raw Chart Data")
    assert "Below DB norms: Skepticism" in markdown


def test_primary_gui_export_uses_requested_chart_context():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    assert "render_markdown=lambda chart: build_chart_export_markdown(" in source
    assert "collect_chart_export_prediction_context(self, chart)" in source
