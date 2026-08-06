"""User feedback for the synchronous Database View shutdown workflow."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QWidget

from ephemeraldaddy.gui.style import (
    create_app_loading_progress,
    update_app_loading_progress,
)


class DatabaseCloseProgress:
    """Display named shutdown stages while Database View prepares to close.

    Closing currently performs several small, synchronous persistence tasks on
    the GUI thread.  Keeping this presentation object outside the window makes
    those tasks visible without making the window own another widget workflow.
    """

    def __init__(
        self,
        parent: QWidget,
        *,
        create_progress: Callable[..., object] = create_app_loading_progress,
        update_progress: Callable[[object, str, int], None] = update_app_loading_progress,
    ) -> None:
        self._update_progress = update_progress
        self._progress = create_progress(
            parent=parent,
            title="Closing Ephemeral Daddy",
            message="Preparing to close safely…",
            minimum=0,
            maximum=100,
        )

    def update(self, message: str, percent: int) -> None:
        """Show a shutdown stage and allow its paint events to be processed."""
        self._update_progress(self._progress, message, percent)

