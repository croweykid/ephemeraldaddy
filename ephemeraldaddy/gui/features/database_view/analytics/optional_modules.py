"""Optional-module availability policy for Database Analytics sections."""

from __future__ import annotations

from collections.abc import Callable


VisibilityLookup = Callable[[str], bool]


def database_analytics_section_is_visible(
    section_key: str,
    *,
    configured_visible: bool,
    visibility: VisibilityLookup,
) -> bool:
    """Return effective visibility after applying appwide module switches."""
    if not configured_visible:
        return False
    if section_key == "enneagram":
        return visibility("predictions.enneagram")
    if section_key == "species_distribution":
        return visibility("database_metrics_visibility.species_distribution")
    return True
