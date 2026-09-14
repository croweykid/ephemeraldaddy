"""Chart Editor policy for coordinate-sensitive and shared person panels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence, Any


class AstrologyChartContext(Protocol):
    chart_uid: str
    zodiac: str
    division: str
    positions: Mapping[str, float]
    retrogrades: Mapping[str, bool]
    house_cusps: Sequence[float] | None
    aspects: Sequence[Mapping[str, Any]]


SHARED_PERSON_PANELS = frozenset(
    {"subjective_notes", "abc", "material_facts", "photo_gallery"}
)
COORDINATE_AWARE_PANELS = frozenset({"analytics", "time_sensitivity"})


@dataclass(frozen=True)
class ChartEditorModePolicy:
    """Available panels and editability for a concrete astrology context."""

    chart_uid: str
    zodiac: str
    division: str = "D1"

    def __post_init__(self) -> None:
        zodiac = self.zodiac.strip().lower()
        division = self.division.strip().upper()
        if zodiac not in {"tropical", "sidereal"}:
            raise ValueError(f"Unsupported zodiac {self.zodiac!r}")
        if zodiac == "tropical" and division != "D1":
            raise ValueError("Divisional projections require Sidereal coordinates")
        object.__setattr__(self, "zodiac", zodiac)
        object.__setattr__(self, "division", division)

    @property
    def predictions_available(self) -> bool:
        return self.zodiac == "tropical" and self.division == "D1"

    @property
    def derived_coordinates_editable(self) -> bool:
        return self.zodiac == "tropical" and self.division == "D1"

    @property
    def available_panels(self) -> frozenset[str]:
        panels = SHARED_PERSON_PANELS | COORDINATE_AWARE_PANELS
        if self.predictions_available:
            panels |= {"predictions"}
        return frozenset(panels)

    def resolve_panel(self, requested: str) -> str:
        normalized = requested.strip().lower()
        return normalized if normalized in self.available_panels else "analytics"
