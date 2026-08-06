"""Settings orchestration for OCEAN Predictor scoring."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox

from ephemeraldaddy.gui.features.predictions.ocean import set_ocean_predictor_weights
from ephemeraldaddy.gui.features.predictions.ocean_settings import (
    OCEAN_WEIGHT_ROWS,
    OceanPredictorWeights,
    load_ocean_predictor_weights,
    ocean_predictor_weights_from_payload,
    ocean_predictor_weights_to_payload,
    save_ocean_predictor_weights,
)


class SettingsAdapter(Protocol):
    """Narrow persistence boundary required by the OCEAN settings controller."""

    def value(self, key: str, default: Any = None) -> Any: ...

    def setValue(self, key: str, value: Any) -> None: ...


def configure_ocean_predictor_from_settings(settings: SettingsAdapter) -> OceanPredictorWeights:
    """Load, normalize, persist, and activate OCEAN settings once at startup."""
    config = load_ocean_predictor_weights(settings)
    save_ocean_predictor_weights(settings, config)
    set_ocean_predictor_weights(config)
    return config


class OceanPredictorSettingsController:
    """Own OCEAN Settings widget state without coupling it to an app window."""

    def __init__(
        self,
        settings: SettingsAdapter,
        *,
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        self._settings = settings
        self._on_changed = on_changed
        self._config = configure_ocean_predictor_from_settings(settings)

    def enabled_toggled(self, category: str, enabled: bool) -> None:
        self._update(f"use_{category}_weights", bool(enabled))

    def weight_changed(self, category: str, weight: float) -> None:
        self._update(f"{category}_weight", float(weight))

    def bind_controls(
        self,
        checkboxes: Mapping[str, QCheckBox],
        weight_spinboxes: Mapping[str, QDoubleSpinBox],
    ) -> None:
        """Render persisted values without emitting change callbacks."""
        for key, _title, _default in OCEAN_WEIGHT_ROWS:
            checkbox = checkboxes.get(key)
            spinbox = weight_spinboxes.get(key)
            if checkbox is not None:
                blocker = QSignalBlocker(checkbox)
                checkbox.setChecked(bool(getattr(self._config, f"use_{key}_weights")))
                del blocker
            if spinbox is not None:
                blocker = QSignalBlocker(spinbox)
                spinbox.setValue(float(getattr(self._config, f"{key}_weight")))
                del blocker

    def _update(self, key: str, value: object) -> None:
        payload = ocean_predictor_weights_to_payload(self._config)
        payload[key] = value
        self._config = ocean_predictor_weights_from_payload(payload)
        save_ocean_predictor_weights(self._settings, self._config)
        set_ocean_predictor_weights(self._config)
        if self._on_changed is not None:
            self._on_changed()
