from __future__ import annotations

from typing import Any


from ephemeraldaddy.gui.features.charts.sign_distribution import (
    SIGN_DISTRIBUTION_DROPDOWN_OPTIONS,
)

def decans_dropdown_options() -> list[tuple[str, str]]:
    return list(SIGN_DISTRIBUTION_DROPDOWN_OPTIONS)


def decans_empty_cache_fields() -> dict[str, Any]:
    return {
        "position_decan_totals_by_body": {
            body: {1: 0, 2: 0, 3: 0}
            for _label, body in SIGN_DISTRIBUTION_DROPDOWN_OPTIONS
        },
        "position_decan_count_by_body": {
            body: 0.0 for _label, body in SIGN_DISTRIBUTION_DROPDOWN_OPTIONS
        },
    }


def snapshot_add_decan(snapshot: dict[str, Any], body: str, longitude: float) -> None:
    decan_number = min(3, max(1, int((float(longitude) % 30.0) // 10.0) + 1))
    snapshot["position_decan_totals_by_body"][body][decan_number] += 1
    snapshot["position_decan_count_by_body"][body] += 1


def apply_decan_snapshot_delta(totals: dict[str, Any], snapshot: dict[str, Any], direction: int) -> None:
    for body, count in snapshot.get("position_decan_count_by_body", {}).items():
        totals["position_decan_count_by_body"][body] += direction * float(count)
    for body, decan_totals in snapshot.get("position_decan_totals_by_body", {}).items():
        for decan in (1, 2, 3):
            totals["position_decan_totals_by_body"][body][decan] += direction * int(decan_totals.get(decan, 0))


def render_decans_chart(dialog: Any, selection_cache: dict[str, Any], database_cache: dict[str, Any], loaded_charts: int) -> None:
    decans_mode = dialog._decans_mode
    selection_decan_counts = selection_cache["position_decan_totals_by_body"].get(decans_mode, {1: 0, 2: 0, 3: 0})
    database_decan_counts = database_cache["position_decan_totals_by_body"].get(decans_mode, {1: 0, 2: 0, 3: 0})

    selection_counts = [int(selection_decan_counts[i]) for i in (1, 2, 3)]
    database_counts = [int(database_decan_counts[i]) for i in (1, 2, 3)]
    show_selection_only = loaded_charts > 0
    display_counts = selection_counts if show_selection_only else database_counts

    decans_canvas = dialog._build_count_distribution_chart(
        labels=["Decan 1", "Decan 2", "Decan 3"],
        selection_counts=display_counts,
        database_counts=display_counts,
        loaded_charts=0,
    )
    dialog._clear_layout(dialog.decans_chart_layout)
    dialog.decans_chart_layout.addWidget(decans_canvas, 0)

    export_selection_values = [float(value) for value in display_counts]
    export_database_values = [float(value) for value in display_counts]
    dialog._analysis_chart_export_rows["decans"] = dialog._build_analysis_export_rows(
        labels=["Decan 1", "Decan 2", "Decan 3"],
        selection_values=export_selection_values,
        database_values=export_database_values,
        selection_counts=display_counts,
        database_counts=display_counts,
        loaded_charts=0,
        include_significance=False,
    )
