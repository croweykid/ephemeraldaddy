"""Explain the factor activations behind semantic Theme prominence scores.

This module deliberately reuses the activation context and item resolver from
``theme_prominence``.  Chart Info therefore explains the exact inputs consumed
by the scorer instead of reconstructing a second, potentially divergent notion
of what is active in a chart.

Only positive active evidence is returned here.  A future taxonomy may add
negative membership weights/counter-evidence; those should be rendered as a
separate concept rather than described as reasons a theme is prominent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ephemeraldaddy.analysis import theme_prominence as prominence
from ephemeraldaddy.core.theme_reference import (
    THEMES,
    WEIGHTED_THEME_PROPERTIES,
    theme_item_weight,
    themes_in_family,
)


@dataclass(frozen=True)
class ThemeFactorEvidence:
    """One positively active configured factor supporting a subtheme score."""

    property_name: str
    item: Any
    activation: float
    weight: float
    weighted_activation: float


def _evidence_for_theme(
    theme_key: str,
    context: Mapping[str, Any],
) -> tuple[ThemeFactorEvidence, ...]:
    theme = THEMES[theme_key]
    rows: list[ThemeFactorEvidence] = []
    for property_name in WEIGHTED_THEME_PROPERTIES:
        for item in theme.get(property_name, []) or []:
            activation = prominence._activation_for_item(property_name, item, context)
            if activation is None or float(activation) <= 0.0:
                continue
            weight = float(theme_item_weight(theme_key, property_name, item))
            weighted_activation = float(activation) * weight
            if weight <= 0.0 or weighted_activation <= 0.0:
                continue
            rows.append(
                ThemeFactorEvidence(
                    property_name=property_name,
                    item=item,
                    activation=max(0.0, min(1.0, float(activation))),
                    weight=weight,
                    weighted_activation=weighted_activation,
                )
            )
    return tuple(rows)


def calculate_theme_factor_evidence(
    chart: Any,
    theme_keys: Sequence[str] | None = None,
) -> dict[str, tuple[ThemeFactorEvidence, ...]]:
    """Return positive supporting factors for requested subthemes.

    The activation context is built once per request, which is important for
    Human Design and BaZi because those systems can be materially more expensive
    than simple sign/body lookups.
    """

    keys = tuple(theme_keys) if theme_keys is not None else tuple(THEMES)
    unknown = [key for key in keys if key not in THEMES]
    if unknown:
        raise KeyError(f"Unknown Theme key(s): {', '.join(map(str, unknown))}")

    context = prominence._activation_context(chart)
    return calculate_theme_factor_evidence_from_context(context, keys)


def calculate_theme_factor_evidence_from_context(
    context: Mapping[str, Any],
    theme_keys: Sequence[str] | None = None,
) -> dict[str, tuple[ThemeFactorEvidence, ...]]:
    """Return evidence using an activation context already built for scoring."""
    keys = tuple(theme_keys) if theme_keys is not None else tuple(THEMES)
    unknown = [key for key in keys if key not in THEMES]
    if unknown:
        raise KeyError(f"Unknown Theme key(s): {', '.join(map(str, unknown))}")
    return {key: _evidence_for_theme(key, context) for key in keys}


def calculate_theme_family_factor_evidence(
    chart: Any,
    family_key: str,
) -> dict[str, tuple[ThemeFactorEvidence, ...]]:
    """Return positive evidence for every subtheme in one macrotheme family."""

    return calculate_theme_factor_evidence(chart, tuple(themes_in_family(family_key)))
