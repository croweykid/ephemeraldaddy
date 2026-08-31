"""Reusable perceived-accuracy controls for Chart Editor presentations.

The widget owns only its target and persistence interaction.  Chart identity is
supplied explicitly so the control never needs a top-level window as a service
locator.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from weakref import WeakSet

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QToolButton, QWidget

from ephemeraldaddy.core.perceived_accuracy import (
    PERCEIVED_ACCURACY_VERSION,
    PerceivedAccuracyScope,
    get_perceived_accuracy_value,
    toggle_perceived_accuracy,
)


@dataclass(frozen=True)
class PerceivedAccuracyTarget:
    scope: PerceivedAccuracyScope
    key: str
    version: int = PERCEIVED_ACCURACY_VERSION


_CONTROLS: WeakSet["PerceivedAccuracyThumbs"] = WeakSet()


class PerceivedAccuracyThumbs(QWidget):
    """Two-button, three-state rating control that can be safely retargeted."""

    def __init__(
        self,
        chart_uid: Callable[[], str | None],
        *,
        target: PerceivedAccuracyTarget | None = None,
        db_path: str | Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._chart_uid = chart_uid
        self._target = target
        self._db_path = db_path
        self._state: bool | None = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.positive_button = self._button("👍", True)
        self.negative_button = self._button("👎", False)
        layout.addWidget(self.positive_button)
        layout.addWidget(self.negative_button)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        _CONTROLS.add(self)
        self.refresh()

    def _button(self, text: str, value: bool) -> QToolButton:
        button = QToolButton(self)
        button.setText(text)
        button.setCheckable(True)
        button.setAutoRaise(True)
        button.setFocusPolicy(Qt.TabFocus)
        button.setToolTip("Accurate" if value else "Inaccurate")
        button.clicked.connect(lambda _checked=False, selected=value: self._toggle(selected))
        return button

    @property
    def target(self) -> PerceivedAccuracyTarget | None:
        return self._target

    @property
    def state(self) -> bool | None:
        return self._state

    def retarget(self, target: PerceivedAccuracyTarget | None) -> None:
        self._target = target
        self.refresh()

    def refresh(self) -> None:
        uid = self._chart_uid()
        if not uid or self._target is None:
            self.setEnabled(False)
            self._render(None)
            return
        self.setEnabled(True)
        self._render(
            get_perceived_accuracy_value(
                uid, self._target.scope, self._target.key, db_path=self._db_path
            )
        )

    def _toggle(self, value: bool) -> None:
        uid = self._chart_uid()
        if not uid or self._target is None:
            self._render(None)
            return
        self._render(
            toggle_perceived_accuracy(
                uid,
                self._target.scope,
                self._target.key,
                value,
                version=self._target.version,
                db_path=self._db_path,
            )
        )

    def _render(self, state: bool | None) -> None:
        self._state = state
        self.positive_button.setChecked(state is True)
        self.negative_button.setChecked(state is False)
        self.positive_button.setProperty("perceivedAccuracySelected", state is True)
        self.negative_button.setProperty("perceivedAccuracySelected", state is False)
        for button in (self.positive_button, self.negative_button):
            button.style().unpolish(button)
            button.style().polish(button)


def set_perceived_accuracy_controls_visible(visible: bool) -> None:
    """Apply the Display Preferences value live to every existing control."""
    for control in tuple(_CONTROLS):
        control.setVisible(bool(visible))
        if visible:
            control.refresh()


def install_chart_editor_module_controls(
    owner: QWidget,
    *,
    chart_uid: Callable[[], str | None],
    visible: bool,
) -> dict[str, PerceivedAccuracyThumbs]:
    """Add controls to current Chart Editor collapsibles using stable attribute keys."""
    installed: dict[str, PerceivedAccuracyThumbs] = {}
    for attribute, candidate in tuple(vars(owner).items()):
        if not isinstance(candidate, QToolButton):
            continue
        if not candidate.property("collapsibleHeaderLevel") or candidate.layout() is None:
            continue
        key = f"chart_editor:{attribute}"
        control = PerceivedAccuracyThumbs(
            chart_uid,
            target=PerceivedAccuracyTarget("modules", key),
            parent=candidate,
        )
        candidate.layout().addWidget(control, 0, Qt.AlignRight | Qt.AlignVCenter)
        control.setVisible(visible)
        installed[key] = control
    return installed
