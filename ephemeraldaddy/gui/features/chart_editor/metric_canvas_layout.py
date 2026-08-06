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
        # Show is the one canvas event that is authoritative: a previously
        # collapsed graph has just become eligible to consume the current
        # viewport width. Never subscribe to canvas Resize here; that would
        # restore the resize -> redraw -> resize feedback loop.
        canvas.installEventFilter(self)
        scroll_area.installEventFilter(self)
        scroll_area.viewport().installEventFilter(self)
        self.request(canvas)

    def unregister(self, canvas: FigureCanvas) -> None:
        scroll_area = self._scroll_by_canvas.pop(canvas, None)
        try:
            canvas.removeEventFilter(self)
        except RuntimeError:
            pass
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
        # A canvas Show drains width dirtied while its section was collapsed.
        # Canvas Resize remains deliberately ignored because it is an effect of
        # apply_now(), not fresh layout evidence.
        if (
            event.type() == QEvent.Show
            and isinstance(watched, FigureCanvas)
            and watched in self._scroll_by_canvas
        ):
            self.request(watched)
            return False
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

        available_width = viewport_width - self._horizontal_insets_to_viewport(
            canvas, scroll_area
        )
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

    @staticmethod
    def _horizontal_insets_to_viewport(
        canvas: FigureCanvas, scroll_area: QScrollArea
    ) -> int:
        """Return every layout inset between a canvas and its scroll viewport.

        A graph is commonly nested inside a zero-margin chart panel, which is
        itself inside an eight-pixel collapsible-section content layout and a
        padded tab page.  Subtracting only the canvas parent's margins made the
        graph as wide as the *whole* viewport, so it necessarily crossed the
        section's hard edge.  Derive the width from the viewport while walking
        the explicit ancestor chain; do not sample ancestor widths or size
        hints, which can still be stale while a stacked page is hidden.
        """
        total = 0
        widget = canvas.parentWidget()
        scroll_content = scroll_area.widget()
        while widget is not None:
            layout = widget.layout()
            if layout is not None:
                margins = layout.contentsMargins()
                total += margins.left() + margins.right()
            if widget is scroll_content:
                break
            widget = widget.parentWidget()
        return total

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
