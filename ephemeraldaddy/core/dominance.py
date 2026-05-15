"""Shared dominance threshold helpers for elemental and modal chart summaries."""

from __future__ import annotations


def _weight_share(value: float, total: float) -> float:
    return float(value) / total if total > 0.0 else 0.0


def dominant_mode_labels_from_weights(
    mode_weights: dict[str, float],
    *,
    threshold: float = 1.0 / 3.0,
) -> list[str]:
    """Return modes that qualify as app-wide dominant modes.

    Modal dominance is intentionally stricter than sign/body/house dominance:
    with only three modes available, a mode must be tied for the highest modal
    share and clear the natural one-third baseline. This prevents a chart's least
    represented mode from satisfying a generic "mutable/cardinal/fixed emphasis"
    criterion merely because it has a non-zero share.
    """
    ordered_modes = ["cardinal", "fixed", "mutable"]
    total = sum(max(0.0, float(mode_weights.get(mode, 0.0))) for mode in ordered_modes)
    if total <= 0.0:
        return []
    shares = {mode: _weight_share(max(0.0, float(mode_weights.get(mode, 0.0))), total) for mode in ordered_modes}
    top_share = max(shares.values())
    return [
        mode
        for mode in ordered_modes
        if shares[mode] == top_share and shares[mode] > threshold
    ]


def dominant_element_labels_from_weights(
    element_weights: dict[str, float],
    *,
    threshold: float = 0.25,
) -> list[str]:
    """Return elements that qualify as app-wide dominant elements.

    Elemental dominance uses the four-element baseline: an element must exceed
    25% of the elemental weight budget. Unlike signs/bodies/houses, elements do
    not use a top-three shortcut because that would classify nearly every
    non-empty chart as dominant in most elements.
    """
    ordered_elements = ["Fire", "Earth", "Air", "Water"]
    total = sum(max(0.0, float(element_weights.get(element, 0.0))) for element in ordered_elements)
    if total <= 0.0:
        return []
    return [
        element
        for element in ordered_elements
        if _weight_share(max(0.0, float(element_weights.get(element, 0.0))), total) > threshold
    ]
