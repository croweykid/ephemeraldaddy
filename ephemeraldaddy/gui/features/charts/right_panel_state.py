"""State model for Chart View's right-hand panel."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChartRightPanelState:
    """Tracks UI + render state for Chart View's right-side panel."""

    active_tab: str = "subjective_notes"
    expanded_sections: dict[str, bool] = field(default_factory=dict)
    dirty_render_sections: set[str] = field(default_factory=set)
    last_render_chart_token: str | None = None

