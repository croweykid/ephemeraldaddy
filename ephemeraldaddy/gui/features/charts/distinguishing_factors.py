"""Most-distinguishing chart factor summaries for Chart View predictions."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import html
import math
import statistics
from typing import Callable, Iterable

from ephemeraldaddy.analysis.human_design import build_human_design_result
from ephemeraldaddy.core.chart import Chart, chart_uses_houses
from ephemeraldaddy.core.interpretations import NAKSHATRA_RANGES, ZODIAC_NAMES
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_element_weights,
    calculate_dominant_house_weights,
    calculate_dominant_nakshatra_weights,
    calculate_dominant_planet_weights,
    calculate_dominant_sign_weights,
    calculate_mode_weights,
    dominant_planet_keys,
)
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR

DISTINGUISHING_Z_THRESHOLD = 2.0
ELEMENT_SHARE_THRESHOLD = 0.50
MODE_SHARE_THRESHOLD = 0.65
MIN_NORM_SAMPLE_SIZE = 5


@dataclass(frozen=True)
class _MetricGroup:
    key: str
    label: str
    values_for_chart: Callable[[Chart], dict[object, float]]
    labels: tuple[object, ...]


@dataclass(frozen=True)
class DistinguishingFactor:
    group_label: str
    factor_label: str
    value_pct: float
    mean_pct: float
    z_score: float

    @property
    def extremity(self) -> float:
        return abs(self.z_score)


def _normalized_shares(values: dict[object, float], labels: Iterable[object]) -> dict[object, float]:
    raw = {label: max(0.0, float(values.get(label, 0.0) or 0.0)) for label in labels}
    total = sum(raw.values())
    if total <= 0:
        return {label: 0.0 for label in labels}
    return {label: value / total for label, value in raw.items()}


def _planet_group() -> _MetricGroup:
    labels = tuple(dominant_planet_keys(None))
    return _MetricGroup("planets", "planet/body weight", calculate_dominant_planet_weights, labels)


def _house_values(chart: Chart) -> dict[object, float]:
    if not chart_uses_houses(chart):
        return {house: 0.0 for house in range(1, 13)}
    return dict(calculate_dominant_house_weights(chart))


def _metric_groups(chart: Chart) -> tuple[_MetricGroup, ...]:
    groups: list[_MetricGroup] = [
        _planet_group(),
        _MetricGroup("signs", "sign weight", calculate_dominant_sign_weights, tuple(ZODIAC_NAMES)),
        _MetricGroup("elements", "element weight", calculate_dominant_element_weights, ("Fire", "Earth", "Air", "Water")),
        _MetricGroup("modes", "mode weight", calculate_mode_weights, ("cardinal", "mutable", "fixed")),
        _MetricGroup(
            "nakshatras",
            "nakshatra weight",
            calculate_dominant_nakshatra_weights,
            tuple(str(name) for name, *_rest in NAKSHATRA_RANGES),
        ),
    ]
    if chart_uses_houses(chart):
        groups.insert(3, _MetricGroup("houses", "house weight", _house_values, tuple(range(1, 13))))
    return tuple(groups)


def _label_text(label: object, group_key: str) -> str:
    if group_key == "houses":
        return f"House {int(label)}"
    if group_key == "modes":
        return str(label).title()
    return str(label)


def _safe_chart_values(group: _MetricGroup, chart: Chart) -> dict[object, float] | None:
    try:
        values = group.values_for_chart(chart)
    except Exception:
        return None
    if not isinstance(values, dict):
        return None
    return values


def find_distinguishing_factors(chart: Chart, norm_charts: Iterable[Chart]) -> tuple[list[DistinguishingFactor], int]:
    """Return factors whose normalized share is at least two standard deviations from DB norms."""
    usable_norm_charts = [norm_chart for norm_chart in norm_charts if norm_chart is not None]
    factors: list[DistinguishingFactor] = []
    if len(usable_norm_charts) < MIN_NORM_SAMPLE_SIZE:
        return factors, len(usable_norm_charts)

    for group in _metric_groups(chart):
        chart_values = _safe_chart_values(group, chart)
        if chart_values is None:
            continue
        chart_shares = _normalized_shares(chart_values, group.labels)
        norm_shares_by_label: dict[object, list[float]] = {label: [] for label in group.labels}
        for norm_chart in usable_norm_charts:
            if group.key == "houses" and not chart_uses_houses(norm_chart):
                continue
            norm_values = _safe_chart_values(group, norm_chart)
            if norm_values is None:
                continue
            shares = _normalized_shares(norm_values, group.labels)
            for label in group.labels:
                norm_shares_by_label[label].append(float(shares.get(label, 0.0)))
        for label in group.labels:
            baseline = norm_shares_by_label.get(label, [])
            if len(baseline) < MIN_NORM_SAMPLE_SIZE:
                continue
            stdev = statistics.pstdev(baseline)
            if stdev <= 1e-9 or not math.isfinite(stdev):
                continue
            mean = statistics.fmean(baseline)
            value = float(chart_shares.get(label, 0.0))
            z_score = (value - mean) / stdev
            if abs(z_score) >= DISTINGUISHING_Z_THRESHOLD:
                factors.append(
                    DistinguishingFactor(
                        group_label=group.label,
                        factor_label=_label_text(label, group.key),
                        value_pct=value * 100.0,
                        mean_pct=mean * 100.0,
                        z_score=z_score,
                    )
                )
    factors.sort(key=lambda factor: factor.extremity, reverse=True)
    return factors, len(usable_norm_charts)


def _duplicate_human_design_gate_lines(chart: Chart) -> list[tuple[int, list[int]]]:
    try:
        hd_result = build_human_design_result(chart)
    except Exception:
        return []
    activations = (*hd_result.personality_activations, *hd_result.design_activations)
    gate_lines: dict[int, list[int]] = {}
    for activation in activations:
        try:
            gate = int(activation.gate)
            line = int(activation.line)
        except Exception:
            continue
        gate_lines.setdefault(gate, []).append(line)
    duplicates = [
        (gate, sorted(lines))
        for gate, lines in gate_lines.items()
        if len(lines) >= 2
    ]
    duplicates.sort(key=lambda item: (-len(item[1]), item[0]))
    return duplicates


def _concentration_lines(chart: Chart) -> list[str]:
    lines: list[str] = []
    element_shares = _normalized_shares(calculate_dominant_element_weights(chart), ("Fire", "Earth", "Air", "Water"))
    for element, share in sorted(element_shares.items(), key=lambda item: item[1], reverse=True):
        if share > ELEMENT_SHARE_THRESHOLD:
            lines.append(f"{html.escape(str(element))} makes up {share * 100.0:.1f}% of weighted elements.")
    mode_shares = _normalized_shares(calculate_mode_weights(chart), ("cardinal", "mutable", "fixed"))
    for mode, share in sorted(mode_shares.items(), key=lambda item: item[1], reverse=True):
        if share >= MODE_SHARE_THRESHOLD:
            lines.append(f"{html.escape(str(mode).title())} makes up {share * 100.0:.1f}% of weighted modes.")
    return lines


def build_distinguishing_factors_html(chart: Chart | None, norm_charts: Iterable[Chart]) -> str:
    """Build rich text for the Predictions tab's distinguishing-factors section."""
    if chart is None:
        return "<span style='color:#f5f5f5;'>No chart loaded.</span>"

    norm_chart_list = list(norm_charts)
    factors, norm_count = find_distinguishing_factors(chart, norm_chart_list)
    lines: list[str] = []
    if norm_count < MIN_NORM_SAMPLE_SIZE:
        lines.append(
            f"Need at least {MIN_NORM_SAMPLE_SIZE} database charts to calculate norms; found {norm_count}."
        )
    elif factors:
        lines.append(
            f"Compared with {norm_count} database charts, these factors are at least "
            f"{DISTINGUISHING_Z_THRESHOLD:.0f}σ from the current norm:"
        )
        for factor in factors[:12]:
            direction = "above" if factor.z_score > 0 else "below"
            lines.append(
                "• "
                f"{html.escape(factor.factor_label)} {html.escape(factor.group_label)}: "
                f"{factor.value_pct:.1f}% vs DB mean {factor.mean_pct:.1f}% "
                f"({abs(factor.z_score):.1f}σ {direction})."
            )
    else:
        lines.append(
            f"Compared with {norm_count} database charts, no weighted factors currently exceed "
            f"the {DISTINGUISHING_Z_THRESHOLD:.0f}σ distinction threshold."
        )

    concentration_lines = _concentration_lines(chart)
    if concentration_lines:
        lines.append("")
        lines.append("Concentration flags:")
        lines.extend(f"• {line}" for line in concentration_lines)

    duplicate_gates = _duplicate_human_design_gate_lines(chart)
    if duplicate_gates:
        lines.append("")
        lines.append("Repeated Human Design gates:")
        for gate, duplicate_lines in duplicate_gates[:10]:
            line_counts = Counter(duplicate_lines)
            line_text = ", ".join(
                f"{gate}.{line}" + (f" ×{count}" if count > 1 else "")
                for line, count in sorted(line_counts.items())
            )
            lines.append(f"• Gate {gate} appears {len(duplicate_lines)} times ({html.escape(line_text)}).")

    escaped_html_lines = []
    for line in lines:
        if line == "":
            escaped_html_lines.append("<br>")
        else:
            escaped_html_lines.append(html.escape(line))
    body = "<br>".join(escaped_html_lines)
    return (
        f"<span style='color:{CHART_DATA_HIGHLIGHT_COLOR}; font-weight:700;'>Database distinction scan</span>"
        f"<br><span style='color:#f5f5f5; font-weight:400;'>{body}</span>"
    )
