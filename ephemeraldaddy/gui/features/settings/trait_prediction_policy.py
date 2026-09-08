"""Settings controls for optional Trait Predictions provenance/gender policies."""

from __future__ import annotations

from types import ModuleType
from typing import Any

from PySide6.QtWidgets import QCheckBox, QLabel

from ephemeraldaddy.gui.settings.core import (
    SETTINGS_KEY_PREDICTIONS_EXCLUDE_ASCRIBED_TRAIT_CHARTS,
    SETTINGS_KEY_PREDICTIONS_USE_TRAIT_GENDER_DISTRIBUTION,
    load_predictions_exclude_ascribed_trait_charts,
    load_predictions_use_trait_gender_distribution,
)


def _owner_settings(owner: Any) -> Any | None:
    for attr_name in ("settings", "_settings"):
        settings = getattr(owner, attr_name, None)
        if settings is not None and callable(getattr(settings, "value", None)):
            return settings
    return None


def _policy_heading() -> QLabel:
    label = QLabel("Trait Prediction Policy")
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    return label


def _invalidate_trait_prediction_view(owner: Any) -> None:
    owner._traits_prediction_pending_metadata = None
    owner._traits_prediction_pending_metadata_cache_key = ""
    owner._traits_prediction_pending_cache_key = ""
    owner._traits_prediction_render_token = object()
    render_traits = getattr(owner, "_render_traits_predictions", None)
    if callable(render_traits):
        render_traits(getattr(owner, "_latest_chart", None))


def _set_policy(
    owner: Any,
    *,
    key: str,
    attr_name: str,
    checked: bool,
) -> None:
    enabled = bool(checked)
    settings = _owner_settings(owner)
    if settings is not None:
        settings.setValue(key, int(enabled))
    setattr(owner, attr_name, enabled)
    _invalidate_trait_prediction_view(owner)


def add_trait_prediction_policy_controls(owner: Any, traits_section: Any) -> None:
    """Add opt-in Predictions controls above the local Trait file manager."""
    settings = _owner_settings(owner)
    exclude_ascribed = (
        load_predictions_exclude_ascribed_trait_charts(settings, fallback=False)
        if settings is not None
        else bool(getattr(owner, "_predictions_exclude_ascribed_trait_charts", False))
    )
    use_gender = (
        load_predictions_use_trait_gender_distribution(settings, fallback=False)
        if settings is not None
        else bool(getattr(owner, "_predictions_use_trait_gender_distribution", False))
    )
    owner._predictions_exclude_ascribed_trait_charts = bool(exclude_ascribed)
    owner._predictions_use_trait_gender_distribution = bool(use_gender)

    traits_section.addWidget(_policy_heading())

    owner._traits_exclude_ascribed_predictions_checkbox = QCheckBox(
        "Exclude charts used to define a Trait from that Trait's Predictions"
    )
    owner._traits_exclude_ascribed_predictions_checkbox.setChecked(bool(exclude_ascribed))
    owner._traits_exclude_ascribed_predictions_checkbox.setToolTip(
        "Uses permanent chart UIDs exported in chartUIDs. This is Trait-specific: "
        "being ascribed one Trait does not exclude the chart from unrelated Traits."
    )
    owner._traits_exclude_ascribed_predictions_checkbox.toggled.connect(
        lambda checked: _set_policy(
            owner,
            key=SETTINGS_KEY_PREDICTIONS_EXCLUDE_ASCRIBED_TRAIT_CHARTS,
            attr_name="_predictions_exclude_ascribed_trait_charts",
            checked=checked,
        )
    )
    traits_section.addWidget(owner._traits_exclude_ascribed_predictions_checkbox)

    owner._traits_use_gender_distribution_checkbox = QCheckBox(
        "Use statistically significant gender distribution as a Trait prediction criterion"
    )
    owner._traits_use_gender_distribution_checkbox.setChecked(bool(use_gender))
    owner._traits_use_gender_distribution_checkbox.setToolTip(
        "When a Trait export contains a statistically significant genderDistribution, "
        "the chart's recorded gender contributes the sample-vs-database percentage-point "
        "difference as signed evidence. Missing gender is never inferred."
    )
    owner._traits_use_gender_distribution_checkbox.toggled.connect(
        lambda checked: _set_policy(
            owner,
            key=SETTINGS_KEY_PREDICTIONS_USE_TRAIT_GENDER_DISTRIBUTION,
            attr_name="_predictions_use_trait_gender_distribution",
            checked=checked,
        )
    )
    traits_section.addWidget(owner._traits_use_gender_distribution_checkbox)
    traits_section.addSpacing(8)


def install_trait_prediction_settings(core: ModuleType) -> None:
    """Extend the existing Traits manager without moving policy code into it."""
    if bool(getattr(core, "_ephemeraldaddy_trait_prediction_settings_installed", False)):
        return
    original_populate = core.populate_traits_settings_layout

    def populate_with_prediction_policy(owner: Any, traits_section: Any) -> None:
        add_trait_prediction_policy_controls(owner, traits_section)
        original_populate(owner, traits_section)

    core.populate_traits_settings_layout = populate_with_prediction_policy
    core._ephemeraldaddy_trait_prediction_settings_installed = True
