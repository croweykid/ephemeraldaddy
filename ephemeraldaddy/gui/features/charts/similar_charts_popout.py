"""Helpers for Similar Charts list rendering and popout UI."""

from __future__ import annotations

import html
from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

SIMILAR_INFO_TARGET_PREFIX = "sim-info"


def is_similar_info_target(target: str) -> bool:
    return str(target or "").strip().startswith(f"{SIMILAR_INFO_TARGET_PREFIX}:")


def make_similar_info_target(*, info_link_prefix: str, chart_id: int) -> str:
    return f"{info_link_prefix}:{int(chart_id)}"


def map_similar_info_targets(
    *,
    matches: list[Any],
    info_link_prefix: str,
) -> dict[str, Any]:
    return {
        make_similar_info_target(info_link_prefix=info_link_prefix, chart_id=int(match.chart_id)): match
        for match in matches
    }


def build_similarity_reasoning_panel_text(
    *,
    match: Any,
    subject_name: str,
    resolve_similarity_band: Callable[[float], tuple[str, str]],
) -> str:
    similarity_percent = float(getattr(match, "score", 0.0)) * 100.0
    placement_percent = float(getattr(match, "placement_score", 0.0)) * 100.0
    aspect_percent = float(getattr(match, "aspect_score", 0.0)) * 100.0
    distribution_percent = float(getattr(match, "distribution_score", 0.0)) * 100.0
    score_rows: list[tuple[str, float]] = [
        ("Placements", placement_percent),
        ("Aspects", aspect_percent),
        ("Distribution", distribution_percent),
    ]
    nakshatra_score = getattr(match, "nakshatra_score", None)
    if nakshatra_score is not None:
        score_rows.append(("Nakshatra", float(nakshatra_score) * 100.0))
    hd_centers_score = getattr(match, "hd_centers_score", None)
    if hd_centers_score is not None:
        score_rows.append(("Defined Centers", float(hd_centers_score) * 100.0))
    top_factor, top_value = max(score_rows, key=lambda item: item[1])
    bottom_factor, bottom_value = min(score_rows, key=lambda item: item[1])
    band_label, _band_color = resolve_similarity_band(similarity_percent)
    compared_name = str(
        getattr(match, "chart_name", "") or f"Chart #{getattr(match, 'chart_id', '?')}"
    ).strip()
    reasoning_body = (
        f"Compared: {subject_name} ↔ {compared_name}\n"
        f"Overall similarity is {similarity_percent:.1f}% ({band_label}). "
        f"Strongest alignment comes from {top_factor.lower()} at {top_value:.1f}%. "
        f"Weakest alignment comes from {bottom_factor.lower()} at {bottom_value:.1f}%.\n"
        f"Component breakdown: placements {placement_percent:.1f}%, "
        f"aspects {aspect_percent:.1f}%, distribution {distribution_percent:.1f}%."
    )
    if nakshatra_score is not None:
        reasoning_body = f"{reasoning_body} Nakshatra similarity is {float(nakshatra_score) * 100.0:.1f}%."
    if hd_centers_score is not None:
        reasoning_body = (
            f"{reasoning_body} Defined centers similarity is {float(hd_centers_score) * 100.0:.1f}%."
        )
    return "\n".join(
        [
            "CHART INFO",
            "",
            "Name: Similarity Analysis",
            "Reasoning:",
            reasoning_body,
        ]
    )


def load_similar_chart_candidates(
    *,
    rows: list[tuple[Any, ...]],
    current_chart_id: int | None,
    load_chart_by_id: Callable[[int], Any],
) -> list[tuple[int, Any]]:
    candidates: list[tuple[int, Any]] = []
    for row in rows:
        chart_id = int(row[0])
        is_placeholder = bool(row[15]) if len(row) > 15 else False
        if current_chart_id is not None and chart_id == current_chart_id:
            continue
        if is_placeholder:
            continue
        try:
            candidate = load_chart_by_id(chart_id)
        except Exception:
            continue
        candidates.append((chart_id, candidate))
    return candidates


def render_similar_match_blocks(
    *,
    matches: list[Any],
    highlight_color: str,
    resolve_similarity_band: Callable[[float], tuple[str, str]],
    info_link_prefix: str = "sim-info",
) -> str:
    if not matches:
        return "No charts found."
    blocks: list[str] = []
    for rank, match in enumerate(matches, start=1):
        safe_name = html.escape(str(match.chart_name))
        similarity_percent = float(match.score) * 100.0
        band_label, band_color = resolve_similarity_band(similarity_percent)
        extra_bits: list[str] = []
        if getattr(match, "nakshatra_score", None) is not None:
            extra_bits.append(f"nakshatra {float(match.nakshatra_score) * 100.0:.0f}%")
        if getattr(match, "hd_centers_score", None) is not None:
            extra_bits.append(f"defined centers {float(match.hd_centers_score) * 100.0:.0f}%")
        extra_suffix = f", {', '.join(extra_bits)}" if extra_bits else ""
        blocks.append(
            (
                f'<span style="font-weight: bold; color: {highlight_color};">{rank}.</span> '
                f'#{match.chart_id} — <a href="{match.chart_id}">{safe_name}</a> '
                f'<a href="{make_similar_info_target(info_link_prefix=info_link_prefix, chart_id=int(match.chart_id))}">ⓘ</a><br>'
                f'Similarity <span style="color: {band_color}; font-weight: 600;">'
                f"{similarity_percent:.1f}% ({band_label})</span> "
                f"(placements {match.placement_score * 100.0:.0f}%, "
                f"aspects {match.aspect_score * 100.0:.0f}%, "
                f"distribution {match.distribution_score * 100.0:.0f}%{extra_suffix})"
            )
        )
    return "<br><br>".join(blocks)


def build_similar_charts_popout_dialog(
    *,
    parent: QWidget,
    subject_name: str,
    most_similar_matches: list[Any],
    least_similar_matches: list[Any],
    on_link_activated: Callable[[str], None],
    header_style: str,
    output_style: str,
    highlight_color: str,
    resolve_similarity_band: Callable[[float], tuple[str, str]],
    info_link_prefix: str = "sim-info",
    configure_splitter: Callable[[QSplitter], None] | None = None,
) -> QDialog:
    dialog = QDialog(parent)
    dialog.setWindowTitle(f"Similar Charts — {subject_name}")
    dialog.setModal(False)
    dialog.resize(860, 700)
    layout = QVBoxLayout(dialog)

    title_label = QLabel(f"Similar Charts for {subject_name}")
    title_label.setStyleSheet(header_style)
    layout.addWidget(title_label)

    splitter = QSplitter(Qt.Horizontal)
    splitter.setChildrenCollapsible(False)
    splitter.setHandleWidth(6)
    if configure_splitter is not None:
        configure_splitter(splitter)
    layout.addWidget(splitter, 1)

    def _panel(title: str, matches: list[Any], panel_key: str) -> QWidget:
        panel_widget = QWidget()
        panel_layout = QVBoxLayout(panel_widget)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(6)
        header_label = QLabel(title)
        header_label.setStyleSheet(header_style)
        panel_layout.addWidget(header_label)

        result_label = QLabel()
        result_label.setWordWrap(True)
        result_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        result_label.setOpenExternalLinks(False)
        result_label.linkActivated.connect(on_link_activated)
        result_label.setStyleSheet(output_style)
        result_label.setText(
            render_similar_match_blocks(
                matches=matches,
                highlight_color=highlight_color,
                resolve_similarity_band=resolve_similarity_band,
                info_link_prefix=f"{info_link_prefix}:{panel_key}",
            )
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(result_label)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        panel_layout.addWidget(scroll, 1)
        return panel_widget

    splitter.addWidget(_panel("Top 25 Most Similar charts", most_similar_matches, "most"))
    splitter.addWidget(_panel("Top 25 Least Similar Charts", least_similar_matches, "least"))
    splitter.setSizes([430, 430])
    return dialog
