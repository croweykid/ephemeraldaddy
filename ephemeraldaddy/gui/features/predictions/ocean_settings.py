"""Persistent scoring configuration for the OCEAN predictor."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


SETTINGS_KEY_OCEAN_PREDICTOR_WEIGHTS = "predictions/ocean_predictor_weights"


@dataclass(frozen=True)
class OceanPredictorWeights:
    """Enabled OCEAN evidence categories and their relative contributions."""

    use_sign_weights: bool = True
    sign_weight: float = 45.0
    use_body_weights: bool = True
    body_weight: float = 25.0
    use_nakshatra_weights: bool = True
    nakshatra_weight: float = 10.0
    use_elemental_weights: bool = True
    elemental_weight: float = 10.0
    use_house_weights: bool = True
    house_weight: float = 10.0


OCEAN_WEIGHT_ROWS = (
    ("sign", "use sign weights", 45.0),
    ("body", "use body/planet weights", 25.0),
    ("nakshatra", "use nakshatra weights", 10.0),
    ("elemental", "use elemental weights", 10.0),
    (
        "house",
        "use house weights (if/when available via known birth time or rectified time)",
        10.0,
    ),
)


def ocean_predictor_weights_from_payload(payload: Any) -> OceanPredictorWeights:
    values = payload if isinstance(payload, dict) else {}
    defaults = OceanPredictorWeights()
    updates: dict[str, Any] = {}
    for key, _label, _default in OCEAN_WEIGHT_ROWS:
        enabled_name = f"use_{key}_weights"
        weight_name = f"{key}_weight"
        updates[enabled_name] = bool(
            values.get(enabled_name, getattr(defaults, enabled_name))
        )
        try:
            updates[weight_name] = max(
                0.0,
                min(
                    100.0,
                    float(values.get(weight_name, getattr(defaults, weight_name))),
                ),
            )
        except (TypeError, ValueError):
            updates[weight_name] = getattr(defaults, weight_name)
    return replace(defaults, **updates)


def ocean_predictor_weights_to_payload(config: OceanPredictorWeights) -> dict[str, Any]:
    return {
        name: getattr(config, name)
        for key, _label, _default in OCEAN_WEIGHT_ROWS
        for name in (f"use_{key}_weights", f"{key}_weight")
    }


def load_ocean_predictor_weights(settings: Any) -> OceanPredictorWeights:
    return ocean_predictor_weights_from_payload(
        settings.value(SETTINGS_KEY_OCEAN_PREDICTOR_WEIGHTS, {}) or {}
    )


def save_ocean_predictor_weights(settings: Any, config: OceanPredictorWeights) -> None:
    settings.setValue(
        SETTINGS_KEY_OCEAN_PREDICTOR_WEIGHTS, ocean_predictor_weights_to_payload(config)
    )
