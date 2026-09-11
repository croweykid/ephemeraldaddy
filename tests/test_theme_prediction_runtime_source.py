from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/charts/theme_prediction_runtime.py"
).read_text(encoding="utf-8")
TRAIT_FACADE_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions.py"
).read_text(encoding="utf-8")


def test_theme_runtime_patches_app_early_bound_scheduler():
    assert 'sys.modules.get("ephemeraldaddy.gui.app")' in RUNTIME_SOURCE
    assert '"schedule_chart_render_for_active_right_panel"' in RUNTIME_SOURCE
    assert "stack.schedule_chart_render_for_active_right_panel" in RUNTIME_SOURCE


def test_theme_runtime_uses_one_context_for_score_and_norm_stratum():
    assert "prominence._activation_context(chart)" in RUNTIME_SOURCE
    assert "calculate_theme_subtheme_scores_from_context(context)" in RUNTIME_SOURCE
    assert "theme_availability_key_from_context(context)" in RUNTIME_SOURCE
    assert "theme_family_snapshot_averages_for_availability" in RUNTIME_SOURCE


def test_theme_runtime_injects_availability_strata_during_explicit_norm_rebuild():
    assert "calculate_database_theme_norms(charts)" in RUNTIME_SOURCE
    assert 'captured["extended_norms"] = extended' in RUNTIME_SOURCE
    assert "enrich_theme_snapshot_with_norms" in RUNTIME_SOURCE
    assert '"refresh_prediction_norms_snapshot"' in RUNTIME_SOURCE
    assert 'sys.modules.get("ephemeraldaddy.gui.features.controllers.db_info")' in RUNTIME_SOURCE


def test_theme_runtime_caches_scoring_context_for_chart_info():
    assert "owner._theme_prediction_activation_context = context" in RUNTIME_SOURCE
    assert "owner._theme_prediction_evidence_by_family = {}" in RUNTIME_SOURCE


def test_theme_runtime_installs_after_theme_predictions_extension():
    assert "install_theme_prediction_runtime" in TRAIT_FACADE_SOURCE
    predictions_install = TRAIT_FACADE_SOURCE.index("_install_theme_predictions(_core)")
    runtime_install = TRAIT_FACADE_SOURCE.index(
        "_install_theme_prediction_runtime(_theme_predictions)"
    )
    assert predictions_install < runtime_install
