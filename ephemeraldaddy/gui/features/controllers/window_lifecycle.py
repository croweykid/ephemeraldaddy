"""Window lifecycle helpers that keep startup choreography out of app.py."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QWidget

from ephemeraldaddy.gui.startup import StartupProgress


def configure_initial_window_state(
    *,
    app: QApplication,
    window: QWidget,
    startup_loading: StartupProgress,
    get_icon_path: Callable[[], str | None],
    show_default_view: Callable[[], None],
) -> None:
    """Apply icon/default-view startup behavior in one focused place."""
    startup_loading.update_status("Applying startup settings…", 75)

    icon_path = get_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
        window.setWindowIcon(QIcon(icon_path))

    # Always launch into Database View. Persisted "last_view" state previously
    # allowed cold-start entry into Chart View, which can present a blank chart
    # canvas while heavy initialization catches up (more pronounced on Windows).
    # Keeping launch deterministic avoids that startup race without changing
    # intended user-facing behavior (Database View first, Chart View on demand).
    show_default_view()
    window.hide()
    startup_loading.update_status("Startup complete.", 100)
    QTimer.singleShot(250, startup_loading.close)
