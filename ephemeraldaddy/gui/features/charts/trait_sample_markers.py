"""Display source-sample markers without changing Trait or chart identity."""

from __future__ import annotations

import html
from collections.abc import Mapping
from types import ModuleType
from typing import Any

from ephemeraldaddy.gui.features.similarities.cohort_metadata import (
    chart_uid_is_anti_ascribed,
    chart_uid_is_ascribed,
    normalize_chart_uid,
)
from ephemeraldaddy.gui.features.charts.trait_prediction_policy import (
    ascribed_trait_names_for_chart,
    predictions_exclude_ascribed_enabled,
)

SOURCE_SAMPLE_TRAIT_PREFIX = "🧚 "
ANTI_SAMPLE_TRAIT_PREFIX = "👹 "
_MARKER_NAMES_ATTR = "_trait_source_sample_marker_names"
_ANTI_MARKER_NAMES_ATTR = "_trait_anti_sample_marker_names"
_MISSING = object()


def _marker_names(core: ModuleType, attr_name: str = _MARKER_NAMES_ATTR) -> set[str]:
    raw = getattr(core, attr_name, ())
    return {str(name) for name in raw if str(name)}


def _marked_name(
    name: object,
    marker_names: set[str],
    anti_marker_names: set[str] | None = None,
) -> str:
    text = str(name or "")
    positive = text in marker_names
    anti = text in (anti_marker_names or set())
    if not positive and not anti:
        return text
    prefix = ("🧚" if positive else "") + ("👹" if anti else "")
    return f"{prefix} {text}"


def _trait_profile(trait: Mapping[str, Any]) -> Mapping[str, Any]:
    profile = trait.get("profile")
    return profile if isinstance(profile, Mapping) else trait


def _marked_chart_name_for_profile(
    name: object,
    profile: Mapping[str, Any],
    chart_uid: object,
) -> str:
    """Decorate one chart display name from Trait sample provenance."""
    text = str(name or "")
    positive = chart_uid_is_ascribed(profile, chart_uid)
    anti = chart_uid_is_anti_ascribed(profile, chart_uid)
    if not positive and not anti:
        return text
    prefix = ("🧚" if positive else "") + ("👹" if anti else "")
    return f"{prefix} {text}"


def _rankings_rows_with_sample_markers(
    selected_trait_name: str | None,
    rankings: list[dict[str, Any]],
    traits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return display copies of Ranking rows with UID-driven sample markers."""
    wanted = str(selected_trait_name or "").strip().casefold()
    if not wanted or not rankings:
        return rankings
    selected_trait = next(
        (
            trait
            for trait in traits
            if str(trait.get("name", "") or "").strip().casefold() == wanted
        ),
        None,
    )
    if not isinstance(selected_trait, Mapping):
        return rankings
    profile = _trait_profile(selected_trait)
    marked_rows: list[dict[str, Any]] = []
    for row in rankings:
        marked_row = dict(row)
        marked_row["name"] = _marked_chart_name_for_profile(
            row.get("name", ""),
            profile,
            row.get("chart_uid", ""),
        )
        marked_rows.append(marked_row)
    return marked_rows


def _anti_ascribed_trait_names_for_chart(
    chart: Any,
    traits: list[dict[str, Any]],
) -> set[str]:
    chart_uid = normalize_chart_uid(getattr(chart, "chart_uid", ""))
    if not chart_uid:
        return set()
    return {
        name
        for trait in traits
        if (name := str(trait.get("name", "") or "").strip())
        and chart_uid_is_anti_ascribed(_trait_profile(trait), chart_uid)
    }


def install_trait_sample_markers(core: ModuleType) -> None:
    """Install display-only 🧚/👹 provenance markers on Trait-related UI.

    The underlying Trait names, chart names, href targets, scores, persisted
    metadata, ranking order, and cache identities remain unchanged. Markers are
    applied only to presentation copies immediately before rendering.
    """
    if bool(getattr(core, "_ephemeraldaddy_trait_sample_markers_installed", False)):
        return

    original_apply = core._apply_traits_prediction_metadata
    original_rows_from_metadata = core._trait_prediction_rows_from_metadata
    original_rank_row = core._trait_rank_row

    def rows_from_metadata_with_sample_markers(
        traits: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        rows = original_rows_from_metadata(traits, metadata)
        marker_names = _marker_names(core)
        anti_marker_names = _marker_names(core, _ANTI_MARKER_NAMES_ATTR)
        if not marker_names and not anti_marker_names:
            return rows
        marked_rows: list[dict[str, Any]] = []
        for row in rows:
            marked = dict(row)
            marked["display_name"] = _marked_name(
                marked.get("name", ""),
                marker_names,
                anti_marker_names,
            )
            marked_rows.append(marked)
        return marked_rows

    def rank_row_with_sample_marker(
        name: str,
        percentage: float,
        *,
        color: str,
        db_average: float,
        db_deviation: float,
    ) -> str:
        rendered = original_rank_row(
            name,
            percentage,
            color=color,
            db_average=db_average,
            db_deviation=db_deviation,
        )
        marked = _marked_name(
            name,
            _marker_names(core),
            _marker_names(core, _ANTI_MARKER_NAMES_ATTR),
        )
        if marked == name:
            return rendered
        escaped_name = html.escape(name)
        marked_name = html.escape(marked)
        return rendered.replace(f">{escaped_name}</a>", f">{marked_name}</a>", 1)

    def apply_metadata_with_sample_markers(
        owner: Any,
        traits: list[dict[str, Any]],
        metadata: dict[str, Any],
        *,
        prefix_html: str = "",
    ) -> None:
        chart = getattr(owner, "_traits_prediction_chart", None)
        marker_names = (
            set()
            if predictions_exclude_ascribed_enabled(owner)
            else ascribed_trait_names_for_chart(chart, traits)
        )
        anti_marker_names = _anti_ascribed_trait_names_for_chart(chart, traits)
        previous = getattr(core, _MARKER_NAMES_ATTR, _MISSING)
        previous_anti = getattr(core, _ANTI_MARKER_NAMES_ATTR, _MISSING)
        setattr(core, _MARKER_NAMES_ATTR, marker_names)
        setattr(core, _ANTI_MARKER_NAMES_ATTR, anti_marker_names)
        try:
            original_apply(owner, traits, metadata, prefix_html=prefix_html)
        finally:
            if previous is _MISSING:
                try:
                    delattr(core, _MARKER_NAMES_ATTR)
                except AttributeError:
                    pass
            else:
                setattr(core, _MARKER_NAMES_ATTR, previous)
            if previous_anti is _MISSING:
                try:
                    delattr(core, _ANTI_MARKER_NAMES_ATTR)
                except AttributeError:
                    pass
            else:
                setattr(core, _ANTI_MARKER_NAMES_ATTR, previous_anti)

    # Database View Rankings already keeps chart UID separate from display name.
    # Wrap only the final Traits renderer so scoring, sorting, caches, and chart
    # links continue to operate on the original raw rows.
    from ephemeraldaddy.gui.ranking_panel import RankingsPanelMixin

    original_render_rankings_traits_html = RankingsPanelMixin._render_rankings_traits_html

    def render_rankings_traits_html_with_sample_markers(
        owner: Any,
        selected_trait_name: str | None,
        rankings: list[dict[str, Any]],
        *,
        cache_warmed: bool,
        parsed_percent: float | None,
    ) -> str:
        from ephemeraldaddy.gui.features.settings.traits import list_traits

        display_rankings = _rankings_rows_with_sample_markers(
            selected_trait_name,
            rankings,
            list_traits(active_only=True),
        )
        return original_render_rankings_traits_html(
            owner,
            selected_trait_name,
            display_rankings,
            cache_warmed=cache_warmed,
            parsed_percent=parsed_percent,
        )

    RankingsPanelMixin._render_rankings_traits_html = (
        render_rankings_traits_html_with_sample_markers
    )
    core._trait_prediction_rows_from_metadata = rows_from_metadata_with_sample_markers
    core._trait_rank_row = rank_row_with_sample_marker
    core._apply_traits_prediction_metadata = apply_metadata_with_sample_markers
    core._ephemeraldaddy_trait_sample_markers_installed = True
