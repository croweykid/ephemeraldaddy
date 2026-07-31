"""Stable layout ownership for Chart Editor's embedded metric graphs."""

from __future__ import annotations

from collections.abc import Callable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import QScrollArea, QSizePolicy


class MetricCanvasLayoutController(QObject):
    """Make the visible scroll viewport the sole authority for graph width.

    Matplotlib canvases derive a large size hint from figure inches.  Older code
    tried to reconcile that hint with hidden stacked-page geometry by sampling
    ancestors repeatedly at several arbitrary delays.  A stale hidden width
    could therefore become the canvas's fixed width and survive until a user
    resized the window.  Never reintroduce ancestor-width sampling or timer
    chains here: Qt's *visible viewport resize event* is the authoritative
    notification that usable graph width has changed.
    """

    def __init__(
        self,
        *,
        side_gutter_px: int,
        redraw: Callable[[FigureCanvas], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._side_gutter_px = max(0, int(side_gutter_px))
        self._redraw = redraw or (lambda canvas: canvas.draw_idle())
        self._scroll_by_canvas: dict[FigureCanvas, QScrollArea] = {}
        self._canvases_by_scroll: dict[QScrollArea, set[FigureCanvas]] = {}
        self._dirty_canvases: set[FigureCanvas] = set()
        self._pending_canvases: set[FigureCanvas] = set()
        self._flush_scheduled = False

    def register(self, canvas: FigureCanvas, scroll_area: QScrollArea | None) -> None:
        """Track *canvas* and its explicit owning scroll area."""
        if scroll_area is None:
            # Canvas construction precedes layout insertion in Chart Editor.
            # Keep an already valid association if a transient re-check occurs
            # while Qt is reparenting; replacing it with None could orphan the
            # canvas until an unrelated resize happens.
            if canvas in self._scroll_by_canvas:
                return
            self._dirty_canvases.add(canvas)
            return
        if self._scroll_by_canvas.get(canvas) is scroll_area:
            self.request(canvas)
            return
        self.unregister(canvas)
        self._scroll_by_canvas[canvas] = scroll_area
        self._canvases_by_scroll.setdefault(scroll_area, set()).add(canvas)
        scroll_area.installEventFilter(self)
        scroll_area.viewport().installEventFilter(self)
        self.request(canvas)

    def unregister(self, canvas: FigureCanvas) -> None:
        scroll_area = self._scroll_by_canvas.pop(canvas, None)
        if scroll_area is not None:
            canvases = self._canvases_by_scroll.get(scroll_area)
            if canvases is not None:
                canvases.discard(canvas)
                if not canvases:
                    self._canvases_by_scroll.pop(scroll_area, None)
        self._dirty_canvases.discard(canvas)
        self._pending_canvases.discard(canvas)

    def request(self, canvas: FigureCanvas) -> None:
        """Coalesce one graph update into the next Qt event-loop turn."""
        if not self._is_authoritative_geometry_visible(canvas):
            self._dirty_canvases.add(canvas)
            return
        self._pending_canvases.add(canvas)
        if self._flush_scheduled:
            return
        self._flush_scheduled = True
        QTimer.singleShot(0, self._flush)

    def request_visible(self) -> None:
        """Update visible graphs; hidden graphs remain dirty until revealed."""
        for canvas in tuple(self._scroll_by_canvas):
            self.request(canvas)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API
        # Listen only to the owning scroll area and viewport. Canvas resize
        # events are effects of apply_now(), never fresh layout evidence.
        if event.type() in (QEvent.Resize, QEvent.Show):
            for scroll_area, canvases in tuple(self._canvases_by_scroll.items()):
                if watched is scroll_area or watched is scroll_area.viewport():
                    for canvas in tuple(canvases):
                        self.request(canvas)
                    break
        return False

    def apply_now(self, canvas: FigureCanvas) -> bool:
        """Apply authoritative visible geometry, returning whether it was usable."""
        scroll_area = self._scroll_by_canvas.get(canvas)
        if scroll_area is None or not self._is_authoritative_geometry_visible(canvas):
            self._dirty_canvases.add(canvas)
            return False
        viewport_width = scroll_area.viewport().width()
        if viewport_width <= 0:
            self._dirty_canvases.add(canvas)
            return False

        available_width = viewport_width
        parent = canvas.parentWidget()
        parent_layout = parent.layout() if parent is not None else None
        if parent_layout is not None:
            margins = parent_layout.contentsMargins()
            available_width -= margins.left() + margins.right()
        available_width = max(1, available_width - (self._side_gutter_px * 2))

        display_height = canvas.property("metric_display_height")
        if not isinstance(display_height, int) or display_height <= 0:
            _figure_width, figure_height = canvas.figure.get_size_inches()
            display_height = max(1, int(round(figure_height * canvas.figure.get_dpi())))

        # The viewport is the only width authority.  Do not consult canvas size
        # hints or hidden ancestors: both caused the historical distortion race.
        canvas.setFixedHeight(display_height)
        canvas.setMinimumWidth(available_width)
        canvas.setMaximumWidth(available_width)
        canvas.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if canvas.size().width() != available_width or canvas.size().height() != display_height:
            canvas.resize(available_width, display_height)
        canvas.updateGeometry()
        self._dirty_canvases.discard(canvas)
        self._redraw(canvas)
        return True

    def _flush(self) -> None:
        self._flush_scheduled = False
        pending, self._pending_canvases = self._pending_canvases, set()
        for canvas in pending:
            try:
                self.apply_now(canvas)
            except RuntimeError:
                self.unregister(canvas)

    def _is_authoritative_geometry_visible(self, canvas: FigureCanvas) -> bool:
        scroll_area = self._scroll_by_canvas.get(canvas)
        if scroll_area is None:
            return False
        try:
            return scroll_area.isVisible() and canvas.isVisibleTo(scroll_area)
        except RuntimeError:
            self.unregister(canvas)
            return False
