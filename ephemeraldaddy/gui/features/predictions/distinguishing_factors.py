"""Asynchronous Distinguishing Factors presentation with stale-result rejection."""
from __future__ import annotations
import copy
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtWidgets import QLabel
from ephemeraldaddy.analysis.distinguishing_factors import build_distinguishing_factors_html, calculate_weirdness_score_from_metric_payloads, DISTINGUISHING_FORMULA_VERSION
from ephemeraldaddy.analysis.trait_signatures import chart_prediction_signature
from ephemeraldaddy.core.prediction_norms import distinguishing_norm_reference
from ephemeraldaddy.core import db
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR

_log = logging.getLogger(__name__)
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='distinguishing-factors')


def _calculate(chart: Any, payloads: tuple[dict[str, Any], ...], norm_signature: str, debug: bool) -> tuple[str, float | None]:
    score, _ = calculate_weirdness_score_from_metric_payloads(chart, payloads)
    rendered = build_distinguishing_factors_html(chart, [], metric_payloads=payloads, debug_scoring=debug, highlight_color=CHART_DATA_HIGHLIGHT_COLOR)
    uid = str(getattr(chart, 'chart_uid', '') or '').upper()
    if uid and score is not None:
        # A draft or an astro edit during calculation must not replace saved data.
        saved = db.load_chart_by_uid(uid)
        if saved is not None and chart_prediction_signature(saved) == chart_prediction_signature(chart):
            db.update_chart_weirdness_score_by_uid(uid, score, formula_version=DISTINGUISHING_FORMULA_VERSION, norm_signature=norm_signature)
    return rendered, score


class DistinguishingFactorsPresenter(QObject):
    completed = Signal(object, object)

    def __init__(self, label: QLabel) -> None:
        super().__init__(label)
        self._label = label
        self._token: object = None
        self._future: Any = None
        self._cached: dict[tuple[Any, ...], tuple[str, float | None]] = {}
        self.completed.connect(self._apply, Qt.QueuedConnection)
        self.destroyed.connect(lambda *_: self._cancel())

    def _cancel(self) -> None:
        self._token = None
        if self._future:
            self._future.cancel()

    def render(self, chart: Any, *, debug: bool = False) -> None:
        if chart is None or getattr(chart, 'is_placeholder', False):
            self._cancel()
            self._label.setText('No chart loaded.' if chart is None else 'No data for placeholder/hypothetical charts.')
            return
        payloads, norm_signature = distinguishing_norm_reference()
        if not payloads:
            self._cancel()
            self._label.setText('Static DB norms for Distinguishing Factors are unavailable. Generate DB Norms in Developer Tools.')
            return
        token = (str(getattr(chart, 'chart_uid', '') or ''), chart_prediction_signature(chart), norm_signature, debug)
        if token in self._cached:
            self._token = token
            self._label.setText(self._cached[token][0])
            return
        if token == self._token and self._future is not None and not self._future.done():
            return
        self._cancel()
        self._token = token
        self._label.setText('Calculating distinguishing factors…')
        self._future = _pool.submit(_calculate, copy.deepcopy(chart), payloads, norm_signature, debug)
        def finished(future: Any) -> None:
            if future.cancelled():
                return
            try:
                result = future.result()
            except Exception:
                _log.exception('Distinguishing Factors calculation failed')
                result = ('Distinguishing Factors calculation failed. See the application log.', None)
            try:
                self.completed.emit(token, result)
            except RuntimeError:
                pass  # The label/window was closed while the worker ran.
        self._future.add_done_callback(finished)

    @Slot(object, object)
    def _apply(self, token: object, result: tuple[str, float | None]) -> None:
        if token != self._token:
            return
        if len(self._cached) >= 32:
            self._cached.pop(next(iter(self._cached)))
        self._cached[token] = result
        self._label.setText(result[0])
