"""Visibility defaults and persistence helpers for UI data sections."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings

SETTINGS_GROUP = "visibility"

OPTIONAL_MODULE_KEYS: dict[str, bool] = {
    "optional_modules.human_design": False,
    "optional_modules.anagrams": False,
    "optional_modules.bazi": False,
    "optional_modules.dndification": True,
    "optional_modules.event_predictor": False,
    "optional_modules.cursedness": True,
}

CHART_DATA_KEYS: dict[str, bool] = {
    "chart_data.cursedness": True,
    "chart_data.dnd_output": True,
    "chart_data.human_design_alpha_prototype": False,
    "popout.synastry_aspect_weights": False,
    "chart_analytics.planet_dynamics": False,
    "chart_analytics.anagrams": False,
}

DATABASE_ANALYTICS_VISIBILITY_KEYS: dict[str, bool] = {
    "database_metrics_visibility.species_distribution": False,
    "database_metrics_visibility.bazi": False,
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
    **CHART_DATA_KEYS,
    **DATABASE_ANALYTICS_SECTION_KEYS,
    **DATABASE_ANALYTICS_VISIBILITY_KEYS,
    **OPTIONAL_MODULE_KEYS,
}

VISIBILITY_KEY_ALIASES: dict[str, tuple[str, ...]] = {
    "optional_modules.human_design": ("chart_data.human_design_alpha_prototype",),
    "optional_modules.anagrams": ("chart_analytics.anagrams",),
    "optional_modules.bazi": ("database_metrics_visibility.bazi",),
    "optional_modules.dndification": (
        "chart_data.dnd_output",
        "database_metrics_visibility.species_distribution",
    ),
    "optional_modules.cursedness": ("chart_data.cursedness",),
}


@dataclass
class VisibilityStore:
    settings: QSettings

    def get(self, key: str) -> bool:
        default = DEFAULT_VISIBILITY.get(key, True)
        settings_key = f"{SETTINGS_GROUP}/{key}"
        raw = self.settings.value(settings_key, default)
        if not self.settings.contains(settings_key):
            for alias in VISIBILITY_KEY_ALIASES.get(key, ()):
                alias_key = f"{SETTINGS_GROUP}/{alias}"
                if self.settings.contains(alias_key):
                    raw = self.settings.value(alias_key, default)
                    break
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}

    def set(self, key: str, visible: bool) -> None:
        normalized = bool(visible)
        self.settings.setValue(f"{SETTINGS_GROUP}/{key}", normalized)
        for alias in VISIBILITY_KEY_ALIASES.get(key, ()):
            self.settings.setValue(f"{SETTINGS_GROUP}/{alias}", normalized)

    def reset_defaults(self) -> None:
        for key, default in DEFAULT_VISIBILITY.items():
            self.set(key, default)
