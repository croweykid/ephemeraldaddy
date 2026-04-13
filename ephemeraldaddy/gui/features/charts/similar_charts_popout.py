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
                f'<a href="{info_link_prefix}:{match.chart_id}">ⓘ</a><br>'
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
