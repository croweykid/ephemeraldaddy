"""Cultural Contribution controls for the Database View Batch Editor."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from PySide6.QtWidgets import QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from ephemeraldaddy.core.chart_data_fields import NonastralPatch


@dataclass(frozen=True)
class CulturalContributionBatchCallbacks:
    selected_chart_uids: Callable[[], list[str]]
    chart_for_uid: Callable[[str], Any | None]
    apply_patch: Callable[[Iterable[str], NonastralPatch], set[int]]
    confirm: Callable[[str, int], bool]
    refresh_selection: Callable[[], None]
    refresh_filters: Callable[[set[int]], None]


class CulturalContributionBatchEditor:
    """Own cultural-contribution batch state without depending on a window."""

    def __init__(
        self,
        callbacks: CulturalContributionBatchCallbacks,
        *,
        parent: QWidget,
        slider_factory: Callable[[], QWidget],
        layout: QVBoxLayout,
    ) -> None:
        self._callbacks = callbacks
        self._parent = parent
        self.slider = slider_factory()
        self.score_label = QLabel()
        self.apply_button = QPushButton("Apply cultural contribution")
        self.slider.valueChanged.connect(self._update_score_label)
        self.apply_button.clicked.connect(self.apply)
        layout.addWidget(QLabel("actively detrimental   ⟷   exceptionally useful"))
        layout.addWidget(self.slider)
        layout.addWidget(self.score_label)
        layout.addWidget(self.apply_button)
        self.clear()

    def refresh(self) -> None:
        values = [
            self._normalized_value(getattr(chart, "cultural_contribution_score", None))
            for uid in self._callbacks.selected_chart_uids()
            if (chart := self._callbacks.chart_for_uid(uid)) is not None
        ]
        value = values[0] if values else 0
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self._update_score_label(value)
        self.slider.setToolTip(
            "Selected charts have mixed cultural contribution scores. "
            "Applying will overwrite all selected charts."
            if len(set(values)) > 1
            else ""
        )

    def clear(self) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(0)
        self.slider.blockSignals(False)
        self.slider.setToolTip("")
        self._update_score_label(0)

    def apply(self) -> None:
        chart_uids = self._callbacks.selected_chart_uids()
        if not chart_uids:
            QMessageBox.information(
                self._parent,
                "No charts selected",
                "Psst...Select one or more charts before applying batch edits.",
            )
            self._callbacks.refresh_selection()
            return
        value = int(self.slider.value())
        if not self._callbacks.confirm(
            f"Set cultural contribution score to {value} for", len(chart_uids)
        ):
            self._callbacks.refresh_selection()
            return
        try:
            changed_ids = self._callbacks.apply_patch(
                chart_uids, {"cultural_contribution_score": value}
            )
        except Exception as exc:
            QMessageBox.critical(
                self._parent,
                "Batch edit error",
                f"*sepukkus* Couldn't update the selected charts:\n{exc}",
            )
            return
        self._callbacks.refresh_selection()
        self._callbacks.refresh_filters(changed_ids)

    def _update_score_label(self, value: int) -> None:
        self.score_label.setText(f"Cultural contribution score: {int(value)}")

    @staticmethod
    def _normalized_value(value: Any) -> int:
        try:
            return max(-10, min(10, int(value))) if value is not None else 0
        except (TypeError, ValueError):
            return 0
