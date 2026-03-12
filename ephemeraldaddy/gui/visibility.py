"""Visibility defaults and persistence helpers for UI data sections."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings

SETTINGS_GROUP = "visibility"

CHART_DATA_KEYS: dict[str, bool] = {
    "chart_data.cursedness": True,
    "chart_data.dnd_species": True,
}

DATABASE_ANALYTICS_SECTION_KEYS: dict[str, bool] = {
    "database_metrics.planetary_sign_prevalence": False,
    "database_metrics.sentiment_prevalence": False,
    "database_metrics.relationship_prevalence": False,
    "database_metrics.social_score_summary": False,
    "database_metrics.sign_prevalence": False,
    "database_metrics.dominant_signs": False,
    "database_metrics.species_distribution": False,
    "database_metrics.birth_time": False,
    "database_metrics.age": False,
    "database_metrics.birth_month": False,
    "database_metrics.birthplace": False,
}

DEFAULT_VISIBILITY: dict[str, bool] = {
    **CHART_DATA_KEYS,
    **DATABASE_ANALYTICS_SECTION_KEYS,
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
