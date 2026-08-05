"""Shared Settings constants and conversion helpers."""

from __future__ import annotations

from typing import Any

SETTINGS_KEY_DATABASE_VIEW_ROW_INFO = "manage_charts/database_view_row_info"
SETTINGS_KEY_PREDICTIONS_MANUAL_RECALCULATION_ONLY = "predictions/manual_recalculation_only"

DATABASE_VIEW_ROW_INFO_OPTIONS: tuple[tuple[str, str], ...] = (
    ("name", "Name"),
    ("alias", "Alias"),
    ("from_whence", "From"),
    ("birth_date", "Birth date"),
    ("birth_time", "Birth time"),
    ("birth_place", "Birth place"),
    ("current_age", "Current age"),
    ("sign_glyphs", "Sun/Moon/Rising sign glyphs"),
    ("human_design_profile", "HD profile"),
    ("gender", "Gender glyph"),
)

DATABASE_VIEW_ROW_INFO_DEFAULTS: dict[str, bool] = {
    key: True for key, _label in DATABASE_VIEW_ROW_INFO_OPTIONS
}


def settings_bool(value: object, fallback: bool) -> bool:
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
    return bool(fallback)


def load_database_view_row_info_visibility(settings: Any) -> dict[str, bool]:
    payload = settings.value(SETTINGS_KEY_DATABASE_VIEW_ROW_INFO, {})
    if not isinstance(payload, dict):
        payload = {}
    return {
        key: settings_bool(payload.get(key, default), default)
        for key, default in DATABASE_VIEW_ROW_INFO_DEFAULTS.items()
    }


def save_database_view_row_info_visibility(settings: Any, visibility: dict[str, bool]) -> None:
    settings.setValue(
        SETTINGS_KEY_DATABASE_VIEW_ROW_INFO,
        {
            key: bool(visibility.get(key, default))
            for key, default in DATABASE_VIEW_ROW_INFO_DEFAULTS.items()
        },
    )


def load_predictions_manual_recalculation_only(settings: Any, *, fallback: bool = True) -> bool:
    value = settings.value(SETTINGS_KEY_PREDICTIONS_MANUAL_RECALCULATION_ONLY, int(fallback))
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "checked"}
    return bool(value)
