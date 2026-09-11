from __future__ import annotations

from dataclasses import asdict

from ephemeraldaddy.analysis.get_astro_twin import DOMINANCE_COMPONENT_KEYS
from ephemeraldaddy.gui.features.similarities.settings import (
    SETTINGS_KEY_SIMILAR_CALCULATOR,
    load_similarity_calculator_settings,
    save_similarity_calculator_settings,
    similarity_calculator_settings_defaults,
)


class MemorySettings:
    def __init__(self, payload: object = None) -> None:
        self.values = {SETTINGS_KEY_SIMILAR_CALCULATOR: payload}

    def value(self, key: str, default: object = None) -> object:
        return self.values.get(key, default)

    def setValue(self, key: str, value: object) -> None:
        self.values[key] = value


def test_similarity_settings_round_trip_all_fields() -> None:
    settings = MemorySettings()
    expected = similarity_calculator_settings_defaults()

    save_similarity_calculator_settings(settings, expected)
    actual = load_similarity_calculator_settings(settings)

    assert asdict(actual) == asdict(expected)


def test_legacy_combined_dominance_is_distributed_across_components() -> None:
    settings = MemorySettings(
        {"use_combined_dominance": False, "weight_combined_dominance": 28.0}
    )

    loaded = load_similarity_calculator_settings(settings)

    for key in DOMINANCE_COMPONENT_KEYS:
        assert getattr(loaded, f"use_{key}") is False
        assert getattr(loaded, f"weight_{key}") == 28.0 / len(DOMINANCE_COMPONENT_KEYS)


def test_granular_dominance_values_override_legacy_combined_values() -> None:
    settings = MemorySettings(
        {
            "use_combined_dominance": False,
            "weight_combined_dominance": 28.0,
            "use_dominant_bodies": True,
            "weight_dominant_bodies": 17.0,
        }
    )

    loaded = load_similarity_calculator_settings(settings)

    assert loaded.use_dominant_bodies is True
    assert loaded.weight_dominant_bodies == 17.0


def test_non_mapping_settings_payload_uses_defaults() -> None:
    loaded = load_similarity_calculator_settings(MemorySettings("invalid"))

    assert asdict(loaded) == asdict(similarity_calculator_settings_defaults())
