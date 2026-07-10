from pathlib import Path
import sys
import types

from ephemeraldaddy.analysis.hd_incarnation_crosses import (
    HD_INCARNATION_CROSSES,
    find_cross_by_name,
    get_cross_theme_description,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_distinguishing_factor_html_does_not_truncate_significant_factors():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/distinguishing_factors.py").read_text()

    assert "for factor in factors:" in source
    assert "for factor in factors[:12]:" not in source


def test_incarnation_cross_info_uses_cross_type_for_angle_description():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert 'angle = str(cross_entry.get("cross_type", "")).strip() or "Unknown"' in source
    assert 'get_cross_type_description(angle)' in source
    assert 'cross_entry.get("angle"' not in source


def test_incarnation_cross_lookup_accepts_chart_display_label_with_gates():
    cross = find_cross_by_name("Right Angle Cross of the Sphinx 4 (gates 1/2 • 7/13)")

    assert cross is not None
    assert cross["full_name"] == "Right Angle Cross of the Sphinx 4"


def test_all_incarnation_cross_themes_have_descriptions():
    missing = sorted(
        {
            str(entry["theme"])
            for entry in HD_INCARNATION_CROSSES
            if not get_cross_theme_description(str(entry["theme"]))
        }
    )

    assert missing == []


def test_database_distinction_repeated_gate_score_weights_extra_repetitions(monkeypatch):
    from types import SimpleNamespace

    hd_module = types.ModuleType("ephemeraldaddy.analysis.human_design")
    hd_module.build_human_design_result = lambda _chart: None
    sys.modules.setdefault("ephemeraldaddy.analysis.human_design", hd_module)
    hd_reference_module = types.ModuleType("ephemeraldaddy.analysis.human_design_reference")
    hd_reference_module.GATE_COLORS = {}
    hd_reference_module.HD_LINE_COLORS = {}
    sys.modules.setdefault("ephemeraldaddy.analysis.human_design_reference", hd_reference_module)
    style_module = types.ModuleType("ephemeraldaddy.gui.style")
    style_module.CHART_DATA_HIGHLIGHT_COLOR = "#fff"
    sys.modules.setdefault("ephemeraldaddy.gui.style", style_module)

    from ephemeraldaddy.gui.features.charts import distinguishing_factors

    query_profile = distinguishing_factors.DatabaseDistinctionProfile(
        factors=(),
        concentration_traits=(),
        repeated_gate_counts=((20, 3), (25, 2)),
        norm_count=5,
    )

    def fake_duplicate_gate_lines(chart):
        return {
            "triple_match": [(20, [1, 2, 3])],
            "double_match": [(25, [1, 2])],
        }.get(chart.name, [])

    monkeypatch.setattr(distinguishing_factors, "_duplicate_human_design_gate_lines", fake_duplicate_gate_lines)

    triple_score, triple_components = distinguishing_factors.database_distinction_similarity_score(
        query_profile,
        SimpleNamespace(name="triple_match"),
        [],
    )
    double_score, double_components = distinguishing_factors.database_distinction_similarity_score(
        query_profile,
        SimpleNamespace(name="double_match"),
        [],
    )

    assert triple_components["repeated_hd_gates"] == 3 / 5
    assert double_components["repeated_hd_gates"] == 2 / 5
    assert triple_score > double_score


def test_distinguishing_factors_include_raw_weight_outliers(monkeypatch):
    from types import SimpleNamespace

    from ephemeraldaddy.gui.features.charts import distinguishing_factors

    metric_group = distinguishing_factors._MetricGroup(
        "demo",
        "demo weight",
        lambda chart: {"alpha": chart.raw_weight, "beta": chart.total_weight - chart.raw_weight},
        ("alpha", "beta"),
    )
    monkeypatch.setattr(distinguishing_factors, "_metric_groups", lambda _chart: (metric_group,))
    monkeypatch.setattr(distinguishing_factors, "MIN_NORM_SAMPLE_SIZE", 5)

    target = SimpleNamespace(raw_weight=20.0, total_weight=1000.0)
    norms = [
        SimpleNamespace(raw_weight=value, total_weight=100.0)
        for value in (1.0, 2.0, 3.0, 4.0, 5.0)
    ]

    factors, norm_count = distinguishing_factors.find_distinguishing_factors(target, norms)

    assert norm_count == 5
    raw_factor = next(factor for factor in factors if factor.raw_label == "alpha")
    assert raw_factor.basis == "raw"
    assert raw_factor.raw_z_score >= distinguishing_factors.DISTINGUISHING_Z_THRESHOLD


def test_distinguishing_metric_payload_persists_raw_weights(monkeypatch):
    from types import SimpleNamespace

    from ephemeraldaddy.gui.features.charts import distinguishing_factors

    metric_group = distinguishing_factors._MetricGroup(
        "demo",
        "demo weight",
        lambda _chart: {"alpha": 25.0, "beta": 75.0},
        ("alpha", "beta"),
    )
    monkeypatch.setattr(distinguishing_factors, "_metric_groups", lambda _chart: (metric_group,))

    payload = distinguishing_factors.distinguishing_metric_payload_for_chart(SimpleNamespace())

    assert payload["groups"]["demo"]["alpha"]["share"] == 0.25
    assert payload["groups"]["demo"]["alpha"]["raw"] == 25.0
