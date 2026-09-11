"""Persistence mapping for Astro Twin similarity calculator settings."""

from __future__ import annotations

from typing import Protocol

from ephemeraldaddy.analysis.get_astro_twin import (
    DOMINANCE_COMPONENT_KEYS,
    SimilarityCalculatorSettings,
    normalize_all_or_nothing_component,
    normalize_astro_twin_demographic_match_mode,
    normalize_placement_weighting_mode,
)

SETTINGS_KEY_SIMILAR_CALCULATOR = "similar_charts/similarities_calculator"


class SettingsStore(Protocol):
    """Minimal settings boundary required by this workflow."""

    def value(self, key: str, default: object = ...) -> object: ...

    def setValue(self, key: str, value: object) -> None: ...


def similarity_calculator_settings_defaults() -> SimilarityCalculatorSettings:
    return SimilarityCalculatorSettings.defaults_for_default_mode()


def load_similarity_calculator_settings(settings: SettingsStore) -> SimilarityCalculatorSettings:
    defaults = similarity_calculator_settings_defaults()
    payload = settings.value(SETTINGS_KEY_SIMILAR_CALCULATOR, {})
    if not isinstance(payload, dict):
        payload = {}
    def _as_bool(value: object, fallback: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        return fallback
    legacy_combined_weight = float(payload.get("weight_combined_dominance", defaults.weight_combined_dominance))
    legacy_combined_enabled = _as_bool(
        payload.get("use_combined_dominance", defaults.use_combined_dominance),
        defaults.use_combined_dominance,
    )
    has_granular_dominance_payload = any(
        f"use_{key}" in payload or f"weight_{key}" in payload
        for key in DOMINANCE_COMPONENT_KEYS
    )

    def _dominance_enabled(key: str, fallback: bool) -> bool:
        if has_granular_dominance_payload:
            return _as_bool(payload.get(f"use_{key}", fallback), fallback)
        return legacy_combined_enabled

    def _dominance_weight(key: str, fallback: float) -> float:
        if has_granular_dominance_payload:
            return float(payload.get(f"weight_{key}", fallback))
        return legacy_combined_weight / len(DOMINANCE_COMPONENT_KEYS)
    values = {
        "use_placement": _as_bool(payload.get("use_placement", defaults.use_placement), defaults.use_placement),
        "weight_placement": float(payload.get("weight_placement", defaults.weight_placement)),
        "use_aspect": _as_bool(payload.get("use_aspect", defaults.use_aspect), defaults.use_aspect),
        "weight_aspect": float(payload.get("weight_aspect", defaults.weight_aspect)),
        "use_distribution": _as_bool(payload.get("use_distribution", defaults.use_distribution), defaults.use_distribution),
        "weight_distribution": float(payload.get("weight_distribution", defaults.weight_distribution)),
        "use_combined_dominance": legacy_combined_enabled,
        "weight_combined_dominance": legacy_combined_weight,
        "use_dominant_bodies": _dominance_enabled("dominant_bodies", defaults.use_dominant_bodies),
        "weight_dominant_bodies": _dominance_weight("dominant_bodies", defaults.weight_dominant_bodies),
        "use_dominant_houses": _dominance_enabled("dominant_houses", defaults.use_dominant_houses),
        "weight_dominant_houses": _dominance_weight("dominant_houses", defaults.weight_dominant_houses),
        "use_dominant_signs": _dominance_enabled("dominant_signs", defaults.use_dominant_signs),
        "weight_dominant_signs": _dominance_weight("dominant_signs", defaults.weight_dominant_signs),
        "use_dominant_nakshatras": _dominance_enabled("dominant_nakshatras", defaults.use_dominant_nakshatras),
        "weight_dominant_nakshatras": _dominance_weight("dominant_nakshatras", defaults.weight_dominant_nakshatras),
        "use_nakshatra_placement": _as_bool(payload.get("use_nakshatra_placement", defaults.use_nakshatra_placement), defaults.use_nakshatra_placement),
        "weight_nakshatra_placement": float(payload.get("weight_nakshatra_placement", defaults.weight_nakshatra_placement)),
        "use_nakshatra_dominance": _as_bool(payload.get("use_nakshatra_dominance", defaults.use_nakshatra_dominance), defaults.use_nakshatra_dominance),
        "weight_nakshatra_dominance": float(payload.get("weight_nakshatra_dominance", defaults.weight_nakshatra_dominance)),
        "use_defined_centers": _as_bool(payload.get("use_defined_centers", defaults.use_defined_centers), defaults.use_defined_centers),
        "weight_defined_centers": float(payload.get("weight_defined_centers", defaults.weight_defined_centers)),
        "use_human_design_gates": _as_bool(payload.get("use_human_design_gates", defaults.use_human_design_gates), defaults.use_human_design_gates),
        "weight_human_design_gates": float(payload.get("weight_human_design_gates", defaults.weight_human_design_gates)),
        "use_human_design_channels": _as_bool(payload.get("use_human_design_channels", defaults.use_human_design_channels), defaults.use_human_design_channels),
        "weight_human_design_channels": float(payload.get("weight_human_design_channels", defaults.weight_human_design_channels)),
        "use_inner_planet_placement": _as_bool(payload.get("use_inner_planet_placement", defaults.use_inner_planet_placement), defaults.use_inner_planet_placement),
        "weight_inner_planet_placement": float(payload.get("weight_inner_planet_placement", defaults.weight_inner_planet_placement)),
        "use_outer_planet_placement": _as_bool(payload.get("use_outer_planet_placement", defaults.use_outer_planet_placement), defaults.use_outer_planet_placement),
        "weight_outer_planet_placement": float(payload.get("weight_outer_planet_placement", defaults.weight_outer_planet_placement)),
        "use_big_3": _as_bool(payload.get("use_big_3", defaults.use_big_3), defaults.use_big_3),
        "weight_big_3": float(payload.get("weight_big_3", defaults.weight_big_3)),
        "placement_weighting_mode": normalize_placement_weighting_mode(
            payload.get("placement_weighting_mode", defaults.placement_weighting_mode)
        ),
        "all_or_nothing_component": normalize_all_or_nothing_component(
            payload.get("all_or_nothing_component", defaults.all_or_nothing_component)
        ),
        "demographic_match_mode": normalize_astro_twin_demographic_match_mode(
            payload.get("demographic_match_mode", defaults.demographic_match_mode)
        ),
    }
    return SimilarityCalculatorSettings(**values)


def save_similarity_calculator_settings(settings: SettingsStore, value: SimilarityCalculatorSettings) -> None:
    settings.setValue(
        SETTINGS_KEY_SIMILAR_CALCULATOR,
        {
            "use_placement": bool(value.use_placement),
            "weight_placement": float(value.weight_placement),
            "use_aspect": bool(value.use_aspect),
            "weight_aspect": float(value.weight_aspect),
            "use_distribution": bool(value.use_distribution),
            "weight_distribution": float(value.weight_distribution),
            "use_combined_dominance": bool(value.use_combined_dominance),
            "weight_combined_dominance": float(value.weight_combined_dominance),
            "use_dominant_bodies": bool(value.use_dominant_bodies),
            "weight_dominant_bodies": float(value.weight_dominant_bodies),
            "use_dominant_houses": bool(value.use_dominant_houses),
            "weight_dominant_houses": float(value.weight_dominant_houses),
            "use_dominant_signs": bool(value.use_dominant_signs),
            "weight_dominant_signs": float(value.weight_dominant_signs),
            "use_dominant_nakshatras": bool(value.use_dominant_nakshatras),
            "weight_dominant_nakshatras": float(value.weight_dominant_nakshatras),
            "use_nakshatra_placement": bool(value.use_nakshatra_placement),
            "weight_nakshatra_placement": float(value.weight_nakshatra_placement),
            "use_nakshatra_dominance": bool(value.use_nakshatra_dominance),
            "weight_nakshatra_dominance": float(value.weight_nakshatra_dominance),
            "use_defined_centers": bool(value.use_defined_centers),
            "weight_defined_centers": float(value.weight_defined_centers),
            "use_human_design_gates": bool(value.use_human_design_gates),
            "weight_human_design_gates": float(value.weight_human_design_gates),
            "use_human_design_channels": bool(value.use_human_design_channels),
            "weight_human_design_channels": float(value.weight_human_design_channels),
            "use_inner_planet_placement": bool(value.use_inner_planet_placement),
            "weight_inner_planet_placement": float(value.weight_inner_planet_placement),
            "use_outer_planet_placement": bool(value.use_outer_planet_placement),
            "weight_outer_planet_placement": float(value.weight_outer_planet_placement),
            "use_big_3": bool(value.use_big_3),
            "weight_big_3": float(value.weight_big_3),
            "placement_weighting_mode": normalize_placement_weighting_mode(value.placement_weighting_mode),
            "all_or_nothing_component": normalize_all_or_nothing_component(value.all_or_nothing_component),
            "demographic_match_mode": normalize_astro_twin_demographic_match_mode(value.demographic_match_mode),
        },
    )
