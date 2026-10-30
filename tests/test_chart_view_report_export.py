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




def test_theme_predictions_use_availability_matched_chart_shares(monkeypatch):
    from ephemeraldaddy.analysis import theme_prominence
    from ephemeraldaddy.analysis import theme_norms
    from ephemeraldaddy.gui.features.charts import prediction_norms_snapshot
    from ephemeraldaddy.core.theme_reference import THEME_FAMILIES, THEMES

    first_family, second_family = list(THEME_FAMILIES)[:2]
    first_theme = next(key for key, item in THEMES.items() if item["family"] == first_family)
    second_theme = next(key for key, item in THEMES.items() if item["family"] == second_family)
    scores = {first_theme: 90.0, second_theme: 10.0}
    monkeypatch.setattr(
        theme_prominence, "_activation_context",
        lambda chart: {"houses_available": chart.houses_available, "hd": {"available": False}, "bazi_available": False},
    )
    monkeypatch.setattr(theme_norms, "calculate_theme_subtheme_scores_from_context", lambda _context: scores)

    no_houses = "houses:0|hd:0|bazi:0"
    with_houses = "houses:1|hd:0|bazi:0"
    # Both strata exist, deliberately disagreeing about above/below direction.
    family_means_no = {key: 0.0 for key in THEME_FAMILIES}
    family_means_no[first_family] = 40.0
    family_means_no[second_family] = 30.0
    family_means_yes = dict(family_means_no, **{first_family: 95.0, second_family: 5.0})
    subtheme_means = {key: 0.0 for key in THEMES}

    snapshot = {
        "theme_family_definition_signature": theme_prominence.theme_definition_signature(),
        theme_norms.THEME_CHART_SHARE_SCHEMA_FIELD: theme_norms.THEME_CHART_SHARE_SCHEMA_VERSION,
        theme_norms.THEME_NORMS_AVAILABILITY_SCHEMA_FIELD: theme_norms.THEME_NORMS_AVAILABILITY_SCHEMA_VERSION,
        theme_norms.THEME_FAMILY_AVAILABILITY_ROWS_FIELD: {
            key: {name: 0.0 for name in THEME_FAMILIES} for key in (no_houses, with_houses)
        },
        theme_norms.THEME_SUBTHEME_SHARE_AVERAGES_FIELD: {
            key: subtheme_means for key in (no_houses, with_houses)
        },
        theme_norms.THEME_SUBTHEME_SHARE_VALUES_FIELD: {
            key: {name: [0.0] for name in THEMES} for key in (no_houses, with_houses)
        },
        theme_norms.THEME_FAMILY_SHARE_AVERAGES_FIELD: {
            no_houses: family_means_no, with_houses: family_means_yes,
        },
        theme_norms.THEME_FAMILY_SHARE_VALUES_FIELD: {
            key: {name: [0.0] for name in THEME_FAMILIES} for key in (no_houses, with_houses)
        },
        theme_norms.THEME_FACTOR_ACTIVATION_VALUES_FIELD: {
            key: {"presence": [0.0]} for key in (no_houses, with_houses)
        },
    }
    monkeypatch.setattr(prediction_norms_snapshot, "load_prediction_norms_snapshot", lambda: snapshot)

    unknown = "\n".join(report._theme_report(SimpleNamespace(houses_available=False)))
    known = "\n".join(report._theme_report(SimpleNamespace(houses_available=True)))
    first_label = THEME_FAMILIES[first_family]["label"]
    second_label = THEME_FAMILIES[second_family]["label"]

    assert f"{first_label}: 90.0% of chart" in unknown
    assert "Above DB norms:" in unknown and "Below DB norms:" in unknown
    assert f"{first_label} (family): 90.0% of chart vs matched DB share 40.0% (+50.0 pp)" in unknown
    assert f"{second_label} (family): 10.0% of chart vs matched DB share 30.0% (-20.0 pp)" in unknown
    assert f"{first_label} (family): 90.0% of chart vs matched DB share 95.0% (-5.0 pp)" in known
    assert f"{second_label} (family): 10.0% of chart vs matched DB share 5.0% (+5.0 pp)" in known


def test_theme_export_rejects_legacy_and_mismatched_availability_norms(monkeypatch):
    from ephemeraldaddy.analysis import theme_prominence
    from ephemeraldaddy.gui.features.charts import prediction_norms_snapshot
    monkeypatch.setattr(
        theme_prominence, "_activation_context",
        lambda _chart: {"houses_available": False, "hd": {"available": False}, "bazi_available": False},
    )
    monkeypatch.setattr(prediction_norms_snapshot, "load_prediction_norms_snapshot", lambda: {
        "theme_family_definition_signature": theme_prominence.theme_definition_signature(),
        "theme_family_raw_averages": {key: 50.0 for key in theme_prominence.THEME_FAMILIES},
    })
    text = "\n".join(report._theme_report(SimpleNamespace()))
    assert "Above DB norms: unavailable." in text
    assert "Below DB norms: unavailable." in text
    assert "predates availability-stratified Theme baselines" in text


def test_statblock_requires_complete_selected_baseline(monkeypatch):
    from ephemeraldaddy.analysis.dnd import dnd_class_axes_v2
    from ephemeraldaddy.gui.features.charts import dnd_predictions_core

    monkeypatch.setattr(report, "_theme_report", lambda _chart: [])
    monkeypatch.setattr(dnd_predictions_core, "_collect_ranked_class_payloads", lambda _chart: ({}, []))
    monkeypatch.setattr(dnd_predictions_core, "_collect_ranked_species_payloads", lambda _chart: [])
    calls = []

    def scorer(chart, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            scores={"STR": 16, "DEX": 13, "CON": 10, "INT": 9, "WIS": 7, "CHA": 5},
            modifiers={"STR": 3, "DEX": 1, "CON": 0, "INT": -1, "WIS": -2, "CHA": -3},
        )

    monkeypatch.setattr(dnd_class_axes_v2, "score_dnd_statblock", scorer)
    chart = SimpleNamespace(is_placeholder=False, birthtime_unknown=True, positions={}, aspects=[])

    missing = report.build_chart_predictions_report(chart, stat_norm_averages={})
    assert "Statblock unavailable: selected DB Norms lack a complete stat baseline." in missing
    assert "Class predictions above chart median" in missing
    assert not calls

    invalid = report.build_chart_predictions_report(
        chart,
        stat_norm_averages={
            "STR": 1, "DEX": 1, "CON": 1, "INT": 1, "WIS": 1, "CHA": float("nan"),
        },
    )
    assert "Statblock unavailable" in invalid
    assert not calls

    norms = {key: float(i + 1) for i, key in enumerate(("STR", "DEX", "CON", "INT", "WIS", "CHA"))}
    exported = report.build_chart_predictions_report(chart, stat_norm_averages=norms)
    assert calls == [{"db_norm_averages": norms}]
    assert "STR=16" in exported
    assert "modifier +3" in exported


def test_alignment_export_rejects_stale_uid_and_norm_keys(monkeypatch):
    from ephemeraldaddy.gui.features.charts import dnd_predictions_core as core

    trait_items = [{"name": "Good"}, {"name": "Evil"}, {"name": "Lawful"}, {"name": "Chaotic"}]
    monkeypatch.setattr(core, "_dnd_alignment_trait_items", lambda: trait_items)
    monkeypatch.setattr(core, "_dnd_alignment_trait_name", lambda trait: trait["name"])
    monkeypatch.setattr(
        core, "_dnd_alignment_cache_key",
        lambda owner, chart: (chart.birth_state, "dnd_alignment_norms:snapshot:selected"),
    )
    owner = SimpleNamespace(
        _prediction_norm_snapshot_trait_averages=lambda _traits: {
            item["name"]: 50 for item in trait_items
        },
    )
    parts = {item["name"].lower(): {"deviation": 10.0} for item in trait_items}
    chart = SimpleNamespace(
        chart_uid="CURRENT-UID",
        birth_state="original",
        _dnd_alignment_score_parts_cache={
            "chart_uid": "CURRENT-UID",
            "key": ("original", "dnd_alignment_norms:snapshot:selected"),
            "parts": parts,
        },
    )

    assert report._current_alignment_scores(owner, chart) == {
        item["name"].lower(): 10.0 for item in trait_items
    }
    chart.birth_state = "changed"
    assert report._current_alignment_scores(owner, chart) is None
    chart.birth_state = "original"
    chart._dnd_alignment_score_parts_cache["chart_uid"] = "OTHER-UID"
    assert report._current_alignment_scores(owner, chart) is None
    chart._dnd_alignment_score_parts_cache["chart_uid"] = "CURRENT-UID"
    chart._dnd_alignment_score_parts_cache["key"] = (
        "original", "dnd_alignment_norms:snapshot:previous",
    )
    assert report._current_alignment_scores(owner, chart) is None
    chart._dnd_alignment_score_parts_cache["key"] = (
        "original", "dnd_alignment_norms:snapshot:selected",
    )
    owner._prediction_norm_snapshot_trait_averages = lambda _traits: {}
    assert report._current_alignment_scores(owner, chart) is None


def test_placeholder_predictions_do_not_make_ascribed_or_db_comparisons():
    chart = SimpleNamespace(is_placeholder=True)
    text = report.build_chart_predictions_report(chart)
    assert "Predictions unavailable for placeholder/hypothetical charts." in text
    assert "Above DB norms: unavailable." in text
    assert "Below DB norms: unavailable." in text
    assert "### Fantasy RPG" not in text

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
