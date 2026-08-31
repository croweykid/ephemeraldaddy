"""Reusable perceived-accuracy controls for Chart Editor presentations.

The widget owns only its target and persistence interaction.  Chart identity is
supplied explicitly so the control never needs a top-level window as a service
locator.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from weakref import WeakSet

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QToolButton, QWidget

from ephemeraldaddy.core.perceived_accuracy import (
    PERCEIVED_ACCURACY_VERSION,
    PerceivedAccuracyScope,
    get_perceived_accuracy_value,
    load_perceived_accuracy,
    toggle_perceived_accuracy,
)


@dataclass(frozen=True)
class PerceivedAccuracyTarget:
    scope: PerceivedAccuracyScope
    key: str
    version: int = PERCEIVED_ACCURACY_VERSION


def property_target_from_entry(
    entry: Mapping[str, object],
) -> PerceivedAccuracyTarget | None:
    """Build a stable target only from semantic presenter fields, never prose."""
    kind = str(entry.get("kind", "") or "").strip().lower()
    identity_fields = (
        "property_key", "property_value", "body", "sign", "house",
        "nakshatra", "gate", "line", "gate_a", "gate_b", "color",
        "tone", "base", "class_key", "family", "subtype",
        "p1", "p2", "type",
    )
    identity = [
        f"{field}={str(entry[field]).strip().lower()}"
        for field in identity_fields
        if entry.get(field) not in (None, "")
    ]
    if not kind or not identity:
        return None
    return PerceivedAccuracyTarget("properties", ":".join([kind, *identity]))


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

    def refresh_from_payload(self, payload: Mapping[str, object]) -> None:
        """Render this target from an already-loaded chart payload."""
        if self._target is None:
            self.setEnabled(False)
            self._render(None)
            return
        root = payload.get("perceived_accuracy", {})
        scopes = root if isinstance(root, Mapping) else {}
        ratings = scopes.get(self._target.scope, {})
        record = ratings.get(self._target.key) if isinstance(ratings, Mapping) else None
        value = record.get("value") if isinstance(record, Mapping) else None
        self.setEnabled(True)
        self._render(value if isinstance(value, bool) else None)

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


def refresh_perceived_accuracy_controls(owner: object, *, clear_property: bool = False) -> None:
    """Refresh controls after Chart Editor identity changes."""
    controls = tuple(
        getattr(owner, "_perceived_accuracy_module_controls", {}).values()
    )
    chart_uid = getattr(owner, "current_chart_uid", None)
    payload = load_perceived_accuracy(chart_uid) if chart_uid else None
    for control in controls:
        control.refresh_from_payload(payload) if payload is not None else control.refresh()
    property_control = getattr(owner, "chart_information_accuracy_control", None)
    if property_control is not None:
        property_control.retarget(None) if clear_property else property_control.refresh()


def install_chart_editor_module_controls(
    owner: QWidget,
    *,
    chart_uid: Callable[[], str | None],
    visible: bool,
) -> dict[str, PerceivedAccuracyThumbs]:
    """Add controls to semantically identified descendant collapsible headers."""
    installed: dict[str, PerceivedAccuracyThumbs] = {}
    for candidate in owner.findChildren(QToolButton):
        semantic_key = str(candidate.property("collapsibleSemanticKey") or "").strip()
        if not semantic_key or candidate.layout() is None:
            continue
        key = f"chart_editor:{semantic_key}"
        if key in installed:
            raise ValueError(f"Duplicate Chart Editor module key: {semantic_key}")
        control = PerceivedAccuracyThumbs(
            chart_uid,
            target=PerceivedAccuracyTarget("modules", key),
            parent=candidate,
        )
        candidate.layout().addWidget(control, 0, Qt.AlignRight | Qt.AlignVCenter)
        control.setVisible(visible)
        installed[key] = control
    return installed
