"""Shared Human Design aggregation helpers for chart commonality views."""
from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from ephemeraldaddy.analysis.human_design_reference import canonicalize_hd_authority_label

SimilarityMatches = list[tuple[str, int, int]]
SortMatches = Callable[[dict[str, int], int], SimilarityMatches]
ExtractHumanDesignProfile = Callable[[Any], tuple[Any, Any, Any, Any, Any, Any]]
ChartHumanDesignProfile = Callable[[Any], str]


@dataclass(frozen=True)
class HumanDesignSharedAggregates:
    """Common Human Design factors computed from one pass over charts."""

    gates: SimilarityMatches
    channels: SimilarityMatches
    defined_centers: SimilarityMatches
    authorities: SimilarityMatches
    profiles: SimilarityMatches


def normalize_human_design_channel(channel: object) -> str:
    """Return a stable channel label, ordering numeric gate endpoints."""

    normalized = str(channel).strip()
    if not normalized:
        return ""
    channel_parts = normalized.split("-")
    if (
        len(channel_parts) == 2
        and channel_parts[0].strip().isdigit()
        and channel_parts[1].strip().isdigit()
    ):
        gate_a = int(channel_parts[0].strip())
        gate_b = int(channel_parts[1].strip())
        return f"{min(gate_a, gate_b)}-{max(gate_a, gate_b)}"
    return normalized


def _ordered_channel_counts(channel_counts: dict[str, int]) -> dict[str, int]:
    ordered_labels = sorted(
        channel_counts.keys(),
        key=lambda label: (
            int(label.split("-")[0])
            if "-" in label and label.split("-")[0].isdigit()
            else 999,
            int(label.split("-")[1])
            if "-" in label and len(label.split("-")) > 1 and label.split("-")[1].isdigit()
            else 999,
            label,
        ),
    )
    return {label: channel_counts[label] for label in ordered_labels}


def _ordered_known_then_extra_counts(
    counts: dict[str, int],
    ordered_labels: Sequence[str],
) -> dict[str, int]:
    ordered_counts = {label: counts[label] for label in ordered_labels if label in counts}
    for label in sorted(set(counts) - set(ordered_counts)):
        ordered_counts[label] = counts[label]
    return ordered_counts


def compute_common_human_design_aggregates(
    charts: Iterable[Any],
    *,
    extract_profile: ExtractHumanDesignProfile,
    chart_profile: ChartHumanDesignProfile,
    sort_matches: SortMatches,
    defined_center_order: Sequence[str],
    authority_order: Sequence[str],
    profile_order: Sequence[str],
) -> HumanDesignSharedAggregates:
    """Compute all common Human Design aggregates with one profile extraction per chart."""

    chart_list = [chart for chart in charts if chart is not None]
    chart_count = len(chart_list)
    if chart_count < 2:
        empty: SimilarityMatches = []
        return HumanDesignSharedAggregates(empty, empty, empty, empty, empty)

    gate_counts: dict[str, int] = {}
    channel_counts: dict[str, int] = {}
    center_counts: dict[str, int] = {}
    authority_counts: dict[str, int] = {}
    profile_counts: dict[str, int] = {}

    for chart in chart_list:
        hd_gates, _hd_lines, hd_channels, hd_defined_centers, _hd_type, hd_authority = extract_profile(chart)

        for gate in sorted({int(gate) for gate in hd_gates if str(gate).strip().isdigit()}):
            label = f"Gate {gate}"
            gate_counts[label] = gate_counts.get(label, 0) + 1

        for channel in {normalize_human_design_channel(channel) for channel in hd_channels}:
            if channel:
                channel_counts[channel] = channel_counts.get(channel, 0) + 1

        for center in {str(center).strip() for center in hd_defined_centers if str(center).strip()}:
            center_counts[center] = center_counts.get(center, 0) + 1

        authority = canonicalize_hd_authority_label(str(hd_authority).strip())
        if authority:
            authority_counts[authority] = authority_counts.get(authority, 0) + 1

        profile = chart_profile(chart)
        if profile:
            profile_counts[profile] = profile_counts.get(profile, 0) + 1

    ordered_gate_counts = {
        f"Gate {gate}": gate_counts[f"Gate {gate}"]
        for gate in range(1, 65)
        if f"Gate {gate}" in gate_counts
    }

    return HumanDesignSharedAggregates(
        gates=sort_matches(ordered_gate_counts, chart_count),
        channels=sort_matches(_ordered_channel_counts(channel_counts), chart_count),
        defined_centers=sort_matches(
            _ordered_known_then_extra_counts(center_counts, defined_center_order), chart_count
        ),
        authorities=sort_matches(
            _ordered_known_then_extra_counts(authority_counts, authority_order), chart_count
        ),
        profiles=sort_matches(
            _ordered_known_then_extra_counts(profile_counts, profile_order), chart_count
        ),
    )
