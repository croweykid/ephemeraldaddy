from __future__ import annotations

from ephemeraldaddy.analysis.get_astro_twin import SimilarityCalculatorSettings

SETTINGS_KEY_SIMILAR_CALCULATOR = "similar_charts/similarities_calculator"

SIMILARITY_CALCULATOR_ROWS: tuple[tuple[str, str], ...] = (
    ("placement", "Placement score"),
    ("aspect", "Aspect score"),
    ("distribution", "Distribution score"),
    ("combined_dominance", "Combined dominance score"),
    ("nakshatra_placement", "Nakshatra placement score"),
    ("nakshatra_dominance", "Nakshatra dominance score"),
    ("defined_centers", "Defined centers score"),
)


def defaults_similarity_calculator_settings() -> SimilarityCalculatorSettings:
    return SimilarityCalculatorSettings.defaults_from_comprehensive()


def load_similarity_calculator_settings(settings) -> SimilarityCalculatorSettings:
    defaults = defaults_similarity_calculator_settings()
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

    values = {
        "use_placement": _as_bool(payload.get("use_placement", defaults.use_placement), defaults.use_placement),
        "weight_placement": float(payload.get("weight_placement", defaults.weight_placement)),
        "use_aspect": _as_bool(payload.get("use_aspect", defaults.use_aspect), defaults.use_aspect),
        "weight_aspect": float(payload.get("weight_aspect", defaults.weight_aspect)),
        "use_distribution": _as_bool(payload.get("use_distribution", defaults.use_distribution), defaults.use_distribution),
        "weight_distribution": float(payload.get("weight_distribution", defaults.weight_distribution)),
        "use_combined_dominance": _as_bool(payload.get("use_combined_dominance", defaults.use_combined_dominance), defaults.use_combined_dominance),
        "weight_combined_dominance": float(payload.get("weight_combined_dominance", defaults.weight_combined_dominance)),
        "use_nakshatra_placement": _as_bool(payload.get("use_nakshatra_placement", defaults.use_nakshatra_placement), defaults.use_nakshatra_placement),
        "weight_nakshatra_placement": float(payload.get("weight_nakshatra_placement", defaults.weight_nakshatra_placement)),
        "use_nakshatra_dominance": _as_bool(payload.get("use_nakshatra_dominance", defaults.use_nakshatra_dominance), defaults.use_nakshatra_dominance),
        "weight_nakshatra_dominance": float(payload.get("weight_nakshatra_dominance", defaults.weight_nakshatra_dominance)),
        "use_defined_centers": _as_bool(payload.get("use_defined_centers", defaults.use_defined_centers), defaults.use_defined_centers),
        "weight_defined_centers": float(payload.get("weight_defined_centers", defaults.weight_defined_centers)),
    }
    return SimilarityCalculatorSettings(**values)


def save_similarity_calculator_settings(settings, value: SimilarityCalculatorSettings) -> None:
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
            "use_nakshatra_placement": bool(value.use_nakshatra_placement),
            "weight_nakshatra_placement": float(value.weight_nakshatra_placement),
            "use_nakshatra_dominance": bool(value.use_nakshatra_dominance),
            "weight_nakshatra_dominance": float(value.weight_nakshatra_dominance),
            "use_defined_centers": bool(value.use_defined_centers),
            "weight_defined_centers": float(value.weight_defined_centers),
        },
    )
