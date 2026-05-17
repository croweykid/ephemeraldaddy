"""Helpers for Database View Similarities Analysis calculations and progress UI."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from PySide6.QtCore import QEventLoop, Qt
from PySide6.QtWidgets import QApplication, QProgressDialog, QWidget


class SimilaritiesBaselineProvider(Protocol):
    """Minimal app-facing interface needed to build similarities baselines."""

    def _build_common_position_signs(self, chart_ids: list[int]) -> list[tuple[str, int, int]]: ...

    def _build_common_houses_in_positions(self, chart_ids: list[int]) -> list[tuple[str, int, int]]: ...

    def _build_common_signs_in_houses(self, chart_ids: list[int]) -> list[tuple[str, int, int]]: ...

    def _build_common_aspects(self, chart_ids: list[int]) -> list[tuple[str, int, int]]: ...

    def _build_common_dominant_signs(self, chart_ids: list[int]) -> list[tuple[str, int, int]]: ...

    def _build_common_dominant_bodies(self, chart_ids: list[int]) -> list[tuple[str, int, int]]: ...

    def _build_common_dominant_houses(self, chart_ids: list[int]) -> list[tuple[str, int, int]]: ...

    def _build_common_dominant_nakshatras(self, chart_ids: list[int]) -> list[tuple[str, int, int]]: ...

    def _build_common_human_design_gates(self, chart_ids: list[int]) -> list[tuple[str, int, int]]: ...

    def _build_common_human_design_channels(self, chart_ids: list[int]) -> list[tuple[str, int, int]]: ...

    def _build_common_human_design_defined_centers(self, chart_ids: list[int]) -> list[tuple[str, int, int]]: ...

    def _build_common_human_design_authorities(self, chart_ids: list[int]) -> list[tuple[str, int, int]]: ...

    def _build_common_human_design_profiles(self, chart_ids: list[int]) -> list[tuple[str, int, int]]: ...


class SimilaritiesDbBaselineCache:
    """Memoize database-wide similarities baselines between selection refreshes."""

    def __init__(self) -> None:
        self._cache_key: tuple[int, ...] | None = None
        self._cache: dict[str, Any] | None = None

    def clear(self) -> None:
        self._cache_key = None
        self._cache = None

    def get(
        self,
        db_chart_ids: list[int],
        builder: Callable[[list[int]], dict[str, Any]],
    ) -> dict[str, Any]:
        cache_key = tuple(int(chart_id) for chart_id in db_chart_ids)
        if self._cache_key == cache_key and self._cache is not None:
            return self._cache
        baselines = builder(db_chart_ids)
        self._cache_key = cache_key
        self._cache = baselines
        return baselines


def _match_counts(matches: list[tuple[str, int, int]]) -> dict[str, int]:
    return {label: count for label, count, _total in matches}


def _match_totals(matches: list[tuple[str, int, int]]) -> dict[str, int]:
    return {label: total for label, _count, total in matches}


def build_similarity_db_baselines(
    provider: SimilaritiesBaselineProvider,
    db_chart_ids: list[int],
) -> dict[str, Any]:
    """Build database-wide counts used to compare Similarities Analysis results."""

    common_positions = provider._build_common_position_signs(db_chart_ids)
    common_houses_in_positions = provider._build_common_houses_in_positions(db_chart_ids)
    common_signs_in_houses = provider._build_common_signs_in_houses(db_chart_ids)
    common_aspects = provider._build_common_aspects(db_chart_ids)
    return {
        "common_positions": _match_counts(common_positions),
        "common_positions_totals": _match_totals(common_positions),
        "common_houses_in_positions": _match_counts(common_houses_in_positions),
        "common_houses_in_positions_totals": _match_totals(common_houses_in_positions),
        "common_signs_in_houses": _match_counts(common_signs_in_houses),
        "common_signs_in_houses_totals": _match_totals(common_signs_in_houses),
        "common_dominant_signs": _match_counts(provider._build_common_dominant_signs(db_chart_ids)),
        "common_dominant_bodies": _match_counts(provider._build_common_dominant_bodies(db_chart_ids)),
        "common_dominant_houses": _match_counts(provider._build_common_dominant_houses(db_chart_ids)),
        "common_dominant_nakshatras": _match_counts(
            provider._build_common_dominant_nakshatras(db_chart_ids)
        ),
        "common_aspects": _match_counts(common_aspects),
        "common_aspects_totals": _match_totals(common_aspects),
        "common_hd_gates": _match_counts(provider._build_common_human_design_gates(db_chart_ids)),
        "common_hd_channels": _match_counts(provider._build_common_human_design_channels(db_chart_ids)),
        "common_hd_defined_centers": _match_counts(
            provider._build_common_human_design_defined_centers(db_chart_ids)
        ),
        "common_hd_authorities": _match_counts(
            provider._build_common_human_design_authorities(db_chart_ids)
        ),
        "common_hd_profiles": _match_counts(provider._build_common_human_design_profiles(db_chart_ids)),
    }


def show_similarities_loading_progress(
    *,
    parent: QWidget | None,
    message: str = "Calculating similarities analysis…",
) -> QProgressDialog:
    progress = QProgressDialog(message, None, 0, 0, parent)
    progress.setWindowTitle("Similarities Analysis")
    progress.setWindowModality(Qt.WindowModal)
    progress.setCancelButton(None)
    progress.setMinimumDuration(0)
    progress.setAutoClose(False)
    progress.setAutoReset(False)
    progress.setValue(0)
    progress.show()
    QApplication.processEvents(QEventLoop.AllEvents, 50)
    return progress


def update_similarities_loading_progress(
    progress: QProgressDialog | None,
    message: str,
) -> None:
    if progress is None:
        return
    progress.setLabelText(message)
    progress.setValue(0)
    QApplication.processEvents(QEventLoop.AllEvents, 50)


def close_similarities_loading_progress(progress: QProgressDialog | None) -> None:
    if progress is None:
        return
    progress.close()
    QApplication.processEvents(QEventLoop.AllEvents, 50)
