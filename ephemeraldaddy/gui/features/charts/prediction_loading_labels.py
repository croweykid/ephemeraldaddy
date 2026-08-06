"""Shared loading-label animation helpers for Chart View Predictions."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QTimer


_LOADING_TIMER_ATTR = "_ephemeraldaddy_loading_blink_timer"
_LOADING_STATE_ATTR = "_ephemeraldaddy_loading_blink_state"
_LOADING_STYLE_ATTR = "_ephemeraldaddy_loading_blink_previous_style"
_ELLIPSIS_TIMER_ATTR = "_ephemeraldaddy_loading_ellipsis_timer"


def stop_prediction_loading_blink(label: Any) -> None:
    """Stop a Predictions loading blink timer and restore the label's pre-loading style."""
    timer = getattr(label, _LOADING_TIMER_ATTR, None)
    if isinstance(timer, QTimer):
        try:
            timer.stop()
            timer.deleteLater()
        except RuntimeError:
            pass
    previous_style = getattr(label, _LOADING_STYLE_ATTR, None)
    if previous_style is not None and hasattr(label, "setStyleSheet"):
        try:
            label.setStyleSheet(str(previous_style))
        except RuntimeError:
            pass
    for attr in (_LOADING_TIMER_ATTR, _LOADING_STATE_ATTR, _LOADING_STYLE_ATTR):
        try:
            delattr(label, attr)
        except (AttributeError, RuntimeError):
            pass


def start_prediction_loading_blink(label: Any) -> None:
    """Pulse a Predictions loading label purple until its text no longer says it is loading."""
    stop_prediction_loading_blink(label)
    try:
        label._ephemeraldaddy_loading_blink_previous_style = label.styleSheet()
    except RuntimeError:
        label._ephemeraldaddy_loading_blink_previous_style = ""
    label._ephemeraldaddy_loading_blink_state = 0

    def _tick() -> None:
        try:
            label_text = str(label.text())
        except RuntimeError:
            stop_prediction_loading_blink(label)
            return
        if "Loading" not in label_text:
            stop_prediction_loading_blink(label)
            return
        state = int(getattr(label, _LOADING_STATE_ATTR, 0) or 0)
        color = ("#c77dff", "#7b4dff")[state % 2]
        try:
            label.setStyleSheet(f"color: {color}; font-style: italic; font-weight: 700; padding: 18px 8px;")
        except RuntimeError:
            stop_prediction_loading_blink(label)
            return
        label._ephemeraldaddy_loading_blink_state = state + 1

    timer = QTimer(label)
    timer.timeout.connect(_tick)
    label._ephemeraldaddy_loading_blink_timer = timer
    _tick()
    timer.start(450)


def start_prediction_loading_ellipsis(label: Any, message: str) -> None:
    """Animate a centered loading message with one through three periods."""
    previous_timer = getattr(label, _ELLIPSIS_TIMER_ATTR, None)
    if isinstance(previous_timer, QTimer):
        previous_timer.stop()
        previous_timer.deleteLater()

    label._ephemeraldaddy_loading_ellipsis_state = 0

    def _tick() -> None:
        try:
            current_text = str(label.text())
        except RuntimeError:
            timer.stop()
            return
        if current_text and not current_text.startswith(message):
            timer.stop()
            timer.deleteLater()
            return
        state = int(getattr(label, "_ephemeraldaddy_loading_ellipsis_state", 0))
        label.setText(f"{message}{'.' * ((state % 3) + 1)}")
        label._ephemeraldaddy_loading_ellipsis_state = state + 1

    timer = QTimer(label)
    timer.timeout.connect(_tick)
    label._ephemeraldaddy_loading_ellipsis_timer = timer
    _tick()
    timer.start(450)
