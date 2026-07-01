"""Chart View custom trait prediction rendering helpers."""

from __future__ import annotations

import html
from typing import Any

from PySide6.QtWidgets import QLabel

from ephemeraldaddy.analysis.traits import DEFAULT_TRAIT_COLOR, calculate_trait_likelihoods, list_traits, normalize_trait_color

TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD = 5.0


def _format_signed_percentage(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.1f}%"


def _traits_table_header() -> str:
    return (
        "<tr>"
        "<th style='padding:1px 8px 2px 0; text-align:left; color:#f5f5f5;'>trait</th>"
        "<th style='padding:1px 8px 2px 0; text-align:right; color:#f5f5f5;'>%</th>"
        "<th style='padding:1px 0 2px 0; text-align:right; color:#f5f5f5;'>vs DB avg</th>"
        "</tr>"
    )


def _trait_rank_row(
    name: str,
    percentage: float,
    *,
    color: str,
    db_average: float,
    db_deviation: float,
) -> str:
    safe_name = html.escape(name)
    pct = max(0.0, min(100.0, percentage))
    safe_color = html.escape(normalize_trait_color(color))
    difference_text = html.escape(_format_signed_percentage(db_deviation))
    difference_color = "#d8d8d8"
    if db_deviation > 0:
        difference_color = "#90ee90"
    elif db_deviation < 0:
        difference_color = "#ffb3b3"
    safe_title = html.escape(f"DB average: {max(0.0, min(100.0, db_average)):.1f}%")
    return (
        "<tr>"
        f"<td style='padding:1px 8px 1px 0; white-space:nowrap; color:{safe_color};' title='{safe_title}'>{safe_name}</td>"
        f"<td style='padding:1px 8px 1px 0; text-align:right; color:#d8d8d8;'>{pct:.1f}%</td>"
        f"<td style='padding:1px 0; text-align:right; color:{difference_color};'>{difference_text}</td>"
        "</tr>"
    )


def _trait_column(title: str, rows: list[tuple[str, float, float, float]], color_by_name: dict[str, str]) -> str:
    if rows:
        body = "".join(
            _trait_rank_row(
                name,
                pct,
                color=color_by_name.get(name, DEFAULT_TRAIT_COLOR),
                db_average=db_average,
                db_deviation=db_deviation,
            )
            for name, pct, db_average, db_deviation in rows
        )
    else:
        body = (
            "<tr><td colspan='3' style='padding:3px 0; color:#9a9a9a;'>"
            "No traits meet the 5% deviation threshold."
            "</td></tr>"
        )
    return (
        "<td style='vertical-align:top; width:50%; padding-right:12px;'>"
        f"<div style='padding-bottom:3px;'><b>{html.escape(title)}</b></div>"
        "<table cellspacing='0' cellpadding='0' style='width:100%;'>"
        f"{_traits_table_header()}{body}"
        "</table>"
        "</td>"
    )


def _database_trait_averages(owner: Any, traits: list[dict[str, Any]]) -> dict[str, float]:
    chart_rows = getattr(owner, "_chart_rows", [])
    normalize_row = getattr(owner, "_normalize_chart_row", None)
    chart_ids: set[int] = set()
    for row in chart_rows:
        if callable(normalize_row) and normalize_row(row) is None:
            continue
        try:
            chart_ids.add(int(row[0]))
        except (TypeError, ValueError, IndexError):
            continue
    collect = getattr(owner, "_collect_traits_distribution_analytics", None)
    signature_builder = getattr(owner, "_traits_distribution_signature", None)
    if not chart_ids or not callable(collect) or not callable(signature_builder):
        return {}
    analytics = collect(
        chart_ids,
        trait_items=traits,
        trait_signature=signature_builder(traits),
    )
    chart_count = max(0, int(analytics.get("chart_count", 0)))
    if not chart_count:
        return {}
    totals = analytics.get("totals", {})
    return {
        str(name): (float(totals.get(name, 0.0)) / float(chart_count)) * 100.0
        for name in analytics.get("trait_names", [])
    }


def render_traits_predictions(owner: Any, chart: Any | None) -> None:
    """Render uploaded custom trait scores into Chart View's Predictions panel."""
    label = getattr(owner, "traits_prediction_label", None)
    if not isinstance(label, QLabel):
        return
    traits = list_traits(active_only=True)
    if not traits:
        if list_traits():
            label.setText("No active traits. Reactivate traits in Settings > Traits to include them in Predictions.")
        else:
            label.setText("No traits uploaded. Add traits in Settings > Traits.")
        return
    if chart is None or owner._is_placeholder_chart(chart):
        label.setText("Trait predictions unavailable for this chart.")
        return
    try:
        # calculate_trait_likelihoods wraps calculate_trait_scores and converts
        # the signed raw totals to user-facing percentages.
        likelihoods = calculate_trait_likelihoods(chart, traits)
    except Exception as exc:
        label.setText(f"Trait predictions unavailable: {html.escape(str(exc))}")
        return
    color_by_name = {
        str(trait.get("name", "")): normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR)))
        for trait in traits
    }
    database_averages = _database_trait_averages(owner, traits)
    db_deviations = {
        name: float(pct) - float(database_averages[name])
        for name, pct in likelihoods.items()
        if name in database_averages
    }
    if not likelihoods:
        label.setText("No scorable traits uploaded.")
        return
    if not database_averages:
        label.setText("Trait predictions unavailable until database trait averages can be calculated.")
        return
    threshold = TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD
    above_avg_traits = sorted(
        (
            (name, float(likelihoods[name]), float(database_averages[name]), float(db_deviation))
            for name, db_deviation in db_deviations.items()
            if db_deviation >= threshold
        ),
        key=lambda item: item[3],
        reverse=True,
    )
    below_avg_traits = sorted(
        (
            (name, float(likelihoods[name]), float(database_averages[name]), float(db_deviation))
            for name, db_deviation in db_deviations.items()
            if db_deviation <= -threshold
        ),
        key=lambda item: item[3],
    )
    parts = [
        "<div style='color:#d8d8d8; padding-bottom:4px;'>"
        "Traits are assigned by deviation from the active database average. "
        f"Above-average traits are at least {threshold:.0f}% higher than DB average; "
        f"below-average traits are at least {threshold:.0f}% lower than DB average."
        "</div>",
        "<table cellspacing='0' cellpadding='0' style='width:100%;'><tr>",
        _trait_column("Above avg traits", above_avg_traits, color_by_name),
        _trait_column("Below avg traits", below_avg_traits, color_by_name),
        "</tr></table>",
        "<div style='color:#9a9a9a; padding-top:4px;'>"
        "Hover a trait name to see the DB average used for the comparison."
        "</div>",
    ]
    label.setText("".join(parts))
