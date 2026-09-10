"""State model for Chart View's right-hand panel."""

from __future__ import annotations

from dataclasses import dataclass, field


SECTION_EXPANSION_SETTINGS_PREFIX = "chart_editor/right_panel_sections"


def saved_section_expanded(owner: object, panel: str, section: str) -> bool:
    """Return a persisted expansion choice, defaulting new sections to collapsed."""
    settings = getattr(owner, "_settings", None)
    if settings is None:
        return False
    key = f"{SECTION_EXPANSION_SETTINGS_PREFIX}/{panel}/{section}"
    if not settings.contains(key):
        return False
    value = settings.value(key, False)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def save_section_expanded(owner: object, panel: str, section: str, expanded: bool) -> None:
    """Persist a user-driven expansion choice for a Chart Editor section."""
    settings = getattr(owner, "_settings", None)
    if settings is not None:
        settings.setValue(
            f"{SECTION_EXPANSION_SETTINGS_PREFIX}/{panel}/{section}",
            bool(expanded),
        )


@dataclass
class ChartRightPanelState:
    """Tracks UI + render state for Chart View's right-side panel."""

    active_tab: str = "subjective_notes"
    expanded_sections: dict[str, bool] = field(default_factory=dict)
    lucy_goosey_render_sections: set[str] = field(default_factory=set)
    last_render_chart_token: str | None = None
