"""Cultural Contribution controls for the Chart Editor Observations panel."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ephemeraldaddy.gui.style import COLLAPSIBLE_SECTION_SUBHEADER_STYLE


class CulturalContributionController:
    """Own the widgets and draft state for the cultural-contribution metric."""

    def __init__(
        self,
        *,
        slider_factory: Callable[[], QWidget],
        on_user_change: Callable[[int], None],
    ) -> None:
        self.slider = slider_factory()
        self.score_label = QLabel()
        self.subheader = QLabel()
        self.subheader.setWordWrap(True)
        self.subheader.setStyleSheet(COLLAPSIBLE_SECTION_SUBHEADER_STYLE)
        self._assigned = False
        self._programmatic_update = False
        self._on_user_change = on_user_change
        self.slider.valueChanged.connect(self._on_value_changed)
        self.slider.userActivated.connect(self._on_user_activated)
        self._update_score_label()

    @property
    def assigned(self) -> bool:
        return self._assigned

    @property
    def value(self) -> int:
        return int(self.slider.value())

    def populate_section(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self.subheader)
        layout.addWidget(QLabel("actively detrimental   ⟷   exceptionally useful"))
        layout.addWidget(self.slider)
        layout.addWidget(self.score_label)

    def update_caption(self, chart_name: str) -> None:
        person_name = (chart_name or "this chart").strip()
        self.subheader.setText(
            "Regardless of morality or caveats, how much do you think "
            f"{person_name} has usefully contributed to society & human progress, at large? "
            "Is/was this a 'useful' entity, in your opinion?"
        )

    def load(self, chart: Any) -> None:
        value = getattr(chart, "cultural_contribution_score", None)
        self.set_state(int(value or 0), assigned=isinstance(value, int))

    def clear(self) -> None:
        self.set_state(0, assigned=False)

    def apply_to_chart(self, chart: Any, *, is_event_chart: bool) -> None:
        chart.cultural_contribution_score = (
            0 if is_event_chart else self.value if self._assigned else None
        )

    def set_state(self, value: int, *, assigned: bool) -> None:
        self._programmatic_update = True
        self._assigned = bool(assigned)
        self.slider.setValue(max(-10, min(10, int(value))))
        self._programmatic_update = False
        self._update_score_label()

    def _on_value_changed(self, value: int) -> None:
        if not self._programmatic_update:
            self._assigned = True
        self._update_score_label()
        self._on_user_change(int(value))

    def _on_user_activated(self, value: int) -> None:
        if self._programmatic_update or self._assigned:
            return
        self._assigned = True
        self._update_score_label()
        self._on_user_change(int(value))

    def _update_score_label(self) -> None:
        if self._assigned:
            self.score_label.setText(f"Cultural contribution score: {self.value}")
        else:
            self.score_label.setText("Cultural contribution score: blank")
