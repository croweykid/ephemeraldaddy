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
