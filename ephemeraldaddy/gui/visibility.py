"""Visibility defaults and persistence helpers for UI data sections."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings

SETTINGS_GROUP = "visibility"

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
    "database_metrics.gender": False,
    "database_metrics.human_design": False,
    "database_metrics.bazi": False,
}

DEFAULT_VISIBILITY: dict[str, bool] = {
    **CHART_DATA_KEYS,
    **DATABASE_ANALYTICS_SECTION_KEYS,
    **DATABASE_ANALYTICS_VISIBILITY_KEYS,
}


@dataclass
class VisibilityStore:
    settings: QSettings

    def get(self, key: str) -> bool:
        default = DEFAULT_VISIBILITY.get(key, True)
        raw = self.settings.value(f"{SETTINGS_GROUP}/{key}", default)
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}

    def set(self, key: str, visible: bool) -> None:
        self.settings.setValue(f"{SETTINGS_GROUP}/{key}", bool(visible))

    def reset_defaults(self) -> None:
        for key, default in DEFAULT_VISIBILITY.items():
            self.set(key, default)
