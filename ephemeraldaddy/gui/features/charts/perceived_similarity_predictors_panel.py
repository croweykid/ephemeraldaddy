"""Database View panel for reviewing perceived-similarity predictor signals."""

from __future__ import annotations

import html
from collections import Counter
from typing import Any, Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ephemeraldaddy.analysis.get_astro_twin import (
    SIMILAR_CHARTS_ALGORITHM_DEFAULT,
    find_astro_twins,
    normalize_similar_charts_algorithm_mode,
)
from ephemeraldaddy.core.db import get_chart_uid_map, load_chart, load_charts
from ephemeraldaddy.gui.features.charts.chart_similarity_relationships import (
    load_chart_similarity_relationship_states,
)


DEFAULT_HIGHLIGHT_COLOR = "#f2d16b"


class PerceivedSimilarityPredictorsPanel(QWidget):
    """Left sidebar panel that ranks predictors for saved perceived similarity scores."""

    def __init__(self, *, highlight_color: str = DEFAULT_HIGHLIGHT_COLOR, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._highlight_color = highlight_color or DEFAULT_HIGHLIGHT_COLOR
        self._output_label: QLabel | None = None
        self._refresh_button: QPushButton | None = None
        self._chart_layout: QVBoxLayout | None = None
        self._recommendation_canvas: FigureCanvas | None = None
        self._on_refresh_requested = None
        self._build_ui()

    def set_refresh_callback(self, callback) -> None:  # noqa: ANN001 - Qt callbacks are dynamically typed
        """Install the owner callback used by the panel refresh button."""
        self._on_refresh_requested = callback

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QLabel("🧾 Predictor Feedback")
        header.setStyleSheet("font-weight: 700; font-size: 13px; color: #ffffff;")
        layout.addWidget(header)

        help_label = QLabel(
            "Select one chart in Database View, then refresh to see which similarity "
            "components most strongly show up in its high perceived-similarity scores."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #d9d9d9;")
        layout.addWidget(help_label)

        refresh_button = QPushButton("Calculate for selected chart")
        refresh_button.setObjectName("perceived_similarity_predictors_refresh_button")
        refresh_button.clicked.connect(self._request_refresh)
        layout.addWidget(refresh_button)
        self._refresh_button = refresh_button

        self._chart_layout = QVBoxLayout()
        self._chart_layout.setContentsMargins(0, 0, 0, 0)
        self._chart_layout.setSpacing(0)
        layout.addLayout(self._chart_layout)

        self._output_label = QLabel()
        self._output_label.setTextFormat(Qt.RichText)
        self._output_label.setWordWrap(True)
        self._output_label.setOpenExternalLinks(False)
        self._output_label.setStyleSheet(f"font-weight: 400; color: {self._highlight_color};")
        layout.addWidget(self._output_label)
        layout.addStretch(1)
        self.set_message("Select a chart and press Calculate.")

    def _request_refresh(self) -> None:
        if callable(self._on_refresh_requested):
            self._on_refresh_requested()

    def set_message(self, message: str) -> None:
        self._clear_recommendation_chart()
        if self._output_label is not None:
            self._output_label.setText(f"<div>{html.escape(message)}</div>")

    def _set_refresh_button_chart_name(self, chart_name: str | None) -> None:
        if self._refresh_button is None:
            return
        clean_name = str(chart_name or "").strip()
        self._refresh_button.setText(
            f"Calculate for {clean_name}" if clean_name else "Calculate for selected chart"
        )

    def update_selected_chart_label(self, selected_chart_ids: list[int]) -> None:
        """Update the calculate button to name the currently selected chart."""
        if not selected_chart_ids:
            self._set_refresh_button_chart_name(None)
            return
        try:
            chart = load_chart(int(selected_chart_ids[0]))
        except Exception:  # pragma: no cover - defensive GUI label fallback
            self._set_refresh_button_chart_name(f"Chart #{int(selected_chart_ids[0])}")
            return
        self._set_refresh_button_chart_name(
            str(getattr(chart, "name", "") or f"Chart #{int(selected_chart_ids[0])}")
        )

    def refresh_for_chart_ids(
        self,
        selected_chart_ids: list[int],
        *,
        algorithm_mode: str = SIMILAR_CHARTS_ALGORITHM_DEFAULT,
        similarity_settings: Any = None,
    ) -> None:
        """Refresh predictor analysis for the first selected chart id."""
        if not selected_chart_ids:
            self._set_refresh_button_chart_name(None)
            self.set_message("Select a chart in Database View first.")
            return
        subject_chart_id = int(selected_chart_ids[0])
        try:
            subject_chart = load_chart(subject_chart_id)
        except Exception as exc:  # pragma: no cover - defensive GUI status path
            self.set_message(f"Could not load selected chart #{subject_chart_id}: {exc}")
            return

        subject_chart_name = str(getattr(subject_chart, "name", "") or f"Chart #{subject_chart_id}")
        self._set_refresh_button_chart_name(subject_chart_name)

        score_by_compared_id = self._perceived_scores_for_subject(subject_chart_id)
        scored_compared_ids = sorted(
            score_by_compared_id,
            key=lambda chart_id: (-score_by_compared_id[chart_id], chart_id),
        )
        if not scored_compared_ids:
            self.set_message(
                f"No perceived similarity scores were found for "
                f"{getattr(subject_chart, 'name', 'this chart')}."
            )
            return

        compared_charts = load_charts(scored_compared_ids)
        candidates = [
            (chart_id, compared_charts[chart_id])
            for chart_id in scored_compared_ids
            if chart_id in compared_charts
        ]
        if not candidates:
            self.set_message(
                "The saved perceived-similarity scores point to charts that are no longer available."
            )
            return

        matches = find_astro_twins(
            subject_chart,
            candidates,
            top_k=len(candidates),
            exclude_chart_id=subject_chart_id,
            least_similar=False,
            algorithm_mode=normalize_similar_charts_algorithm_mode(algorithm_mode),
            custom_settings=similarity_settings,
        )
        self._render_predictors(
            subject_chart_name=subject_chart_name,
            matches=matches,
            score_by_compared_id=score_by_compared_id,
        )

    def _perceived_scores_for_subject(self, subject_chart_id: int) -> dict[int, float]:
        states = load_chart_similarity_relationship_states()
        if not states:
            self.set_message("No perceived similarity scores have been saved yet.")
            return {}

        all_chart_uids = get_chart_uid_map()
        uid_by_chart_id = {
            int(chart_id): str(uid or "").strip().upper()
            for chart_id, uid in all_chart_uids.items()
            if uid
        }
        subject_uid = uid_by_chart_id.get(subject_chart_id)
        chart_id_by_uid = {uid: chart_id for chart_id, uid in uid_by_chart_id.items()}
        score_by_compared_id: dict[int, float] = {}
        for state in states.values():
            if not isinstance(state, Mapping):
                continue
            score = state.get("user_reported_accuracy")
            if score is None or bool(state.get("not_applicable", False)):
                continue
            compared_id = self._compared_chart_id_for_state(
                state,
                subject_chart_id=subject_chart_id,
                subject_uid=subject_uid,
                chart_id_by_uid=chart_id_by_uid,
            )
            if compared_id is None or compared_id == subject_chart_id:
                continue
            try:
                score_by_compared_id[int(compared_id)] = float(score)
            except (TypeError, ValueError):
                continue
        return score_by_compared_id

    @staticmethod
    def _compared_chart_id_for_state(
        state: Mapping[str, Any],
        *,
        subject_chart_id: int,
        subject_uid: str | None,
        chart_id_by_uid: Mapping[str, int],
    ) -> int | None:
        chart_ids = state.get("chart_ids") if isinstance(state.get("chart_ids"), list) else []
        if len(chart_ids) >= 2:
            try:
                first_id = int(chart_ids[0])
                second_id = int(chart_ids[1])
            except (TypeError, ValueError):
                first_id = second_id = None
            if first_id == subject_chart_id:
                return second_id
            if second_id == subject_chart_id:
                return first_id
        if not subject_uid:
            return None
        chart_uids = state.get("chart_uids") if isinstance(state.get("chart_uids"), list) else []
        normalized_uids = {str(uid or "").strip().upper() for uid in chart_uids}
        if subject_uid not in normalized_uids:
            return None
        other_uids = [uid for uid in normalized_uids if uid and uid != subject_uid]
        return next((chart_id_by_uid.get(uid) for uid in other_uids if chart_id_by_uid.get(uid)), None)

    def _render_predictors(
        self,
        *,
        subject_chart_name: str,
        matches: list[Any],
        score_by_compared_id: Mapping[int, float],
    ) -> None:
        component_labels = {
            "placement": "Planet/sign placements",
            "aspect": "Aspects",
            "distribution": "Element/mode distribution",
            "dominance": "Dominant planets/signs/houses",
            "nakshatra_placement": "Nakshatra placements",
            "nakshatra_dominance": "Dominant nakshatras",
            "defined_centers": "Human Design defined centers",
            "human_design_gates": "Human Design gates",
            "human_design_channels": "Human Design channels",
            "inner_planet_placement": "Inner planet placements",
            "outer_planet_placement": "Outer planet placements",
        }
        totals: Counter[str] = Counter()
        weights: Counter[str] = Counter()
        examples: dict[str, list[str]] = {}
        match_count = 0
        for rank, match in enumerate(matches, start=1):
            chart_id = int(getattr(match, "chart_id", 0) or 0)
            perceived_score = score_by_compared_id.get(chart_id)
            if perceived_score is None:
                continue
            combined_weight = (1.0 / max(1, rank)) * (max(0.0, perceived_score) / 100.0)
            match_count += 1
            for key, raw_value in self._component_scores_for_match(match).items():
                if raw_value is None:
                    continue
                value = max(0.0, min(1.0, float(raw_value)))
                totals[key] += value * combined_weight
                weights[key] += combined_weight
                examples.setdefault(key, [])
                if len(examples[key]) < 3:
                    examples[key].append(str(getattr(match, "chart_name", "") or f"#{chart_id}"))

        ranked_predictors = sorted(
            ((key, (totals[key] / weights[key]) * 100.0) for key in totals if weights[key] > 0),
            key=lambda item: (-item[1], component_labels.get(item[0], item[0])),
        )
        if not ranked_predictors:
            self.set_message("Perceived scores exist, but no similarity component rankings could be computed.")
            return

        self._render_recommendation_chart(ranked_predictors, component_labels)

        rows = [
            f"<li><b>{html.escape(component_labels.get(key, key.replace('_', ' ').title()))}</b>: "
            f"{score:.1f}% weighted high-rank signal"
            f"<br><span style='color:#d9d9d9;'>Examples: "
            f"{html.escape(', '.join(examples.get(key, [])[:3]))}</span></li>"
            for key, score in ranked_predictors[:8]
        ]
        if self._output_label is not None:
            self._output_label.setText(
                f"<div><b>{html.escape(subject_chart_name)}</b></div>"
                f"<div style='color:#d9d9d9; margin: 6px 0;'>Reviewed {match_count} "
                "saved perceived-similarity score(s). Higher entries are components that were "
                "strongest among high-ranked, highly perceived-similar comparisons.</div>"
                f"<ol>{''.join(rows)}</ol>"
            )

    def _clear_recommendation_chart(self) -> None:
        canvas = self._recommendation_canvas
        if canvas is None:
            return
        if self._chart_layout is not None:
            self._chart_layout.removeWidget(canvas)
        canvas.setParent(None)
        canvas.deleteLater()
        self._recommendation_canvas = None

    def _render_recommendation_chart(
        self,
        ranked_predictors: list[tuple[str, float]],
        labels: Mapping[str, str],
    ) -> None:
        self._clear_recommendation_chart()
        if self._chart_layout is None or not ranked_predictors:
            return

        top_predictors = ranked_predictors[:8]
        total_score = sum(max(0.0, score) for _, score in top_predictors)
        if total_score <= 0:
            return

        names = [labels.get(key, key.replace("_", " ").title()) for key, _ in top_predictors]
        weights = [(max(0.0, score) / total_score) * 100.0 for _, score in top_predictors]
        figure = Figure(figsize=(3.6, 3.0), dpi=100, facecolor="#0f0515")
        ax = figure.add_subplot(111)
        ax.set_facecolor("#0f0515")
        wedges, _ = ax.pie(
            weights,
            startangle=90,
            counterclock=False,
            wedgeprops={"linewidth": 1.0, "edgecolor": "#0f0515"},
        )
        ax.set_title("Recommended factor weights", color="#ffffff", fontsize=10)
        legend_labels = [f"{name} ({weight:.1f}%)" for name, weight in zip(names, weights, strict=False)]
        legend = ax.legend(
            wedges,
            legend_labels,
            loc="center left",
            bbox_to_anchor=(1.0, 0.5),
            fontsize=8,
            frameon=False,
        )
        for text in legend.get_texts():
            text.set_color("#e6e6e6")
        tooltip = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(12, 12),
            textcoords="offset points",
            bbox={"boxstyle": "round", "fc": "#24142d", "ec": "#f2d16b", "alpha": 0.95},
            color="#ffffff",
            fontsize=9,
        )
        tooltip.set_visible(False)

        def _on_hover(event):  # noqa: ANN001 - matplotlib callback signature
            if event.inaxes != ax:
                if tooltip.get_visible():
                    tooltip.set_visible(False)
                    canvas.draw_idle()
                return
            for wedge, name, weight in zip(wedges, names, weights, strict=False):
                contains, _ = wedge.contains(event)
                if contains:
                    tooltip.xy = (event.xdata, event.ydata)
                    tooltip.set_text(f"{name}: {weight:.2f}%")
                    tooltip.set_visible(True)
                    canvas.draw_idle()
                    return
            if tooltip.get_visible():
                tooltip.set_visible(False)
                canvas.draw_idle()

        canvas = FigureCanvas(figure)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        canvas.setMinimumHeight(260)
        canvas.mpl_connect("motion_notify_event", _on_hover)
        figure.tight_layout()
        self._chart_layout.addWidget(canvas)
        self._recommendation_canvas = canvas

    @staticmethod
    def _component_scores_for_match(match: Any) -> dict[str, float | None]:
        component_scores = dict(getattr(match, "component_scores", None) or {})
        if component_scores:
            return component_scores
        return {
            "placement": getattr(match, "placement_score", None),
            "aspect": getattr(match, "aspect_score", None),
            "distribution": getattr(match, "distribution_score", None),
            "dominance": getattr(match, "dominance_score", None),
            "nakshatra_placement": getattr(match, "nakshatra_score", None),
            "defined_centers": getattr(match, "hd_centers_score", None),
            "human_design_gates": getattr(match, "human_design_gates_score", None),
            "human_design_channels": getattr(match, "human_design_channels_score", None),
        }
