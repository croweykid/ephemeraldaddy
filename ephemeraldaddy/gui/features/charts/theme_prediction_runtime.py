"""Runtime integration fixes for semantic Theme Predictions.

``app.py`` binds several right-panel/snapshot functions before the modular
Trait/Theme facade is imported.  Theme Predictions therefore cannot rely on
replacing only attributes on the source modules: the already-imported app
globals must be updated too.

This installer also keeps Theme ``vs DB`` comparisons denominator-compatible.
The chart's activation context is built once for a render, used both for the
score and for selecting the matching availability-stratified snapshot baseline.
"""

from __future__ import annotations

from contextvars import ContextVar
import sys
from typing import Any, Mapping

from ephemeraldaddy.analysis import theme_prominence as prominence
from ephemeraldaddy.analysis.theme_norms import (
    calculate_database_theme_family_baselines,
    calculate_theme_subtheme_scores_from_context,
    enrich_theme_snapshot_with_availability_baselines,
    theme_availability_key_from_context,
    theme_family_snapshot_averages_for_availability,
    theme_snapshot_unavailability_reason_for_availability,
)


_ACTIVE_THEME_CONTEXT: ContextVar[Mapping[str, Any] | None] = ContextVar(
    "ephemeraldaddy_active_theme_context",
    default=None,
)
_ACTIVE_THEME_CONTEXT_ERROR: ContextVar[Exception | None] = ContextVar(
    "ephemeraldaddy_active_theme_context_error",
    default=None,
)


def _loaded_app_module() -> Any | None:
    return sys.modules.get("ephemeraldaddy.gui.app")


def _patch_bound_app_scheduler() -> None:
    """Point app.py's early-bound scheduler global at the installed wrapper."""
    from ephemeraldaddy.gui.features.charts import cv_right_panel_stack as stack

    app_module = _loaded_app_module()
    if app_module is not None:
        setattr(
            app_module,
            "schedule_chart_render_for_active_right_panel",
            stack.schedule_chart_render_for_active_right_panel,
        )


def _install_availability_matched_render(theme_predictions: Any) -> None:
    if getattr(theme_predictions, "_ephemeraldaddy_theme_availability_render_installed", False):
        return

    original_render = theme_predictions.render_theme_predictions
    original_subtheme_scores = theme_predictions.calculate_theme_subtheme_scores
    original_unavailability_reason = theme_predictions.theme_snapshot_unavailability_reason

    def calculate_theme_subtheme_scores(chart: Any) -> dict[str, float]:
        context = _ACTIVE_THEME_CONTEXT.get()
        if context is None:
            return original_subtheme_scores(chart)
        return calculate_theme_subtheme_scores_from_context(context)

    def theme_family_snapshot_averages(snapshot: Mapping[str, Any] | None) -> dict[str, float]:
        context = _ACTIVE_THEME_CONTEXT.get()
        if context is None:
            # A Theme comparison without a chart-specific denominator profile is
            # intentionally unavailable rather than falling back to mixed norms.
            return {}
        return theme_family_snapshot_averages_for_availability(
            snapshot,
            theme_availability_key_from_context(context),
        )

    def theme_snapshot_unavailability_reason(snapshot: Mapping[str, Any] | None) -> str:
        context = _ACTIVE_THEME_CONTEXT.get()
        context_error = _ACTIVE_THEME_CONTEXT_ERROR.get()
        if context_error is not None:
            return f"Theme scoring context failed: {context_error}"
        if context is None:
            return original_unavailability_reason(snapshot)
        return theme_snapshot_unavailability_reason_for_availability(
            snapshot,
            theme_availability_key_from_context(context),
        )

    def render_theme_predictions(owner: Any, chart: Any | None) -> None:
        if chart is None or bool(
            getattr(owner, "_is_placeholder_chart", lambda _chart: False)(chart)
        ):
            owner._theme_prediction_activation_context = None
            owner._theme_prediction_evidence_by_family = {}
            original_render(owner, chart)
            return

        context: Mapping[str, Any] | None = None
        context_error: Exception | None = None
        try:
            context = prominence._activation_context(chart)
        except Exception as exc:  # original renderer converts failures to UI status
            context_error = exc

        # The Chart Information presenter reuses this exact scoring context;
        # changing rows must not rebuild Human Design, BaZi, or house dominance.
        owner._theme_prediction_activation_context = context
        owner._theme_prediction_evidence_by_family = {}

        context_token = _ACTIVE_THEME_CONTEXT.set(context)
        error_token = _ACTIVE_THEME_CONTEXT_ERROR.set(context_error)
        try:
            original_render(owner, chart)
        finally:
            _ACTIVE_THEME_CONTEXT_ERROR.reset(error_token)
            _ACTIVE_THEME_CONTEXT.reset(context_token)

    theme_predictions.calculate_theme_subtheme_scores = calculate_theme_subtheme_scores
    theme_predictions.theme_family_snapshot_averages = theme_family_snapshot_averages
    theme_predictions.theme_snapshot_unavailability_reason = theme_snapshot_unavailability_reason
    theme_predictions.render_theme_predictions = render_theme_predictions
    theme_predictions._ephemeraldaddy_theme_availability_render_installed = True


def _install_availability_stratified_snapshot_refresh() -> None:
    from ephemeraldaddy.gui.features.charts import prediction_norms_snapshot as snapshots

    if getattr(snapshots, "_ephemeraldaddy_theme_availability_norms_installed", False):
        return

    original_refresh = snapshots.refresh_prediction_norms_snapshot

    def refresh_prediction_norms_snapshot(
        owner: Any,
        *,
        user_initiated: bool = False,
    ) -> dict[str, Any]:
        captured: dict[str, Any] = {}
        original_calculator = snapshots.calculate_database_theme_family_averages
        original_save = snapshots._core.save_prediction_norms_snapshot

        def calculate_database_theme_family_averages(charts: list[Any]) -> dict[str, float]:
            overall, by_availability, chart_counts = (
                calculate_database_theme_family_baselines(charts)
            )
            captured["by_availability"] = by_availability
            captured["chart_counts"] = chart_counts
            return overall

        def save_prediction_norms_snapshot(payload: dict[str, Any], path: Any) -> Any:
            by_availability = captured.get("by_availability", {})
            chart_counts = captured.get("chart_counts", {})
            enriched = enrich_theme_snapshot_with_availability_baselines(
                payload,
                by_availability,
                chart_counts,
            )
            return original_save(enriched, path)

        snapshots.calculate_database_theme_family_averages = (
            calculate_database_theme_family_averages
        )
        snapshots._core.save_prediction_norms_snapshot = save_prediction_norms_snapshot
        try:
            return original_refresh(owner, user_initiated=user_initiated)
        finally:
            snapshots.calculate_database_theme_family_averages = original_calculator
            snapshots._core.save_prediction_norms_snapshot = original_save

    snapshots.refresh_prediction_norms_snapshot = refresh_prediction_norms_snapshot
    snapshots._core.refresh_prediction_norms_snapshot = refresh_prediction_norms_snapshot
    snapshots._ephemeraldaddy_theme_availability_norms_installed = True

    # app.py imported the facade function before Trait/Theme installers ran.
    app_module = _loaded_app_module()
    if app_module is not None:
        setattr(
            app_module,
            "refresh_prediction_norms_snapshot",
            refresh_prediction_norms_snapshot,
        )
    db_info_module = sys.modules.get("ephemeraldaddy.gui.features.controllers.db_info")
    if db_info_module is not None:
        setattr(
            db_info_module,
            "refresh_prediction_norms_snapshot",
            refresh_prediction_norms_snapshot,
        )


def install_theme_prediction_runtime(theme_predictions: Any) -> None:
    """Install scheduler binding and denominator-compatible Theme comparisons."""
    if getattr(theme_predictions, "_ephemeraldaddy_theme_runtime_installed", False):
        return
    _patch_bound_app_scheduler()
    _install_availability_matched_render(theme_predictions)
    _install_availability_stratified_snapshot_refresh()
    theme_predictions._ephemeraldaddy_theme_runtime_installed = True
