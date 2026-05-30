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
from ephemeraldaddy.analysis.human_design_reference import canonicalize_hd_authority_label
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.interpretations import NATAL_WEIGHT, PLANET_ORDER
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_house_weights,
    calculate_dominant_planet_weights,
    calculate_dominant_sign_weights,
    chart_uses_houses,
    house_for_longitude,
)
from ephemeraldaddy.gui.features.charts.presentation import get_nakshatra, sign_for_longitude
from ephemeraldaddy.gui.features.charts.similarities_export import similarities_label_has_excluded_bodies
from ephemeraldaddy.gui.features.charts.text_summary import _aspect_label, _is_structural_tautology


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
    human_design_channels_score: float | None = None
    inner_planet_placement_score: float | None = None
    outer_planet_placement_score: float | None = None
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
            human_design_channels_score=component_scores["human_design_channels"],
            inner_planet_placement_score=component_scores["inner_planet_placement"],
            outer_planet_placement_score=component_scores["outer_planet_placement"],
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
            human_design_channels_score=component_scores["human_design_channels"],
            inner_planet_placement_score=component_scores["inner_planet_placement"],
            outer_planet_placement_score=component_scores["outer_planet_placement"],
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

class DissimilaritiesFactorProvider(Protocol):
    """App-facing interface used to build Database View dissimilarity exports."""

    def _get_chart_for_filter(self, chart_id: int) -> Any | None: ...

    def _similarities_body_label(self, body: str) -> str: ...

    def _dominant_sign_top_three_labels(self, dominant_weights: dict[str, float] | None) -> set[str]: ...

    def _dominant_planet_top_three_labels(self, dominant_weights: dict[str, float] | None) -> set[str]: ...

    def _dominant_house_top_three_labels(self, dominant_weights: dict[int, float] | None) -> set[int]: ...

    def _extract_human_design_profile(self, chart: Any) -> tuple[Any, Any, Any, Any, Any, Any]: ...

    def _chart_human_design_profile(self, chart: Any) -> str: ...

    def _similarity_matching_chart_names(
        self,
        section_title: str,
        label: str,
        chart_ids: list[int],
    ) -> str: ...


_DISSIMILARITIES_SECTION_ORDER: tuple[str, ...] = (
    "Signs in positions in contrast",
    "Houses in positions in contrast",
    "Signs in houses in contrast",
    "Top 3 Dominant Signs in contrast",
    "Top 3 Dominant Bodies in contrast",
    "Top 3 Dominant Houses in contrast",
    "Dominant nakshatras in contrast",
    "Aspects in contrast",
    "Gates in contrast",
    "Channels in contrast",
    "Defined Centers in contrast",
    "Authorities in contrast",
    "Profiles in contrast",
)


def _common_section_title_for_contrast(section_title: str) -> str:
    common_title = section_title.replace(" in contrast", " in common")
    replacements = {
        "Aspects in contrast": "Aspects in common",
        "Gates in contrast": "Gates in common",
        "Channels in contrast": "Channels in common",
        "Defined Centers in contrast": "Defined Centers in common",
        "Authorities in contrast": "Authorities in common",
        "Profiles in contrast": "Profiles in common",
    }
    return replacements.get(section_title, common_title)


def _build_similarity_factor_counts(
    provider: DissimilaritiesFactorProvider,
    chart_ids: list[int],
) -> dict[str, tuple[dict[str, int], dict[str, int]]]:
    charts = [provider._get_chart_for_filter(chart_id) for chart_id in chart_ids]
    charts = [chart for chart in charts if chart is not None]
    chart_count = len(charts)
    time_specific_chart_count = sum(1 for chart in charts if chart_uses_houses(chart))
    angular_bodies = {"AS", "MC", "DS", "IC"}

    sections: dict[str, tuple[dict[str, int], dict[str, int]]] = {}

    def add(section: str, label: str, total: int | None = None) -> None:
        if not label:
            return
        counts, totals = sections.setdefault(section, ({}, {}))
        counts[label] = counts.get(label, 0) + 1
        totals.setdefault(label, int(total if total is not None else chart_count))

    for chart in charts:
        use_houses = chart_uses_houses(chart)
        for body in PLANET_ORDER:
            if not use_houses and body in angular_bodies:
                continue
            lon = chart.positions.get(body)
            if lon is None:
                continue
            body_label = provider._similarities_body_label(body)
            add(
                "Signs in positions in contrast",
                f"{body_label} in {sign_for_longitude(lon)}",
                time_specific_chart_count if body in angular_bodies else chart_count,
            )
            if use_houses:
                house_num = house_for_longitude(getattr(chart, "houses", None), lon)
                if house_num is not None and (body, house_num) not in {
                    ("AS", 1),
                    ("IC", 4),
                    ("DS", 7),
                    ("MC", 10),
                }:
                    add(
                        "Houses in positions in contrast",
                        f"{body_label}: House {house_num}",
                        time_specific_chart_count,
                    )
        if use_houses:
            houses = getattr(chart, "houses", None)
            if houses and len(houses) >= 12:
                for house_index in range(12):
                    add(
                        "Signs in houses in contrast",
                        f"House {house_index + 1}: {sign_for_longitude(houses[house_index])}",
                        time_specific_chart_count,
                    )

        dominant_weights = getattr(chart, "dominant_sign_weights", None)
        if not dominant_weights:
            dominant_weights = calculate_dominant_sign_weights(chart)
            chart.dominant_sign_weights = dominant_weights
        for sign in provider._dominant_sign_top_three_labels(dominant_weights):
            add("Top 3 Dominant Signs in contrast", sign)

        dominant_planet_weights = getattr(chart, "dominant_planet_weights", None)
        if not dominant_planet_weights:
            dominant_planet_weights = calculate_dominant_planet_weights(chart)
            chart.dominant_planet_weights = dominant_planet_weights
        for body in provider._dominant_planet_top_three_labels(dominant_planet_weights):
            add("Top 3 Dominant Bodies in contrast", provider._similarities_body_label(body))

        for house_num in provider._dominant_house_top_three_labels(calculate_dominant_house_weights(chart)):
            add("Top 3 Dominant Houses in contrast", f"House {house_num}")

        nakshatra_weights: dict[str, int] = {}
        for body in PLANET_ORDER:
            if not use_houses and body in angular_bodies:
                continue
            lon = chart.positions.get(body)
            if lon is None:
                continue
            nakshatra = get_nakshatra(lon)
            nakshatra_weights[nakshatra] = nakshatra_weights.get(nakshatra, 0) + NATAL_WEIGHT.get(body, 1)
        for name, _weight in sorted(nakshatra_weights.items(), key=lambda item: item[1], reverse=True)[:3]:
            add("Dominant nakshatras in contrast", name)

        chart_aspects: dict[str, int] = {}
        for aspect in getattr(chart, "aspects", []) or []:
            if _is_structural_tautology(aspect):
                continue
            raw_p1 = aspect.get("p1", "")
            raw_p2 = aspect.get("p2", "")
            if raw_p1 in angular_bodies and raw_p2 in angular_bodies:
                continue
            if not use_houses and (raw_p1 in angular_bodies or raw_p2 in angular_bodies):
                continue
            p1_label = provider._similarities_body_label(raw_p1)
            p2_label = provider._similarities_body_label(raw_p2)
            aspect_type = aspect.get("type", "")
            if not p1_label or not p2_label or not aspect_type:
                continue
            body_a, body_b = sorted([p1_label, p2_label])
            aspect_label = f"{body_a} {_aspect_label(aspect_type).lower()} {body_b}"
            chart_aspects[aspect_label] = (
                time_specific_chart_count
                if raw_p1 in angular_bodies or raw_p2 in angular_bodies
                else chart_count
            )
        for aspect_label, total in chart_aspects.items():
            add("Aspects in contrast", aspect_label, total)

        hd_gates, _hd_lines, hd_channels, hd_centers, _hd_type, hd_authority = (
            provider._extract_human_design_profile(chart)
        )
        for gate in sorted(set(hd_gates)):
            add("Gates in contrast", f"Gate {gate}")
        normalized_channels: set[str] = set()
        for channel in hd_channels:
            raw = str(channel).strip()
            parts = raw.split("-")
            if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                a, b = int(parts[0].strip()), int(parts[1].strip())
                raw = f"{min(a, b)}-{max(a, b)}"
            if raw:
                normalized_channels.add(raw)
        for channel in normalized_channels:
            add("Channels in contrast", channel)
        for center in {str(center).strip() for center in hd_centers if str(center).strip()}:
            add("Defined Centers in contrast", center)
        authority = canonicalize_hd_authority_label(str(hd_authority).strip())
        if authority:
            add("Authorities in contrast", authority)
        profile = provider._chart_human_design_profile(chart)
        if profile:
            add("Profiles in contrast", profile)

    return sections


def build_dissimilarity_export_sections(
    provider: DissimilaritiesFactorProvider,
    selected_chart_ids: list[int],
    db_chart_ids: list[int],
    db_total_count: int,
) -> list[tuple[str, list[tuple[str, int, int, int, int, str, str]]]]:
    """Build export-ready pair-only contrast sections for Database View dissimilarities."""

    pair_counts = _build_similarity_factor_counts(provider, selected_chart_ids)
    db_counts = _build_similarity_factor_counts(provider, db_chart_ids)
    chart_unique_counts = [
        _build_similarity_factor_counts(provider, [chart_id])
        for chart_id in selected_chart_ids[:2]
    ]
    export_sections: list[tuple[str, list[tuple[str, int, int, int, int, str, str]]]] = []
    for section_title in _DISSIMILARITIES_SECTION_ORDER:
        counts, totals = pair_counts.get(section_title, ({}, {}))
        db_section_title = _common_section_title_for_contrast(section_title)
        db_section_counts, db_section_totals = db_counts.get(section_title, ({}, {}))
        matches: list[tuple[str, int, int, int, int, str, str]] = []
        selected_total_count = len(selected_chart_ids)
        for label, count in sorted(counts.items(), key=lambda item: item[0].lower()):
            total_count = int(totals.get(label, selected_total_count))
            if (
                count != 1
                or total_count != selected_total_count
                or similarities_label_has_excluded_bodies(label)
            ):
                continue
            owner_key = ""
            for owner_index, owner_counts_by_section in enumerate(chart_unique_counts, start=1):
                owner_counts, _owner_totals = owner_counts_by_section.get(section_title, ({}, {}))
                if int(owner_counts.get(label, 0)) > 0:
                    owner_key = f"chart_{owner_index}"
                    break
            matches.append(
                (
                    label,
                    count,
                    total_count,
                    int(db_section_counts.get(label, 0)),
                    int(db_section_totals.get(label, db_total_count)),
                    provider._similarity_matching_chart_names(
                        db_section_title,
                        label,
                        selected_chart_ids,
                    ),
                    owner_key,
                )
            )
        export_sections.append((section_title, matches))
    return export_sections


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
