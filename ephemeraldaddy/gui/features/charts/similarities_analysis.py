"""Helpers for Database View Similarities Analysis calculations and progress UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from PySide6.QtCore import QEventLoop, Qt
from PySide6.QtWidgets import QApplication, QListWidget, QProgressDialog, QWidget

from ephemeraldaddy.analysis.get_astro_twin import (
    SIMILAR_CHARTS_ALGORITHM_COMPREHENSIVE,
    SIMILAR_CHARTS_ALGORITHM_CUSTOM,
    SimilarityCalculatorSettings,
    chart_similarity_score,
    chart_similarity_score_comprehensive,
    chart_similarity_score_custom,
    normalize_similar_charts_algorithm_mode,
)
from ephemeraldaddy.core.chart import Chart


@dataclass(slots=True)
class PairSimilarityResult:
    """Similarity result for the Database View two-chart calculator."""

    score: float
    placement_score: float
    aspect_score: float
    distribution_score: float
    dominance_score: float | None = None
    nakshatra_score: float | None = None
    nakshatra_dominance_score: float | None = None
    hd_centers_score: float | None = None
    human_design_gates_score: float | None = None
    algorithm_mode: str = "default"


def calculate_pair_similarity_result(
    first: Chart,
    second: Chart,
    *,
    algorithm_mode: str,
    custom_settings: SimilarityCalculatorSettings | None,
) -> PairSimilarityResult:
    """Calculate a pair score using the currently selected Similarities Calculator mode."""

    normalized_mode = normalize_similar_charts_algorithm_mode(algorithm_mode)
    settings = custom_settings or SimilarityCalculatorSettings.defaults_from_comprehensive()
    placement_weighting_mode = settings.normalized_placement_weighting_mode()
    if normalized_mode == SIMILAR_CHARTS_ALGORITHM_CUSTOM:
        final_score, component_scores = chart_similarity_score_custom(first, second, settings)
        return PairSimilarityResult(
            score=final_score,
            placement_score=component_scores["placement"],
            aspect_score=component_scores["aspect"],
            distribution_score=component_scores["distribution"],
            dominance_score=component_scores["combined_dominance"],
            nakshatra_score=component_scores["nakshatra_placement"],
            nakshatra_dominance_score=component_scores["nakshatra_dominance"],
            hd_centers_score=component_scores["defined_centers"],
            human_design_gates_score=component_scores["human_design_gates"],
            algorithm_mode=normalized_mode,
        )
    if normalized_mode == SIMILAR_CHARTS_ALGORITHM_COMPREHENSIVE:
        (
            final_score,
            placement_score,
            aspect_score,
            distribution_score,
            nakshatra_score,
            hd_centers_score,
        ) = chart_similarity_score_comprehensive(
            first,
            second,
            placement_weighting_mode=placement_weighting_mode,
        )
        component_scores = chart_similarity_score_custom(
            first,
            second,
            SimilarityCalculatorSettings.defaults_from_comprehensive(),
        )[1]
        return PairSimilarityResult(
            score=final_score,
            placement_score=placement_score,
            aspect_score=aspect_score,
            distribution_score=distribution_score,
            dominance_score=component_scores["combined_dominance"],
            nakshatra_score=nakshatra_score,
            nakshatra_dominance_score=component_scores["nakshatra_dominance"],
            hd_centers_score=hd_centers_score,
            human_design_gates_score=component_scores["human_design_gates"],
            algorithm_mode=normalized_mode,
        )

    final_score, placement_score, aspect_score, distribution_score = chart_similarity_score(
        first,
        second,
        placement_weighting_mode=placement_weighting_mode,
    )
    return PairSimilarityResult(
        score=final_score,
        placement_score=placement_score,
        aspect_score=aspect_score,
        distribution_score=distribution_score,
        algorithm_mode=normalized_mode,
    )


def resize_similarities_list_to_contents(
    section_list: QListWidget,
    *,
    max_expanded_height: int,
    minimum_empty_height: int = 0,
) -> None:
    """Shrink an expanded similarities list to its rows while preserving a max height."""

    row_count = section_list.count()
    if row_count <= 0:
        desired_height = max(0, int(minimum_empty_height))
    else:
        fallback_row_height = max(24, section_list.fontMetrics().height() + 12)
        rows_height = 0
        for row_index in range(row_count):
            row_height = section_list.sizeHintForRow(row_index)
            rows_height += row_height if row_height > 0 else fallback_row_height
        frame_height = section_list.frameWidth() * 2
        spacing_height = max(0, row_count - 1) * int(section_list.spacing())
        desired_height = rows_height + frame_height + spacing_height + 2
    bounded_height = max(0, min(int(max_expanded_height), int(desired_height)))
    section_list.setMinimumHeight(bounded_height)
    section_list.setMaximumHeight(int(max_expanded_height))
    section_list.updateGeometry()


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
