"""Display source-sample markers on Trait prediction rows without changing Trait identity."""

from __future__ import annotations

import html
from types import ModuleType
from typing import Any

from ephemeraldaddy.gui.features.charts.trait_prediction_policy import (
    ascribed_trait_names_for_chart,
    predictions_exclude_ascribed_enabled,
)

SOURCE_SAMPLE_TRAIT_PREFIX = "🧚 "
_MARKER_NAMES_ATTR = "_trait_source_sample_marker_names"
_MISSING = object()


def _marker_names(core: ModuleType) -> set[str]:
    raw = getattr(core, _MARKER_NAMES_ATTR, ())
    return {str(name) for name in raw if str(name)}


def _marked_name(name: object, marker_names: set[str]) -> str:
    text = str(name or "")
    if text in marker_names and not text.startswith(SOURCE_SAMPLE_TRAIT_PREFIX):
        return f"{SOURCE_SAMPLE_TRAIT_PREFIX}{text}"
    return text


def install_trait_sample_markers(core: ModuleType) -> None:
    """Install display-only 🧚 markers for Traits whose source sample contains the chart.

    The underlying Trait names, href targets, scores, persisted metadata, and cache
    identities remain unchanged.  The marker is applied only while prediction UI
    output is being rendered.  When the user's exclusion checkbox is enabled, the
    existing exclusion policy runs normally and no marker is emitted.
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
        if not marker_names:
            return rows
        marked_rows: list[dict[str, Any]] = []
        for row in rows:
            marked = dict(row)
            marked["display_name"] = _marked_name(
                marked.get("name", ""), marker_names
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
        if name not in _marker_names(core):
            return rendered
        escaped_name = html.escape(name)
        marked_name = html.escape(f"{SOURCE_SAMPLE_TRAIT_PREFIX}{name}")
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
        previous = getattr(core, _MARKER_NAMES_ATTR, _MISSING)
        setattr(core, _MARKER_NAMES_ATTR, marker_names)
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

    core._trait_prediction_rows_from_metadata = rows_from_metadata_with_sample_markers
    core._trait_rank_row = rank_row_with_sample_marker
    core._apply_traits_prediction_metadata = apply_metadata_with_sample_markers
    core._ephemeraldaddy_trait_sample_markers_installed = True
