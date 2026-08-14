"""Application-wide keyboard focus policies for input widgets."""

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QApplication, QLineEdit


class _FocusedInputEnterFilter(QObject):
    """Keep Enter shortcuts from pre-empting the focused single-line input.

    Qt resolves ``QShortcut`` objects before delivering a key press to the
    focused widget.  Consequently, an Enter shortcut owned by another panel
    can otherwise run instead of a ``QLineEdit``'s ``returnPressed`` handler.
    Accepting the shortcut-override event reserves Enter for the focused line
    edit; Qt then delivers the normal key press and the field emits its native
    submission signal.

    Multiline editors are intentionally excluded so Enter can keep inserting a
    newline.  A feature can still give one of those editors an explicit submit
    shortcut when appropriate.
    """

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API
        if (
            event.type() == QEvent.ShortcutOverride
            and isinstance(watched, QLineEdit)
            and watched.hasFocus()
            and event.key() in (Qt.Key_Return, Qt.Key_Enter)
        ):
            event.accept()
            return True
        return super().eventFilter(watched, event)


def install_appwide_input_focus_policy(app: QApplication) -> None:
    """Ensure Enter belongs to the focused single-line input appwide."""
    if getattr(app, "_edd_input_focus_policy_installed", False):
        return
    focus_filter = _FocusedInputEnterFilter(app)
    app.installEventFilter(focus_filter)
    app._edd_input_focus_filter = focus_filter  # type: ignore[attr-defined]
    app._edd_input_focus_policy_installed = True  # type: ignore[attr-defined]
