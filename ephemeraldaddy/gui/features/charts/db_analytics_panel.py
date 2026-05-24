from __future__ import annotations

from typing import Any

from ephemeraldaddy.data.genpop import (
    INNER_PLANET_SIGN_DISTRIBUTION_AGGREGATED,
    SUN_SIGN_DISTRIBUTION_AGGREGATED,
)
from ephemeraldaddy.core.interpretations import NAKSHATRA_RANGES, ZODIAC_NAMES
from ephemeraldaddy.gui.features.charts.presentation import get_nakshatra
from ephemeraldaddy.gui.features.charts.sign_distribution import SIGN_DISTRIBUTION_DROPDOWN_OPTIONS

def _gen_pop_decan_counts(sample_size: int) -> list[int]:
    if sample_size <= 0:
        return [0, 0, 0]
    base = sample_size // 3
    remainder = sample_size % 3
    return [base + (1 if idx < remainder else 0) for idx in range(3)]


def _gen_pop_nakshatra_counts(sample_size: int, label_count: int) -> list[int]:
    if sample_size <= 0 or label_count <= 0:
        return [0] * max(0, label_count)
    base = sample_size // label_count
    remainder = sample_size % label_count
    return [base + (1 if idx < remainder else 0) for idx in range(label_count)]

def _gen_pop_sign_norms_for_body(body: str) -> dict[str, float]:
    if body == "Sun":
        return {
            sign: float(details.get("percent", 0.0)) / 100.0
            for sign, details in SUN_SIGN_DISTRIBUTION_AGGREGATED.items()
        }
    if body in {"Mercury", "Venus"}:
        aggregated = INNER_PLANET_SIGN_DISTRIBUTION_AGGREGATED.get(body, {})
        return {
            sign: float(details.get("percent", 0.0)) / 100.0
            for sign, details in aggregated.items()
        }
    equal = 1.0 / float(len(ZODIAC_NAMES))
    return {sign: equal for sign in ZODIAC_NAMES}


def _gen_pop_nakshatra_counts_for_body(*, body: str, sample_size: int, labels: list[str]) -> list[int]:
    if sample_size <= 0:
        return [0 for _ in labels]
    sign_norms = _gen_pop_sign_norms_for_body(body)
    # Use a fine-grained grid to map sign-weighted longitude likelihood to nakshatras.
    # This keeps the baseline tied to the same aggregated birth data used by sign prevalence.
    points_per_sign = 600
    total_points = points_per_sign * len(ZODIAC_NAMES)
    nak_probs = {label: 0.0 for label in labels}
    for sign_idx, sign in enumerate(ZODIAC_NAMES):
        sign_weight = float(sign_norms.get(sign, 0.0))
        if sign_weight <= 0:
            continue
        per_point_weight = sign_weight / float(points_per_sign)
        sign_start = float(sign_idx * 30.0)
        step = 30.0 / float(points_per_sign)
        for point in range(points_per_sign):
            longitude = sign_start + ((point + 0.5) * step)
            nak_label = str(get_nakshatra(longitude)).strip()
            if nak_label in nak_probs:
                nak_probs[nak_label] += per_point_weight
    raw_counts = [nak_probs[label] * float(sample_size) for label in labels]
    rounded = [int(value) for value in raw_counts]
    remainder = int(sample_size - sum(rounded))
    if remainder > 0:
        fractional = sorted(
            enumerate(raw_counts),
            key=lambda item: (item[1] - int(item[1])),
            reverse=True,
        )
        for idx, _ in fractional[:remainder]:
            rounded[idx] += 1
    return rounded


def _decan_baseline_counts(*, baseline_mode: str, database_counts: list[int]) -> list[int]:
    if baseline_mode != "gen_pop":
        return list(database_counts)
    return _gen_pop_decan_counts(sum(int(count) for count in database_counts))


def _nakshatra_baseline_counts(*, baseline_mode: str, database_counts: list[int], label_count: int) -> list[int]:
    if baseline_mode != "gen_pop":
        return list(database_counts)
    return _gen_pop_nakshatra_counts(sum(int(count) for count in database_counts), label_count)


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


def render_decans_chart(
    dialog: Any,
    selection_cache: dict[str, Any],
    database_cache: dict[str, Any],
    loaded_charts: int,
    baseline_mode: str = "database",
) -> None:
    decans_mode = dialog._decans_mode
    selection_decan_counts = selection_cache["position_decan_totals_by_body"].get(decans_mode, {1: 0, 2: 0, 3: 0})
    database_decan_counts = database_cache["position_decan_totals_by_body"].get(decans_mode, {1: 0, 2: 0, 3: 0})

    selection_counts = [int(selection_decan_counts[i]) for i in (1, 2, 3)]
    database_counts = [int(database_decan_counts[i]) for i in (1, 2, 3)]
    baseline_counts = _decan_baseline_counts(
        baseline_mode=baseline_mode,
        database_counts=database_counts,
    )
    display_counts = selection_counts if loaded_charts > 0 else baseline_counts

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


def render_nakshatras_chart(
    dialog: Any,
    selection_cache: dict[str, Any],
    database_cache: dict[str, Any],
    loaded_charts: int,
    baseline_mode: str = "database",
) -> None:
    nakshatras_mode = dialog._nakshatras_mode
    labels = [str(name) for name, *_ in NAKSHATRA_RANGES]
    selection_totals = selection_cache["position_nakshatra_totals_by_body"].get(nakshatras_mode, {})
    database_totals = database_cache["position_nakshatra_totals_by_body"].get(nakshatras_mode, {})
    selection_counts = [int(selection_totals.get(label, 0)) for label in labels]
    database_counts = [int(database_totals.get(label, 0)) for label in labels]
    if baseline_mode == "gen_pop":
        baseline_counts = _gen_pop_nakshatra_counts_for_body(
            body=nakshatras_mode,
            sample_size=sum(database_counts),
            labels=labels,
        )
    else:
        baseline_counts = _nakshatra_baseline_counts(
            baseline_mode=baseline_mode,
            database_counts=database_counts,
            label_count=len(labels),
        )
    display_counts = selection_counts if loaded_charts > 0 else baseline_counts

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
