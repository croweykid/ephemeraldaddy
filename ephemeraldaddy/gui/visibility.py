"""Visibility defaults and persistence helpers for UI data sections."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings

SETTINGS_GROUP = "visibility"

OPTIONAL_MODULE_KEYS: dict[str, bool] = {
    "optional_modules.human_design": False,
    "optional_modules.anagrams": False,
    "optional_modules.bazi": False,
    "optional_modules.dndification": False,
    "optional_modules.event_predictor": False,
    "optional_modules.cursedness": True,
}

OPTIONAL_MODULE_ALIASES: dict[str, str] = {
    "chart_data.cursedness": "optional_modules.cursedness",
    "chart_data.dnd_output": "optional_modules.dndification",
    "chart_data.human_design_alpha_prototype": "optional_modules.human_design",
    "chart_analytics.anagrams": "optional_modules.anagrams",
    "database_metrics_visibility.bazi": "optional_modules.bazi",
    "database_metrics_visibility.human_design": "optional_modules.human_design",
    "database_metrics_visibility.species_distribution": "optional_modules.dndification",
}

# Backwards-compatible names for callers that still iterate older setting groups.
CHART_DATA_KEYS: dict[str, bool] = {
    "chart_data.cursedness": OPTIONAL_MODULE_KEYS["optional_modules.cursedness"],
    "chart_data.dnd_output": OPTIONAL_MODULE_KEYS["optional_modules.dndification"],
    "chart_data.human_design_alpha_prototype": OPTIONAL_MODULE_KEYS["optional_modules.human_design"],
    "popout.synastry_aspect_weights": False,
    "chart_analytics.planet_dynamics": False,
    "chart_analytics.anagrams": OPTIONAL_MODULE_KEYS["optional_modules.anagrams"],
}

DATABASE_ANALYTICS_VISIBILITY_KEYS: dict[str, bool] = {
    "database_metrics_visibility.species_distribution": OPTIONAL_MODULE_KEYS["optional_modules.dndification"],
    "database_metrics_visibility.bazi": OPTIONAL_MODULE_KEYS["optional_modules.bazi"],
    "database_metrics_visibility.human_design": OPTIONAL_MODULE_KEYS["optional_modules.human_design"],
    "database_metrics_visibility.enneagram": True,
}

DATABASE_ANALYTICS_SECTION_KEYS: dict[str, bool] = {
    "database_metrics.planetary_sign_prevalence": False,
    "database_metrics.sentiment_prevalence": False,
    "database_metrics.relationship_prevalence": False,
    "database_metrics.social_score_summary": False,
    "database_metrics.alignment_summary": False,
    "database_metrics.sign_prevalence": False,
    "database_metrics.dominant_signs": False,
    "database_metrics.subordinant_factors": False,
    "database_metrics.species_distribution": False,
    "database_metrics.enneagram": False,
    "database_metrics.birth_time": False,
    "database_metrics.age": False,
    "database_metrics.birth_month": False,
    "database_metrics.birthplace": False,
    "database_metrics.tag_distribution": False,
    "database_metrics.gender": False,
    "database_metrics.human_design": False,
    "database_metrics.bazi": False,
}

DEFAULT_VISIBILITY: dict[str, bool] = {
    **OPTIONAL_MODULE_KEYS,
    **CHART_DATA_KEYS,
    **DATABASE_ANALYTICS_SECTION_KEYS,
    **DATABASE_ANALYTICS_VISIBILITY_KEYS,
}


@dataclass
class VisibilityStore:
    settings: QSettings

    def get(self, key: str) -> bool:
        canonical_key = OPTIONAL_MODULE_ALIASES.get(key, key)
        default = DEFAULT_VISIBILITY.get(canonical_key, DEFAULT_VISIBILITY.get(key, True))
        raw = self.settings.value(f"{SETTINGS_GROUP}/{canonical_key}", None)
        if raw is None and canonical_key != key:
            raw = self.settings.value(f"{SETTINGS_GROUP}/{key}", None)
        if raw is None:
            raw = default
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}

    def set(self, key: str, visible: bool) -> None:
        canonical_key = OPTIONAL_MODULE_ALIASES.get(key, key)
        self.settings.setValue(f"{SETTINGS_GROUP}/{canonical_key}", bool(visible))
        if canonical_key != key:
            self.settings.setValue(f"{SETTINGS_GROUP}/{key}", bool(visible))

    def reset_defaults(self) -> None:
        for key, default in DEFAULT_VISIBILITY.items():
            self.set(key, default)
