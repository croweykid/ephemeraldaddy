"""Most-distinguishing chart factor summaries for Chart Analytics."""

from __future__ import annotations

from collections import Counter
import json
from dataclasses import dataclass
import html
import math
import statistics
import urllib.parse
from pathlib import Path
from typing import Any, Callable, Iterable

from ephemeraldaddy.analysis.human_design import build_human_design_result
from ephemeraldaddy.analysis.human_design_reference import GATE_COLORS, HD_LINE_COLORS
from ephemeraldaddy.core.chart import Chart, chart_uses_houses
from ephemeraldaddy.core.interpretations import (
    ELEMENT_COLORS,
    HOUSE_COLORS,
    MODE_COLORS,
    NAKSHATRA_PLANET_COLOR,
    NAKSHATRA_RANGES,
    PLANET_COLORS,
    SIGN_COLORS,
    ZODIAC_NAMES,
)
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

DISTINGUISHING_METRICS_SCHEMA_VERSION = 1
DISTINGUISHING_FORMULA_VERSION = 1


def chart_essential_astro_signature(chart: Chart) -> str:
    """Return the narrow ESSENTIAL_ASTRO signature used to invalidate derived astro caches."""
    dt_value = getattr(chart, "dt", None)
    payload = {
        "dt": dt_value.isoformat() if dt_value is not None else None,
        "lat": round(float(getattr(chart, "lat", 0.0) or 0.0), 8),
        "lon": round(float(getattr(chart, "lon", 0.0) or 0.0), 8),
        "birthtime_unknown": bool(getattr(chart, "birthtime_unknown", False)),
        "retcon_time_used": bool(getattr(chart, "retcon_time_used", False)),
        "retcon_hour": getattr(chart, "retcon_hour", None),
        "retcon_minute": getattr(chart, "retcon_minute", None),
    }
    return json.dumps(payload, default=str, sort_keys=True, separators=(",", ":"))


def distinguishing_metric_payload_for_chart(chart: Chart) -> dict[str, Any]:
    """Build persisted per-chart normalized shares used by distinguishing-factor baselines."""
    groups: dict[str, dict[str, float]] = {}
    for group in _metric_groups(chart):
        values = _safe_chart_values(group, chart)
        if values is None:
            continue
        shares = _normalized_shares(values, group.labels)
        groups[group.key] = {str(label): float(shares.get(label, 0.0)) for label in group.labels}
    return {
        "schema_version": DISTINGUISHING_METRICS_SCHEMA_VERSION,
        "formula_version": DISTINGUISHING_FORMULA_VERSION,
        "essential_astro_signature": chart_essential_astro_signature(chart),
        "uses_houses": bool(chart_uses_houses(chart)),
        "groups": groups,
    }


def load_distinguishing_metric_cache(cache_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": DISTINGUISHING_METRICS_SCHEMA_VERSION, "charts": {}}
    if not isinstance(data, dict) or data.get("schema_version") != DISTINGUISHING_METRICS_SCHEMA_VERSION:
        return {"schema_version": DISTINGUISHING_METRICS_SCHEMA_VERSION, "charts": {}}
    charts = data.get("charts")
    if not isinstance(charts, dict):
        data["charts"] = {}
    return data


def save_distinguishing_metric_cache(cache_path: Path, cache: dict[str, Any]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(cache, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    tmp_path.replace(cache_path)


@dataclass(frozen=True)
class _MetricGroup:
    key: str
    label: str
    values_for_chart: Callable[[Chart], dict[object, float]]
    labels: tuple[object, ...]


@dataclass(frozen=True)
class DistinguishingFactor:
    group_key: str
    group_label: str
    raw_label: object
    factor_label: str
    value_pct: float
    mean_pct: float
    z_score: float

    @property
    def extremity(self) -> float:
        return abs(self.z_score)


@dataclass(frozen=True)
class _NormBaseline:
    mean: float
    stdev: float


_NORM_BASELINE_CACHE: dict[tuple[tuple[object, ...], ...], tuple[int, dict[tuple[str, object], _NormBaseline]]] = {}
_NORM_BASELINE_CACHE_MAX_SIZE = 8


def _normalized_shares(values: dict[object, float], labels: Iterable[object]) -> dict[object, float]:
    raw = {label: max(0.0, float(values.get(label, 0.0) or 0.0)) for label in labels}
    total = sum(raw.values())
    if total <= 0:
        return {label: 0.0 for label in labels}
    return {label: value / total for label, value in raw.items()}


def _normalize_css_color(color: str | None) -> str:
    color_text = str(color or "").strip()
    if (
        color_text
        and not color_text.startswith("#")
        and len(color_text) in {3, 6}
        and all(character in "0123456789abcdefABCDEF" for character in color_text)
    ):
        return f"#{color_text}"
    return color_text


def _color_token(label: object, color: str | None, href: str = "") -> str:
    label_text = str(label)
    color_text = _normalize_css_color(color)
    escaped_label = html.escape(label_text)
    if not color_text:
        token = escaped_label
    else:
        token = (
            f'<span style="color:{html.escape(color_text)}; font-weight:400;">'
            f"{escaped_label}</span>"
        )
    if not href:
        return token
    return (
        f'<a href="{html.escape(href, quote=True)}" '
        'style="text-decoration:none;">'
        f"{token}</a>"
    )


def _factor_info_href(group_key: str, raw_label: object) -> str:
    if group_key == "planets":
        kind = "planet"
    elif group_key == "signs":
        kind = "sign"
    elif group_key == "houses":
        kind = "house"
    elif group_key == "nakshatras":
        kind = "nakshatra"
    else:
        return ""
    return f"distinguishing-factor:{kind}:{urllib.parse.quote(str(raw_label), safe='')}"


def _factor_label_html(group_key: str, raw_label: object, display_label: str) -> str:
    href = _factor_info_href(group_key, raw_label)
    if group_key == "planets":
        return _color_token(display_label, PLANET_COLORS.get(str(raw_label)), href)
    if group_key == "signs":
        return _color_token(display_label, SIGN_COLORS.get(str(raw_label)), href)
    if group_key == "houses":
        return _color_token(display_label, HOUSE_COLORS.get(str(raw_label)), href)
    if group_key == "elements":
        return _color_token(display_label, ELEMENT_COLORS.get(str(raw_label)))
    if group_key == "modes":
        return _color_token(display_label, MODE_COLORS.get(str(raw_label).lower()))
    if group_key == "nakshatras":
        return _color_token(display_label, NAKSHATRA_PLANET_COLOR.get(str(raw_label), (None, None))[1], href)
    return html.escape(display_label)


def _hd_gate_label_html(gate: int) -> str:
    href = f"distinguishing-factor:gate:{int(gate)}"
    return _color_token(f"Gate {gate}", GATE_COLORS.get(int(gate)), href)


def _hd_gate_line_html(gate: int, line: int) -> str:
    href = f"distinguishing-factor:gate-line:{int(gate)}:{int(line)}"
    return _color_token(f"{gate}.{line}", HD_LINE_COLORS.get(int(line), GATE_COLORS.get(int(gate))), href)


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


def _chart_norm_signature(chart: Chart) -> tuple[object, ...]:
    dt_value = getattr(chart, "dt", None)
    dt_token = dt_value.isoformat() if dt_value is not None else None
    positions = tuple(
        sorted(
            (str(body), round(float(value), 8))
            for body, value in (getattr(chart, "positions", None) or {}).items()
            if isinstance(value, (int, float))
        )
    )
    houses = tuple(
        round(float(value), 8)
        for value in (getattr(chart, "houses", None) or [])
        if isinstance(value, (int, float))
    )
    return (
        id(chart),
        dt_token,
        round(float(getattr(chart, "lat", 0.0) or 0.0), 8),
        round(float(getattr(chart, "lon", 0.0) or 0.0), 8),
        bool(getattr(chart, "birthtime_unknown", False)),
        bool(getattr(chart, "retcon_time_used", False)),
        getattr(chart, "retcon_hour", None),
        getattr(chart, "retcon_minute", None),
        positions,
        houses,
    )


def _norm_baselines(chart: Chart, usable_norm_charts: list[Chart]) -> dict[tuple[str, object], _NormBaseline]:
    cache_key = (
        ("target_uses_houses", chart_uses_houses(chart)),
        *(_chart_norm_signature(norm_chart) for norm_chart in usable_norm_charts),
    )
    cached = _NORM_BASELINE_CACHE.get(cache_key)
    if cached is not None and cached[0] == len(usable_norm_charts):
        return cached[1]

    baselines: dict[tuple[str, object], _NormBaseline] = {}
    for group in _metric_groups(chart):
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
        for label, baseline in norm_shares_by_label.items():
            if len(baseline) < MIN_NORM_SAMPLE_SIZE:
                continue
            stdev = statistics.pstdev(baseline)
            if stdev <= 1e-9 or not math.isfinite(stdev):
                continue
            baselines[(group.key, label)] = _NormBaseline(
                mean=statistics.fmean(baseline),
                stdev=stdev,
            )

    if len(_NORM_BASELINE_CACHE) >= _NORM_BASELINE_CACHE_MAX_SIZE:
        _NORM_BASELINE_CACHE.pop(next(iter(_NORM_BASELINE_CACHE)))
    _NORM_BASELINE_CACHE[cache_key] = (len(usable_norm_charts), baselines)
    return baselines


def _norm_baselines_from_metric_payloads(chart: Chart, payloads: Iterable[dict[str, Any]]) -> tuple[int, dict[tuple[str, object], _NormBaseline]]:
    usable_payloads = [payload for payload in payloads if isinstance(payload, dict)]
    baselines: dict[tuple[str, object], _NormBaseline] = {}
    for group in _metric_groups(chart):
        norm_shares_by_label: dict[object, list[float]] = {label: [] for label in group.labels}
        for payload in usable_payloads:
            if group.key == "houses" and not bool(payload.get("uses_houses")):
                continue
            group_values = (payload.get("groups") or {}).get(group.key) or {}
            if not isinstance(group_values, dict):
                continue
            for label in group.labels:
                norm_shares_by_label[label].append(float(group_values.get(str(label), 0.0) or 0.0))
        for label, baseline in norm_shares_by_label.items():
            if len(baseline) < MIN_NORM_SAMPLE_SIZE:
                continue
            stdev = statistics.pstdev(baseline)
            if stdev <= 1e-9 or not math.isfinite(stdev):
                continue
            baselines[(group.key, label)] = _NormBaseline(mean=statistics.fmean(baseline), stdev=stdev)
    return len(usable_payloads), baselines


def find_distinguishing_factors_from_metric_payloads(chart: Chart, metric_payloads: Iterable[dict[str, Any]]) -> tuple[list[DistinguishingFactor], int]:
    factors: list[DistinguishingFactor] = []
    norm_count, baselines = _norm_baselines_from_metric_payloads(chart, metric_payloads)
    if norm_count < MIN_NORM_SAMPLE_SIZE:
        return factors, norm_count
    for group in _metric_groups(chart):
        chart_values = _safe_chart_values(group, chart)
        if chart_values is None:
            continue
        chart_shares = _normalized_shares(chart_values, group.labels)
        for label in group.labels:
            baseline = baselines.get((group.key, label))
            if baseline is None:
                continue
            value = float(chart_shares.get(label, 0.0))
            z_score = (value - baseline.mean) / baseline.stdev
            if abs(z_score) >= DISTINGUISHING_Z_THRESHOLD:
                factors.append(DistinguishingFactor(group.key, group.label, label, _label_text(label, group.key), value * 100.0, baseline.mean * 100.0, z_score))
    factors.sort(key=lambda factor: factor.extremity, reverse=True)
    return factors, norm_count


def find_distinguishing_factors(chart: Chart, norm_charts: Iterable[Chart]) -> tuple[list[DistinguishingFactor], int]:
    """Return factors whose normalized share is at least two standard deviations from DB norms."""
    usable_norm_charts = [norm_chart for norm_chart in norm_charts if norm_chart is not None]
    factors: list[DistinguishingFactor] = []
    if len(usable_norm_charts) < MIN_NORM_SAMPLE_SIZE:
        return factors, len(usable_norm_charts)

    baselines = _norm_baselines(chart, usable_norm_charts)
    for group in _metric_groups(chart):
        chart_values = _safe_chart_values(group, chart)
        if chart_values is None:
            continue
        chart_shares = _normalized_shares(chart_values, group.labels)
        for label in group.labels:
            baseline = baselines.get((group.key, label))
            if baseline is None:
                continue
            value = float(chart_shares.get(label, 0.0))
            z_score = (value - baseline.mean) / baseline.stdev
            if abs(z_score) >= DISTINGUISHING_Z_THRESHOLD:
                factors.append(
                    DistinguishingFactor(
                        group_key=group.key,
                        group_label=group.label,
                        raw_label=label,
                        factor_label=_label_text(label, group.key),
                        value_pct=value * 100.0,
                        mean_pct=baseline.mean * 100.0,
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
            lines.append(f"{_color_token(element, ELEMENT_COLORS.get(element))} makes up {share * 100.0:.1f}% of weighted elements.")
    mode_shares = _normalized_shares(calculate_mode_weights(chart), ("cardinal", "mutable", "fixed"))
    for mode, share in sorted(mode_shares.items(), key=lambda item: item[1], reverse=True):
        if share >= MODE_SHARE_THRESHOLD:
            lines.append(f"{_color_token(str(mode).title(), MODE_COLORS.get(mode))} makes up {share * 100.0:.1f}% of weighted modes.")
    return lines


def build_distinguishing_factors_html(chart: Chart | None, norm_charts: Iterable[Chart], metric_payloads: Iterable[dict[str, Any]] | None = None) -> str:
    """Build rich text for the Chart Analytics tab's distinguishing-factors section."""
    if chart is None:
        return "<span style='color:#f5f5f5;'>No chart loaded.</span>"

    if metric_payloads is not None:
        factors, norm_count = find_distinguishing_factors_from_metric_payloads(chart, metric_payloads)
    else:
        norm_chart_list = list(norm_charts)
        factors, norm_count = find_distinguishing_factors(chart, norm_chart_list)
    lines: list[str] = []
    if norm_count < MIN_NORM_SAMPLE_SIZE:
        lines.append(
            html.escape(f"Need at least {MIN_NORM_SAMPLE_SIZE} database charts to calculate norms; found {norm_count}.")
        )
    elif factors:
        lines.append(
            html.escape(
                f"Compared with {norm_count} database charts, these factors are at least "
                f"{DISTINGUISHING_Z_THRESHOLD:.0f}σ from the current norm:"
            )
        )
        for factor in factors:
            direction = "above" if factor.z_score > 0 else "below"
            lines.append(
                "• "
                f"{_factor_label_html(factor.group_key, factor.raw_label, factor.factor_label)} {html.escape(factor.group_label)}: "
                f"{factor.value_pct:.1f}% vs DB mean {factor.mean_pct:.1f}% "
                f"({abs(factor.z_score):.1f}σ {html.escape(direction)})."
            )
    else:
        lines.append(
            html.escape(
                f"Compared with {norm_count} database charts, no weighted factors currently exceed "
                f"the {DISTINGUISHING_Z_THRESHOLD:.0f}σ distinction threshold."
            )
        )

    concentration_lines = _concentration_lines(chart)
    if concentration_lines:
        lines.append("")
        lines.append(html.escape("Concentration flags:"))
        lines.extend(f"• {line}" for line in concentration_lines)

    duplicate_gates = _duplicate_human_design_gate_lines(chart)
    if duplicate_gates:
        lines.append("")
        lines.append(html.escape("Repeated Human Design gates:"))
        for gate, duplicate_lines in duplicate_gates[:10]:
            line_counts = Counter(duplicate_lines)
            line_text = ", ".join(
                _hd_gate_line_html(gate, line) + (f" ×{count}" if count > 1 else "")
                for line, count in sorted(line_counts.items())
            )
            lines.append(f"• {_hd_gate_label_html(gate)} appears {len(duplicate_lines)} times ({line_text}).")

    body = "<br>".join("<br>" if line == "" else line for line in lines)
    return (
        f"<span style='color:{CHART_DATA_HIGHLIGHT_COLOR}; font-weight:700;'>Database distinction scan</span>"
        f"<br><span style='color:#f5f5f5; font-weight:400;'>{body}</span>"
    )
