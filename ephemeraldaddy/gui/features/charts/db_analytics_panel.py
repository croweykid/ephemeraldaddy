from __future__ import annotations

from typing import Any

from ephemeraldaddy.gui.features.charts.sign_distribution import SIGN_DISTRIBUTION_DROPDOWN_OPTIONS
from ephemeraldaddy.gui.features.charts.presentation import get_nakshatra
from ephemeraldaddy.core.constants import NAKSHATRA_RANGES


def decans_dropdown_options() -> list[tuple[str, str]]:
    return list(SIGN_DISTRIBUTION_DROPDOWN_OPTIONS)


def nakshatras_dropdown_options() -> list[tuple[str, str]]:
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


def nakshatras_empty_cache_fields() -> dict[str, Any]:
    nakshatra_labels = [str(name) for name, *_ in NAKSHATRA_RANGES]
    return {
        "position_nakshatra_totals_by_body": {
            body: {label: 0 for label in nakshatra_labels}
            for _label, body in SIGN_DISTRIBUTION_DROPDOWN_OPTIONS
        },
        "position_nakshatra_count_by_body": {
            body: 0.0 for _label, body in SIGN_DISTRIBUTION_DROPDOWN_OPTIONS
        },
    }


def snapshot_add_decan(snapshot: dict[str, Any], body: str, longitude: float) -> None:
    decan_number = min(3, max(1, int((float(longitude) % 30.0) // 10.0) + 1))
    snapshot["position_decan_totals_by_body"][body][decan_number] += 1
    snapshot["position_decan_count_by_body"][body] += 1


def snapshot_add_nakshatra(snapshot: dict[str, Any], body: str, longitude: float) -> None:
    nakshatra_name = str(get_nakshatra(float(longitude))).strip()
    if not nakshatra_name:
        return
    totals_by_body = snapshot.get("position_nakshatra_totals_by_body", {})
    body_totals = totals_by_body.get(body)
    if body_totals is None or nakshatra_name not in body_totals:
        return
    body_totals[nakshatra_name] += 1
    snapshot["position_nakshatra_count_by_body"][body] += 1


def apply_decan_snapshot_delta(totals: dict[str, Any], snapshot: dict[str, Any], direction: int) -> None:
    for body, count in snapshot.get("position_decan_count_by_body", {}).items():
        totals["position_decan_count_by_body"][body] += direction * float(count)
    for body, decan_totals in snapshot.get("position_decan_totals_by_body", {}).items():
        for decan in (1, 2, 3):
            totals["position_decan_totals_by_body"][body][decan] += direction * int(decan_totals.get(decan, 0))


def apply_nakshatra_snapshot_delta(totals: dict[str, Any], snapshot: dict[str, Any], direction: int) -> None:
    for body, count in snapshot.get("position_nakshatra_count_by_body", {}).items():
        totals["position_nakshatra_count_by_body"][body] += direction * float(count)
    for body, nakshatra_totals in snapshot.get("position_nakshatra_totals_by_body", {}).items():
        for nakshatra_name, count in nakshatra_totals.items():
            totals["position_nakshatra_totals_by_body"][body][nakshatra_name] += direction * int(count)


def render_decans_chart(dialog: Any, selection_cache: dict[str, Any], database_cache: dict[str, Any], loaded_charts: int) -> None:
    decans_mode = dialog._decans_mode
    selection_decan_counts = selection_cache["position_decan_totals_by_body"].get(decans_mode, {1: 0, 2: 0, 3: 0})
    database_decan_counts = database_cache["position_decan_totals_by_body"].get(decans_mode, {1: 0, 2: 0, 3: 0})

    selection_counts = [int(selection_decan_counts[i]) for i in (1, 2, 3)]
    database_counts = [int(database_decan_counts[i]) for i in (1, 2, 3)]
    display_counts = selection_counts if loaded_charts > 0 else database_counts

    decans_canvas = dialog._build_count_distribution_chart(
        labels=["Decan 1", "Decan 2", "Decan 3"],
        selection_counts=display_counts,
        database_counts=display_counts,
        loaded_charts=0,
    )
    dialog._clear_layout(dialog.decans_chart_layout)
    dialog.decans_chart_layout.addWidget(decans_canvas, 0)

    dialog._analysis_chart_export_rows["decans"] = dialog._build_analysis_export_rows(
        labels=["Decan 1", "Decan 2", "Decan 3"],
        selection_values=[float(value) for value in display_counts],
        database_values=[float(value) for value in display_counts],
        selection_counts=display_counts,
        database_counts=display_counts,
        loaded_charts=0,
        include_significance=False,
    )


def render_nakshatras_chart(dialog: Any, selection_cache: dict[str, Any], database_cache: dict[str, Any], loaded_charts: int) -> None:
    nakshatras_mode = dialog._nakshatras_mode
    labels = [str(name) for name, *_ in NAKSHATRA_RANGES]
    selection_totals = selection_cache["position_nakshatra_totals_by_body"].get(nakshatras_mode, {})
    database_totals = database_cache["position_nakshatra_totals_by_body"].get(nakshatras_mode, {})
    selection_counts = [int(selection_totals.get(label, 0)) for label in labels]
    database_counts = [int(database_totals.get(label, 0)) for label in labels]
    display_counts = selection_counts if loaded_charts > 0 else database_counts

    nak_canvas = dialog._build_count_distribution_chart(
        labels=labels,
        selection_counts=display_counts,
        database_counts=display_counts,
        loaded_charts=0,
        auto_height=True,
    )
    dialog._clear_layout(dialog.nakshatras_chart_layout)
    dialog.nakshatras_chart_layout.addWidget(nak_canvas, 0)

    dialog._analysis_chart_export_rows["nakshatras"] = dialog._build_analysis_export_rows(
        labels=labels,
        selection_values=[float(value) for value in display_counts],
        database_values=[float(value) for value in display_counts],
        selection_counts=display_counts,
        database_counts=display_counts,
        loaded_charts=0,
        include_significance=False,
    )
