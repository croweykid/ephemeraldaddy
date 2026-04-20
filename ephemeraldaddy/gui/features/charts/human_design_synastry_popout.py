"""Helpers for Human Design synastry (composite) popouts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ephemeraldaddy.analysis.human_design import build_human_design_result
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.human_design_system import CHANNELS, HumanDesignResult

HD_SYNASTRY_PRIMARY_COLOR = "#f39c12"  # chart 1 orange
HD_SYNASTRY_SECONDARY_COLOR = "#4da3ff"  # chart 2 blue
HD_SYNASTRY_STRIPE_PATTERN = (2.0, 2.0)


@dataclass(frozen=True)
class HumanDesignSynastryBundle:
    chart_one_result: HumanDesignResult
    chart_two_result: HumanDesignResult
    chart_one_gates: frozenset[int]
    chart_two_gates: frozenset[int]
    shared_gates: frozenset[int]
    combined_result: HumanDesignResult


def _defined_channels_for_gates(active_gates: Iterable[int]) -> tuple[tuple[int, int, str, str], ...]:
    gate_set = {int(gate) for gate in active_gates}
    channels: list[tuple[int, int, str, str]] = []
    seen: set[tuple[int, int]] = set()
    for gate_a, gate_b, center_a, center_b in CHANNELS:
        channel_key = tuple(sorted((int(gate_a), int(gate_b))))
        if channel_key in seen:
            continue
        seen.add(channel_key)
        if gate_a in gate_set and gate_b in gate_set:
            channels.append((int(gate_a), int(gate_b), str(center_a), str(center_b)))
    return tuple(channels)


def build_human_design_synastry_bundle(
    chart_one: Chart,
    chart_two: Chart,
) -> HumanDesignSynastryBundle:
    chart_one_result = build_human_design_result(chart_one)
    chart_two_result = build_human_design_result(chart_two)

    chart_one_gates = frozenset(int(gate) for gate in chart_one_result.active_gates)
    chart_two_gates = frozenset(int(gate) for gate in chart_two_result.active_gates)
    shared_gates = frozenset(chart_one_gates & chart_two_gates)
    combined_gates = frozenset(chart_one_gates | chart_two_gates)

    combined_channels = _defined_channels_for_gates(combined_gates)
    combined_centers = frozenset(
        {
            str(center)
            for _gate_a, _gate_b, center_a, center_b in combined_channels
            for center in (center_a, center_b)
        }
    )

    combined_result = HumanDesignResult(
        birth_utc=chart_one_result.birth_utc,
        design_utc=chart_one_result.design_utc,
        personality_activations=chart_one_result.personality_activations,
        design_activations=chart_two_result.design_activations,
        active_gates=combined_gates,
        defined_channels=combined_channels,
        defined_centers=combined_centers,
        hd_type=f"{chart_one_result.hd_type} + {chart_two_result.hd_type}",
        authority=f"{chart_one_result.authority} + {chart_two_result.authority}",
        profile=f"{chart_one_result.profile} + {chart_two_result.profile}",
        strategy=f"{chart_one_result.strategy} + {chart_two_result.strategy}",
        split_definition="Synastry Composite",
        incarnation_cross="Synastry Composite",
    )

    return HumanDesignSynastryBundle(
        chart_one_result=chart_one_result,
        chart_two_result=chart_two_result,
        chart_one_gates=chart_one_gates,
        chart_two_gates=chart_two_gates,
        shared_gates=shared_gates,
        combined_result=combined_result,
    )


def build_human_design_synastry_summary_lines(
    chart_one_name: str,
    chart_two_name: str,
    bundle: HumanDesignSynastryBundle,
) -> list[str]:
    return [
        "Human Design Synastry Composite",
        "------------------------------",
        f"Chart 1 (orange): {chart_one_name}",
        f"Chart 2 (blue): {chart_two_name}",
        f"Chart 1 gates: {', '.join(str(gate) for gate in sorted(bundle.chart_one_gates)) or 'None'}",
        f"Chart 2 gates: {', '.join(str(gate) for gate in sorted(bundle.chart_two_gates)) or 'None'}",
        f"Shared gates (striped): {', '.join(str(gate) for gate in sorted(bundle.shared_gates)) or 'None'}",
        f"Combined active gates: {len(bundle.combined_result.active_gates)}",
        f"Combined defined channels: {len(bundle.combined_result.defined_channels)}",
        f"Combined defined centers: {len(bundle.combined_result.defined_centers)}",
    ]
