"""Runtime integration for semantic Theme Predictions.

``app.py`` binds several right-panel/snapshot functions before the modular
Trait/Theme facade is imported. Theme Predictions therefore update those
already-imported bindings here as well as the source modules.

Theme DB comparisons remain denominator-compatible: every chart is compared
only with charts having the same houses/Human Design/BaZi availability profile.
"""

from __future__ import annotations

from contextvars import ContextVar
import sys
from typing import Any, Callable, Mapping

from ephemeraldaddy.analysis import theme_prominence as prominence
from ephemeraldaddy.analysis.theme_norms import (
    calculate_database_theme_norms,
    calculate_theme_chart_shares,
    calculate_theme_subtheme_scores_from_context,
    empirical_percentile,
    enrich_theme_snapshot_with_availability_baselines,
    format_theme_percentile,
    theme_availability_key_from_context,
    theme_chart_share_norms_for_availability,
    theme_chart_share_unavailability_reason,
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

_THEME_FAMILY_COLORS = {
    "self_agency_power": "#ff8a80",
    "mind_language_truth": "#7ec8ff",
    "relationship_attachment_society": "#f3a6d8",
    "material_life_work_survival": "#d8bd72",
    "shadow_crisis_transformation": "#bd9cff",
    "change_boundaries_disappearance": "#77d8ca",
    "imagination_expanded_perspective": "#a9d77d",
}


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


def _direction_for_deviation(deviation: float) -> str:
    threshold = float(prominence.THEME_DEVIATION_ASSIGNMENT_THRESHOLD)
    if deviation >= threshold:
        return "above"
    if deviation <= -threshold:
        return "below"
    return "neutral"


def _assign_fallback_directions(rows: list[dict[str, Any]]) -> set[str]:
    """Keep either direction useful when no row clears the five-point threshold."""
    fallback: set[str] = set()
    for direction, predicate, reverse in (
        ("above", lambda value: value > 0.0, True),
        ("below", lambda value: value < 0.0, False),
    ):
        if any(row.get("direction") == direction for row in rows):
            continue
        candidates = [row for row in rows if predicate(float(row.get("deviation", 0.0)))]
        candidates.sort(key=lambda row: float(row.get("deviation", 0.0)), reverse=reverse)
        for row in candidates[:5]:
            row["direction"] = direction
        if candidates:
            fallback.add(direction)
    return fallback


def _chart_share_rows(
    subtheme_scores: Mapping[str, float],
    norms: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, float], dict[str, float], set[str]]:
    subtheme_shares, family_shares = calculate_theme_chart_shares(subtheme_scores)
    subtheme_means = norms.get("subtheme_means", {})
    subtheme_values = norms.get("subtheme_values", {})
    family_means = norms.get("family_means", {})
    family_values = norms.get("family_values", {})

    rows: list[dict[str, Any]] = []
    for family_key, family in prominence.THEME_FAMILIES.items():
        family_share = float(family_shares.get(family_key, 0.0))
        try:
            family_mean = float(family_means[family_key])
        except (KeyError, TypeError, ValueError):
            family_mean = None
        if family_mean is not None:
            deviation = family_share - family_mean
            percentile = empirical_percentile(
                family_share,
                family_values.get(family_key, ()),
            )
            rows.append(
                {
                    "key": family_key,
                    "family_key": family_key,
                    "theme_key": None,
                    "kind": "family",
                    "label": str(family.get("label", family_key)),
                    "score": family_share,
                    "db_average": family_mean,
                    "deviation": deviation,
                    "percentile": percentile,
                    "direction": _direction_for_deviation(deviation),
                    "color": _THEME_FAMILY_COLORS.get(family_key, "#e6e6e6"),
                }
            )

        for theme_key in prominence.themes_in_family(family_key):
            theme_share = float(subtheme_shares.get(theme_key, 0.0))
            try:
                theme_mean = float(subtheme_means[theme_key])
            except (KeyError, TypeError, ValueError):
                continue
            deviation = theme_share - theme_mean
            percentile = empirical_percentile(
                theme_share,
                subtheme_values.get(theme_key, ()),
            )
            theme = prominence.THEMES.get(theme_key, {})
            rows.append(
                {
                    "key": family_key,
                    "family_key": family_key,
                    "theme_key": theme_key,
                    "kind": "subtheme",
                    "label": str(theme.get("label", theme_key)),
                    "score": theme_share,
                    "db_average": theme_mean,
                    "deviation": deviation,
                    "percentile": percentile,
                    "direction": _direction_for_deviation(deviation),
                    "color": _THEME_FAMILY_COLORS.get(family_key, "#e6e6e6"),
                }
            )

    fallback_directions = _assign_fallback_directions(rows)
    return rows, subtheme_shares, family_shares, fallback_directions


def _install_theme_table_semantics(theme_predictions: Any) -> None:
    """Teach the existing compact table model about mixed family/subtheme rows."""
    if getattr(theme_predictions, "_ephemeraldaddy_theme_share_table_installed", False):
        return

    model_class = theme_predictions._ThemePredictionRowsModel
    proxy_class = theme_predictions._ThemePredictionFilterModel
    model_class._HEADERS = ("Theme", "% of chart", "vs DB")
    scope_role = int(theme_predictions.Qt.UserRole) + 34
    percentile_role = int(theme_predictions.Qt.UserRole) + 35
    theme_predictions.THEME_ROW_SCOPE_ROLE = scope_role
    theme_predictions.THEME_ROW_PERCENTILE_ROLE = percentile_role

    def data(self: Any, index: Any, role: int = theme_predictions.Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        column = index.column()
        score = float(row.get("score", 0.0))
        deviation = float(row.get("deviation", 0.0))
        percentile = row.get("percentile")

        if role == theme_predictions.Qt.DisplayRole:
            if column == 0:
                return str(row.get("label", row.get("key", "")))
            if column == 1:
                return f"{score:.1f}%"
            if column == 2:
                return format_theme_percentile(percentile)
        if role == theme_predictions.Qt.TextAlignmentRole:
            return (
                theme_predictions.Qt.AlignLeft | theme_predictions.Qt.AlignVCenter
                if column == 0
                else theme_predictions.Qt.AlignRight | theme_predictions.Qt.AlignVCenter
            )
        if role == theme_predictions.Qt.ForegroundRole and theme_predictions.QColor is not None:
            if column == 0:
                return theme_predictions.QColor(str(row.get("color", "#e6e6e6")))
            if column == 1:
                return theme_predictions.QColor(theme_predictions.CHART_DATA_HIGHLIGHT_COLOR)
            red, green, blue = theme_predictions.appwide_red_green_rgb_for_range(
                deviation, -100.0, 100.0
            )
            return theme_predictions.QColor(red, green, blue)
        if role == theme_predictions.Qt.FontRole and column == 0:
            if row.get("kind") == "family" and theme_predictions.QFont is not None:
                font = theme_predictions.QFont()
                font.setBold(True)
                return font
        if role == theme_predictions.Qt.ToolTipRole:
            if column == 0:
                kind = "Macrotheme" if row.get("kind") == "family" else "Subtheme"
                return f"{kind}: {row.get('label', row.get('key', ''))}"
            if column == 1:
                return (
                    "Share of this chart's total semantic Theme activation. "
                    f"Matching DB average: {float(row.get('db_average', 0.0)):.1f}%"
                )
            if column == 2:
                return "Empirical percentile among DB charts with the same data-availability profile."
        if role == theme_predictions.THEME_ROW_KEY_ROLE:
            return str(row.get("family_key", row.get("key", "")))
        if role == scope_role:
            return {
                "family_key": str(row.get("family_key", row.get("key", ""))),
                "theme_key": row.get("theme_key"),
                "kind": str(row.get("kind", "family")),
            }
        if role == percentile_role:
            try:
                return float(percentile) if percentile is not None else None
            except (TypeError, ValueError):
                return None
        if role == theme_predictions.THEME_ROW_DEVIATION_ROLE:
            return deviation
        if role == theme_predictions.THEME_ROW_DIRECTION_ROLE:
            return str(row.get("direction", "neutral"))
        return None

    model_class.data = data
    original_less_than = proxy_class.lessThan

    def lessThan(self: Any, left: Any, right: Any) -> bool:  # noqa: N802
        source = self.sourceModel()
        if source is not None and left.column() == 2 and right.column() == 2:
            left_percentile = source.data(
                source.index(left.row(), 0), percentile_role
            )
            right_percentile = source.data(
                source.index(right.row(), 0), percentile_role
            )
            if left_percentile is not None and right_percentile is not None:
                return float(left_percentile) < float(right_percentile)
        return original_less_than(self, left, right)

    proxy_class.lessThan = lessThan

    original_refresh = theme_predictions._refresh_theme_prediction_filter

    def refresh_theme_prediction_filter(owner: Any) -> None:
        original_refresh(owner)
        if getattr(owner, "_themes_prediction_unavailability_reason", ""):
            return
        combo = getattr(owner, "themes_prediction_mode_combo", None)
        mode = combo.currentData() if isinstance(combo, theme_predictions.QComboBox) else "above"
        direction = "below" if mode == "below" else "above"
        fallback = getattr(owner, "_theme_prediction_fallback_directions", set())
        table = getattr(owner, "themes_prediction_table", None)
        visible_rows = table.model().rowCount() if isinstance(table, theme_predictions.QTableView) and table.model() is not None else 0
        if direction in fallback and visible_rows:
            theme_predictions._set_theme_status(
                owner,
                f"No themes are at least {prominence.THEME_DEVIATION_ASSIGNMENT_THRESHOLD:.0f}% {direction} the selected DB norm; showing the five closest differences.",
            )

    theme_predictions._refresh_theme_prediction_filter = refresh_theme_prediction_filter
    theme_predictions._ephemeraldaddy_theme_share_table_installed = True


def _apply_chart_share_rows(
    theme_predictions: Any,
    owner: Any,
    snapshot: Mapping[str, Any] | None,
    context: Mapping[str, Any] | None,
) -> None:
    model = getattr(owner, "_themes_prediction_rows_model", None)
    if not hasattr(model, "set_rows") or context is None:
        return

    availability_key = theme_availability_key_from_context(context)
    norms = theme_chart_share_norms_for_availability(snapshot, availability_key)
    if not norms:
        reason = theme_chart_share_unavailability_reason(snapshot, availability_key)
        owner._themes_prediction_unavailability_reason = reason
        owner._theme_prediction_fallback_directions = set()
        model.set_rows([])
        theme_predictions._set_theme_status(
            owner,
            f"{reason} Recalculate DB Norms to add current Theme percentiles.",
        )
        theme_predictions._refresh_theme_prediction_filter(owner)
        return

    subtheme_scores = getattr(owner, "_theme_prediction_subtheme_scores", {})
    if not isinstance(subtheme_scores, Mapping):
        return
    rows, subtheme_shares, family_shares, fallback_directions = _chart_share_rows(
        subtheme_scores, norms
    )
    owner._themes_prediction_unavailability_reason = ""
    owner._theme_prediction_subtheme_chart_shares = subtheme_shares
    owner._theme_prediction_family_chart_shares = family_shares
    owner._theme_prediction_share_norms = dict(norms)
    owner._theme_prediction_availability_key = availability_key
    owner._theme_prediction_fallback_directions = fallback_directions
    model.set_rows(rows)
    theme_predictions._refresh_theme_prediction_filter(owner)


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
            owner._theme_prediction_subtheme_chart_shares = {}
            owner._theme_prediction_family_chart_shares = {}
            owner._theme_prediction_share_norms = {}
            original_render(owner, chart)
            return

        context: Mapping[str, Any] | None = None
        context_error: Exception | None = None
        try:
            context = prominence._activation_context(chart)
        except Exception as exc:
            context_error = exc

        owner._theme_prediction_activation_context = context
        owner._theme_prediction_evidence_by_family = {}

        context_token = _ACTIVE_THEME_CONTEXT.set(context)
        error_token = _ACTIVE_THEME_CONTEXT_ERROR.set(context_error)
        try:
            original_render(owner, chart)
            if context_error is None and context is not None:
                snapshot = theme_predictions.load_prediction_norms_snapshot()
                _apply_chart_share_rows(theme_predictions, owner, snapshot, context)
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
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> dict[str, Any]:
        captured: dict[str, Any] = {}
        original_calculator = snapshots.calculate_database_theme_family_averages
        original_save = snapshots._core.save_prediction_norms_snapshot

        def calculate_database_theme_family_averages(charts: list[Any]) -> dict[str, float]:
            extended = calculate_database_theme_norms(charts)
            captured["extended_norms"] = extended
            return dict(extended.get("legacy_family_averages", {}))

        def save_prediction_norms_snapshot(payload: dict[str, Any], path: Any) -> Any:
            extended = captured.get("extended_norms", {})
            enriched = enrich_theme_snapshot_with_availability_baselines(
                payload,
                extended.get("legacy_family_averages_by_availability", {}),
                extended.get("chart_counts", {}),
                extended_norms=extended,
            )
            return original_save(enriched, path)

        snapshots.calculate_database_theme_family_averages = calculate_database_theme_family_averages
        snapshots._core.save_prediction_norms_snapshot = save_prediction_norms_snapshot
        try:
            return original_refresh(
                owner,
                user_initiated=user_initiated,
                progress_callback=progress_callback,
            )
        finally:
            snapshots.calculate_database_theme_family_averages = original_calculator
            snapshots._core.save_prediction_norms_snapshot = original_save

    snapshots.refresh_prediction_norms_snapshot = refresh_prediction_norms_snapshot
    snapshots._core.refresh_prediction_norms_snapshot = refresh_prediction_norms_snapshot
    snapshots._ephemeraldaddy_theme_availability_norms_installed = True

    app_module = _loaded_app_module()
    if app_module is not None:
        setattr(app_module, "refresh_prediction_norms_snapshot", refresh_prediction_norms_snapshot)
    db_info_module = sys.modules.get("ephemeraldaddy.gui.features.controllers.db_info")
    if db_info_module is not None:
        setattr(db_info_module, "refresh_prediction_norms_snapshot", refresh_prediction_norms_snapshot)


def install_theme_prediction_runtime(theme_predictions: Any) -> None:
    """Install Theme share rendering and denominator-compatible DB comparisons."""
    if getattr(theme_predictions, "_ephemeraldaddy_theme_runtime_installed", False):
        return
    _patch_bound_app_scheduler()
    _install_theme_table_semantics(theme_predictions)
    _install_availability_matched_render(theme_predictions)
    _install_availability_stratified_snapshot_refresh()
    theme_predictions._ephemeraldaddy_theme_runtime_installed = True
