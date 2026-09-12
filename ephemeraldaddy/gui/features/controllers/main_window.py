from __future__ import annotations

import csv
import logging
from typing import Callable

from PySide6.QtCore import QPoint, QThread, QTimer, Qt, QSize
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QScrollArea,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.gui.features.charts.quadrants import (
    QUADRANT_DEFINITIONS,
    calculate_dominant_quadrant_weights,
    calculate_quadrant_prevalence_counts,
    quadrant_percentages,
)
from ephemeraldaddy.gui.features.database_view.performance import DatabaseViewOpenTiming
from ephemeraldaddy.gui.features.retcon.workers import SwissEphemerisPrefetchWorker
from ephemeraldaddy.gui.style import (
    apply_button_cursor,
    COLLAPSIBLE_SECTION_CONTENT_STYLE,
    COLLAPSIBLE_SECTION_SUBHEADER_STYLE,
    DATABASE_ANALYTICS_CHART_CONTENT_MARGINS,
    DATABASE_ANALYTICS_CHART_CONTAINER_DEBUG_STYLE,
    DATABASE_ANALYTICS_CONTENT_DEBUG_STYLE,
    DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS,
    DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE,
    DATABASE_ANALYTICS_CONTENT_MARGINS,
    DATABASE_ANALYTICS_CONTENT_SPACING,
    DATABASE_ANALYTICS_DROPDOWN_STYLE,
    apply_shared_dropdown_style,
    DATABASE_ANALYTICS_DROPDOWN_TOP_PADDING,
    DATABASE_ANALYTICS_EXPORT_BUTTON_SIZE,
    DATABASE_ANALYTICS_EXPORT_ICON_SIZE,
    DATABASE_ANALYTICS_HEADER_ROW_DEBUG_STYLE,
    DATABASE_ANALYTICS_HEADER_SPACING,
    DATABASE_ANALYTICS_SECTION_DEBUG_STYLE,
    DATABASE_ANALYTICS_SUBHEADER_STYLE,
    DATABASE_ANALYTICS_SUBTITLE_DEBUG_STYLE,
    configure_collapsible_header_toggle,
)

logger = logging.getLogger(__name__)


class ChartAnalysisSectionsController:
    """Owns chart analysis section/header construction for MainWindow."""

    def __init__(
        self,
        *,
        owner: QWidget,
        on_dropdown_changed: Callable[[str], None],
        on_export_chart_csv: Callable[[str, str], None],
        get_share_icon_path: Callable[[], str | None],
        on_section_toggled: Callable[[str, bool], None] | None = None,
    ) -> None:
        self._owner = owner
        self._on_dropdown_changed = on_dropdown_changed
        self._on_export_chart_csv = on_export_chart_csv
        self._get_share_icon_path = get_share_icon_path
        self._on_section_toggled = on_section_toggled
        self._quadrants_refresh_hook_installed = False

    def _on_header_dropdown_changed(self, chart_key: str) -> None:
        self.update_subtitle(chart_key)
        if chart_key == "quadrants":
            self.render_quadrants()
            return
        self._on_dropdown_changed(chart_key)

    def create_header(
        self,
        *,
        layout: QVBoxLayout,
        title_text: str,
        chart_key: str,
        default_filename: str,
        dropdown_options: list[tuple[str, str]] | None = None,
    ) -> None:
        header_row = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(DATABASE_ANALYTICS_HEADER_SPACING)
        header_row.setLayout(header_layout)
        if DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS:
            header_row.setStyleSheet(DATABASE_ANALYTICS_HEADER_ROW_DEBUG_STYLE)

        header_layout.addStretch(1)

        options = dropdown_options or [(title_text, chart_key)]
        dropdown = QComboBox()
        dropdown_font = QFont(dropdown.font())
        dropdown_font.setCapitalization(QFont.AllUppercase)
        if dropdown_font.pointSize() > 0:
            dropdown_font.setPointSize(max(7, dropdown_font.pointSize() - 2))
        dropdown.setFont(dropdown_font)
        dropdown.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        dropdown.setMinimumContentsLength(14)
        apply_shared_dropdown_style(dropdown)
        for option_label, option_value in options:
            dropdown.addItem(option_label.upper(), option_value)
        dropdown.currentIndexChanged.connect(
            lambda _index, key=chart_key: self._on_header_dropdown_changed(key)
        )
        header_layout.addWidget(dropdown, alignment=Qt.AlignRight)
        self._owner._chart_analysis_chart_dropdowns[chart_key] = dropdown

        export_button = QPushButton()
        share_icon_path = self._get_share_icon_path()
        if share_icon_path:
            export_button.setIcon(QIcon(share_icon_path))
            export_button.setIconSize(QSize(*DATABASE_ANALYTICS_EXPORT_ICON_SIZE))
        else:
            export_button.setText("↗")
        export_button.setFlat(True)
        export_button.setFixedSize(*DATABASE_ANALYTICS_EXPORT_BUTTON_SIZE)
        apply_button_cursor(export_button)
        export_button.setToolTip(f"Export {title_text} as CSV")
        if chart_key == "quadrants":
            export_button.clicked.connect(
                lambda _checked=False, title=title_text: self.export_quadrants_csv(title)
            )
        else:
            export_button.clicked.connect(
                lambda _checked=False, key=chart_key, title=title_text: self._on_export_chart_csv(
                    key,
                    title,
                )
            )
        header_layout.addWidget(export_button, alignment=Qt.AlignRight)

        self._owner._chart_analysis_chart_filenames[chart_key] = default_filename
        layout.addWidget(header_row)

    def update_subtitle(self, chart_key: str) -> None:
        subtitle = self._owner._chart_analysis_subtitles.get(chart_key)
        if subtitle is None:
            return
        subtitle_by_mode = self._owner._chart_analysis_subtitle_by_mode.get(chart_key, {})
        if chart_key == "quadrants":
            mode = self._quadrant_mode()
        else:
            mode = self._owner._chart_analysis_selected_mode(chart_key, chart_key)
        subtitle_text = subtitle_by_mode.get(mode)
        if subtitle_text:
            subtitle.setText(subtitle_text)

    def set_section_expanded(self, section_key: str, expanded: bool) -> None:
        self._owner._chart_analysis_section_expanded[section_key] = expanded

    def set_section_checked(self, section_key: str, expanded: bool) -> None:
        """Set a chart-analysis collapsible section state through its header toggle."""
        widgets = getattr(self._owner, "_chart_analysis_section_widgets", {})
        section = widgets.get(section_key) if isinstance(widgets, dict) else None
        toggle = section.findChild(QToolButton) if isinstance(section, QWidget) else None
        if isinstance(toggle, QToolButton):
            toggle.setChecked(expanded)
        else:
            self.set_section_expanded(section_key, expanded)

    def add_collapsible_section(
        self,
        *,
        panel: QWidget,
        layout: QVBoxLayout,
        title: str,
        expanded: bool = False,
        on_toggled: Callable[[bool], None] | None = None,
        section_key: str | None = None,
    ) -> QVBoxLayout:
        section = QWidget()
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(0)
        section.setLayout(section_layout)
        if DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS:
            section.setStyleSheet(DATABASE_ANALYTICS_SECTION_DEBUG_STYLE)

        toggle = QToolButton()
        configure_collapsible_header_toggle(
            toggle,
            title=title,
            expanded=expanded,
            style_sheet=DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE,
        )
        toggle.setFocusPolicy(Qt.TabFocus)

        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(*DATABASE_ANALYTICS_CONTENT_MARGINS)
        content_layout.setSpacing(DATABASE_ANALYTICS_CONTENT_SPACING)
        content.setLayout(content_layout)
        content_style = COLLAPSIBLE_SECTION_CONTENT_STYLE
        if DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS:
            content_style = f"{content_style} {DATABASE_ANALYTICS_CONTENT_DEBUG_STYLE}"
        content.setStyleSheet(content_style)
        content.setVisible(expanded)

        def nearest_scroll_area(widget: QWidget) -> QScrollArea | None:
            parent = widget.parentWidget()
            while parent is not None:
                if isinstance(parent, QScrollArea):
                    return parent
                parent = parent.parentWidget()
            return None

        def toggle_content(checked: bool) -> None:
            scroll_area = nearest_scroll_area(section)
            vertical_scrollbar = scroll_area.verticalScrollBar() if scroll_area is not None else None
            scroll_widget = scroll_area.widget() if scroll_area is not None else None
            viewport = scroll_area.viewport() if scroll_area is not None else None
            anchor_viewport_y = (
                section.mapTo(viewport, QPoint(0, 0)).y()
                if viewport is not None
                else None
            )

            def restore_scroll_position() -> None:
                if (
                    vertical_scrollbar is not None
                    and scroll_widget is not None
                    and anchor_viewport_y is not None
                ):
                    section_content_y = section.mapTo(scroll_widget, QPoint(0, 0)).y()
                    target_vertical_value = section_content_y - anchor_viewport_y
                    vertical_scrollbar.setValue(
                        max(
                            vertical_scrollbar.minimum(),
                            min(target_vertical_value, vertical_scrollbar.maximum()),
                        )
                    )

            content.setVisible(checked)
            toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
            panel.updateGeometry()
            restore_scroll_position()
            if checked:
                refresh_visible_canvases = getattr(
                    self._owner,
                    "_request_visible_metric_canvas_layouts",
                    None,
                )
                if callable(refresh_visible_canvases):
                    refresh_visible_canvases()
            if on_toggled is not None:
                on_toggled(checked)

        toggle.toggled.connect(toggle_content)

        section_layout.addWidget(toggle)
        section_layout.addWidget(content)
        layout.addWidget(section)
        if section_key is not None:
            self._owner._chart_analysis_section_widgets[section_key] = section
        return content_layout

    def _section_toggled(self, section_key: str, checked: bool) -> None:
        if section_key == "quadrants":
            self.set_section_expanded(section_key, checked)
            if checked:
                QTimer.singleShot(0, self.render_quadrants)
            return
        if self._on_section_toggled is not None:
            self._on_section_toggled(section_key, checked)
        else:
            self.set_section_expanded(section_key, checked)

    def add_section(
        self,
        *,
        panel: QWidget,
        section_key: str,
        section_title: str,
        header_title: str,
        subtitle_text: str,
        default_filename: str,
        chart_container_attr: str,
        chart_layout_attr: str,
        dropdown_options: list[tuple[str, str]] | None = None,
        subtitle_by_mode: dict[str, str] | None = None,
        footer_text: str | None = None,
        expanded: bool = True,
        parent_layout: QVBoxLayout | None = None,
    ) -> None:
        section_layout = self.add_collapsible_section(
            panel=panel,
            layout=parent_layout or self._owner.metrics_layout,
            title=section_title,
            expanded=expanded,
            on_toggled=lambda checked, key=section_key: self._section_toggled(key, checked),
            section_key=section_key,
        )
        self._owner._chart_analysis_section_expanded[section_key] = expanded

        subtitle = QLabel(subtitle_text)
        subtitle_style = COLLAPSIBLE_SECTION_SUBHEADER_STYLE
        if DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS:
            subtitle_style = f"{subtitle_style} {DATABASE_ANALYTICS_SUBTITLE_DEBUG_STYLE}"
        subtitle.setStyleSheet(subtitle_style)
        subtitle.setWordWrap(True)
        section_layout.addWidget(subtitle)
        self._owner._chart_analysis_subtitles[section_key] = subtitle
        self._owner._chart_analysis_subtitle_by_mode[section_key] = subtitle_by_mode or {}

        section_layout.addSpacing(DATABASE_ANALYTICS_DROPDOWN_TOP_PADDING)

        self.create_header(
            layout=section_layout,
            title_text=header_title,
            chart_key=section_key,
            default_filename=default_filename,
            dropdown_options=dropdown_options,
        )

        chart_container = QWidget()
        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(*DATABASE_ANALYTICS_CHART_CONTENT_MARGINS)
        chart_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        chart_container.setLayout(chart_layout)
        if DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS:
            chart_container.setStyleSheet(DATABASE_ANALYTICS_CHART_CONTAINER_DEBUG_STYLE)
        section_layout.addWidget(chart_container)
        self._owner._chart_analysis_section_layouts[section_key] = chart_layout
        setattr(self._owner, chart_container_attr, chart_container)
        setattr(self._owner, chart_layout_attr, chart_layout)

        has_above_average_details = section_key in {
            "dominant_signs",
            "dominant_planets",
            "dominant_houses",
            "nakshatra_prevalence",
            "modal_distribution",
        }
        has_footer_details = footer_text is not None
        if has_above_average_details or has_footer_details:
            details_link = QLabel(
                '<a href="chart-analysis-details" '
                'style="color:#6fa8dc;text-decoration:none;font-weight:700;">more info...</a>'
            )
            details_link.setTextFormat(Qt.RichText)
            details_link.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
            details_link.setOpenExternalLinks(False)
            details_link.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
            section_layout.addWidget(details_link, 0, Qt.AlignLeft)

            details_container = QWidget()
            details_layout = QVBoxLayout()
            details_layout.setContentsMargins(0, 0, 0, 0)
            details_layout.setSpacing(8)
            details_container.setLayout(details_layout)
            details_container.setVisible(False)
            section_layout.addWidget(details_container)

            def toggle_details(
                _target: str = "",
                *,
                link: QLabel = details_link,
                container: QWidget = details_container,
            ) -> None:
                expanded = not container.isVisible()
                container.setVisible(expanded)
                link.setText(
                    '<a href="chart-analysis-details" '
                    'style="color:#6fa8dc;text-decoration:none;font-weight:700;">'
                    f'{"show less" if expanded else "more info..."}</a>'
                )

            details_link.linkActivated.connect(toggle_details)

            if has_above_average_details:
                above_average_label = QLabel("")
                above_average_label.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
                above_average_label.setWordWrap(True)
                above_average_label.setOpenExternalLinks(False)
                above_average_label.linkActivated.connect(self._owner._on_chart_analysis_above_average_link_activated)
                details_layout.addWidget(above_average_label)
                self._owner._chart_analysis_above_average_labels[section_key] = above_average_label

            if has_footer_details:
                footer_label = QLabel(footer_text)
                footer_label.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
                footer_label.setWordWrap(True)
                details_layout.addWidget(footer_label)
                self._owner._chart_analysis_footer_labels[section_key] = footer_label

    def _quadrant_mode(self) -> str:
        dropdown = self._owner._chart_analysis_chart_dropdowns.get("quadrants")
        if isinstance(dropdown, QComboBox):
            mode = dropdown.currentData()
            if isinstance(mode, str) and mode:
                return mode
        return "quadrant_prevalence"

    def _quadrant_values(self, chart: object) -> dict[str, float]:
        if self._quadrant_mode() == "dominant_quadrants":
            return calculate_dominant_quadrant_weights(chart)
        return calculate_quadrant_prevalence_counts(chart)

    def _draw_quadrants(self, ax, chart: object) -> None:
        ax.clear()
        if not chart_uses_houses(chart):
            ax.set_axis_off()
            ax.text(
                0.5,
                0.5,
                "Birth time required for house-based quadrant analysis.",
                transform=ax.transAxes,
                ha="center",
                va="center",
                color="#f5f5f5",
                fontsize=10,
            )
            return

        values_by_quadrant = self._quadrant_values(chart)
        percentages = quadrant_percentages(values_by_quadrant)
        quadrant_keys = [quadrant for quadrant, _meaning, _houses in QUADRANT_DEFINITIONS]
        values = [float(values_by_quadrant.get(quadrant, 0.0)) for quadrant in quadrant_keys]
        bars = ax.bar(quadrant_keys, values, color="#6fa8dc")
        apply_axes = getattr(self._owner, "_apply_standard_ncv_bar_chart_axes", None)
        if callable(apply_axes):
            apply_axes(ax, quadrant_keys)
        else:
            ax.tick_params(axis="x", labelsize=8, colors="#f5f5f5")
            ax.tick_params(axis="y", labelsize=8, colors="#f5f5f5")
        max_value = max(values) if values else 0.0
        ax.set_ylim(0, max(1.0, max_value * 1.18))
        offset = max(0.05, max_value * 0.025)
        for bar, quadrant, value in zip(bars, quadrant_keys, values, strict=True):
            value_text = f"{value:.1f}" if self._quadrant_mode() == "dominant_quadrants" else f"{value:g}"
            ax.text(
                bar.get_x() + (bar.get_width() / 2),
                value + offset,
                f"{value_text} · {percentages[quadrant]:.0f}%",
                ha="center",
                va="bottom",
                color="#f5f5f5",
                fontsize=8,
            )
        mode_title = "Weighted" if self._quadrant_mode() == "dominant_quadrants" else "Object Count"
        ax.set_title(f"Quadrants — {mode_title}", color="#f5f5f5", fontsize=10, pad=8)
        ax.figure.tight_layout()

    def render_quadrants(self, chart: object | None = None) -> None:
        if not self._owner._chart_analysis_section_expanded.get("quadrants", False):
            return
        chart = chart or getattr(self._owner, "_latest_chart", None)
        if chart is None:
            return
        render_metric_panel = getattr(self._owner, "_render_metric_panel", None)
        layout = getattr(self._owner, "quadrants_chart_container_layout", None)
        if not callable(render_metric_panel) or layout is None:
            return
        if not hasattr(self._owner, "quadrants_canvas"):
            self._owner.quadrants_canvas = None
        render_metric_panel(
            canvas_attr="quadrants_canvas",
            container_layout=layout,
            figsize=(5.5, 3.2),
            title="Quadrants",
            draw_fn=self._draw_quadrants,
            chart=chart,
        )

    def export_quadrants_csv(self, title: str = "Quadrants") -> None:
        chart = getattr(self._owner, "_latest_chart", None)
        if chart is None:
            return
        default_name = self._owner._chart_analysis_chart_filenames.get(
            "quadrants",
            "ephemeraldaddy_chart_quadrants",
        )
        path, _selected_filter = QFileDialog.getSaveFileName(
            self._owner,
            f"Export {title} as CSV",
            f"{default_name}.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return
        values = self._quadrant_values(chart)
        percentages = quadrant_percentages(values)
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Quadrant", "Meaning", "Houses", "Value", "Percent"])
            for quadrant, meaning, houses in QUADRANT_DEFINITIONS:
                value = values.get(quadrant, 0.0)
                writer.writerow(
                    [
                        quadrant,
                        meaning,
                        f"{houses[0]}-{houses[-1]}",
                        value,
                        round(percentages[quadrant], 2),
                    ]
                )

    def _install_quadrants_refresh_hook(self) -> None:
        if self._quadrants_refresh_hook_installed:
            return
        schedule_chart_render = getattr(self._owner, "_schedule_chart_render", None)
        if not callable(schedule_chart_render):
            return

        def schedule_with_quadrants(chart, *args, **kwargs):
            result = schedule_chart_render(chart, *args, **kwargs)
            if self._owner._chart_analysis_section_expanded.get("quadrants", False):
                QTimer.singleShot(0, lambda chart=chart: self.render_quadrants(chart))
            return result

        self._owner._schedule_chart_render = schedule_with_quadrants
        self._quadrants_refresh_hook_installed = True

    def create_sections(self, panel: QWidget) -> None:
        self.add_section(
            panel=panel,
            section_key="dominant_signs",
            section_title="Signs",
            header_title="Dominant Signs",
            subtitle_text="Signs evaluated with priority weights (rulerships/houses/signs/etc).",
            subtitle_by_mode={
                "dominant_signs": "Signs evaluated with priority weights (rulerships/houses/signs/etc).",
                "sign_prevalence": "Total distribution of signs across chart, equally weighted.",
            },
            default_filename="ephemeraldaddy_chart_dominant_signs",
            chart_container_attr="sign_chart_container",
            chart_layout_attr="sign_chart_container_layout",
            dropdown_options=[
                ("Dominant Signs", "dominant_signs"),
                ("Sign Prevalence", "sign_prevalence"),
            ],
            footer_text="<b>Avg Weight:</b> 0, <b>Median:</b> 0<br><b>Min:</b> 0, <b>Max:</b> 0, <b>Range:</b> 0, <b>Total:</b> 0",
            expanded=False,
        )
        self.add_section(
            panel=panel,
            section_key="dominant_planets",
            section_title="Bodies",
            header_title="Dominant bodies",
            subtitle_text="Bodies evaluated with priority weights (rulerships/houses/signs/etc).",
            subtitle_by_mode={
                "dominant_planets": "Bodies evaluated with priority weights (rulerships/houses/signs/etc).",
                "sidereal_planet_prevalence": "Bodies mapped from each body's nakshatra ruler using weighted body scoring.",
            },
            default_filename="ephemeraldaddy_chart_dominant_planets",
            chart_container_attr="planet_chart_container",
            chart_layout_attr="planet_chart_container_layout",
            dropdown_options=[
                ("Dominant Bodies", "dominant_planets"),
                ("Dominant Bodies (by nakshatra)", "sidereal_planet_prevalence"),
            ],
            footer_text="<b>Chart Ruler:</b> Unknown",
            expanded=False,
        )
        self.add_section(
            panel=panel,
            section_key="planet_dynamics",
            section_title="Body Dynamics",
            header_title="Body Dynamics",
            subtitle_text="Per-body aspect counts grouped as Antagonizing, Enabling, and Escalating, plus each body's relative dominance share.",
            default_filename="ephemeraldaddy_chart_planet_dynamics",
            chart_container_attr="planet_dynamics_container",
            chart_layout_attr="planet_dynamics_container_layout",
            expanded=False,
        )
        self.add_section(
            panel=panel,
            section_key="dominant_houses",
            section_title="Houses",
            header_title="Dominant houses",
            subtitle_text="Houses evaluated with priority weights (rulerships/houses/signs/etc).",
            subtitle_by_mode={
                "dominant_houses": "Houses evaluated with priority weights (rulerships/houses/signs/etc).",
                "house_prevalence": "Distribution of houses. Each listed body/point counts once. No weights applied.",
            },
            default_filename="ephemeraldaddy_chart_dominant_houses",
            chart_container_attr="house_chart_container",
            chart_layout_attr="house_chart_container_layout",
            dropdown_options=[
                ("Dominant Houses", "dominant_houses"),
                ("House Prevalence", "house_prevalence"),
            ],
            footer_text="<b>Avg Weight:</b> 0, <b>Median:</b> 0<br><b>Min:</b> 0, <b>Max:</b> 0, <b>Range:</b> 0, <b>Total:</b> 0",
            expanded=False,
        )
        self.add_section(
            panel=panel,
            section_key="quadrants",
            section_title="Quadrants",
            header_title="Quadrants",
            subtitle_text="House quadrants grouped as I (1–3), II (4–6), III (7–9), and IV (10–12).",
            subtitle_by_mode={
                "quadrant_prevalence": "Object distribution across the four house quadrants. No weights applied.",
                "dominant_quadrants": "Existing house-dominance weights aggregated into the four house quadrants.",
            },
            default_filename="ephemeraldaddy_chart_quadrants",
            chart_container_attr="quadrants_chart_container",
            chart_layout_attr="quadrants_chart_container_layout",
            dropdown_options=[
                ("Object Count", "quadrant_prevalence"),
                ("Weighted", "dominant_quadrants"),
            ],
            expanded=False,
        )
        self.add_section(
            panel=panel,
            section_key="dominant_elements",
            section_title="Elements",
            header_title="Dominant elements",
            subtitle_text="Elements evaluated with sign-priority weights (derived from dominant sign scoring).",
            subtitle_by_mode={
                "dominant_elements": "Elements evaluated with sign-priority weights (derived from dominant sign scoring).",
                "elemental_prevalence": "Elements evaluated equally based on prevalence alone (not weighted by position).",
            },
            default_filename="ephemeraldaddy_chart_elements",
            chart_container_attr="element_chart_container",
            chart_layout_attr="element_chart_container_layout",
            dropdown_options=[
                ("Dominant Elements", "dominant_elements"),
                ("Elemental Prevalence", "elemental_prevalence"),
            ],
            expanded=False,
        )
        self.add_section(
            panel=panel,
            section_key="nakshatra_prevalence",
            section_title="Nakshatras",
            header_title="Dominant Nakshatras",
            subtitle_text="Nakshatras evaluated with weighted dominance scoring.",
            subtitle_by_mode={
                "dominant_nakshatras": "Nakshatras evaluated with weighted dominance scoring.",
                "nakshatra_prevalence": "Nakshatras evaluated equally based on prevalence alone (no weights).",
            },
            default_filename="ephemeraldaddy_chart_nakshatra_prevalence",
            chart_container_attr="nakshatra_wordcloud_container",
            chart_layout_attr="nakshatra_wordcloud_container_layout",
            dropdown_options=[
                ("Dominant Nakshatras", "dominant_nakshatras"),
                ("Nakshatra Prevalence", "nakshatra_prevalence"),
            ],
            footer_text="<b>Avg Weight:</b> 0, <b>Median:</b> 0<br><b>Min:</b> 0, <b>Max:</b> 0, <b>Range:</b> 0, <b>Total:</b> 0",
            expanded=False,
        )
        self.add_section(
            panel=panel,
            section_key="modal_distribution",
            section_title="Modes",
            header_title="Dominant Modes",
            subtitle_text="Modes weighted by dominant sign scoring (derived from sign weights).",
            subtitle_by_mode={
                "dominant_modes": "Modes weighted by dominant sign scoring (derived from sign weights).",
                "modal_prevalence": "Signs grouped by modality (cardinal, mutable, fixed) with equal prevalence counts.",
            },
            default_filename="ephemeraldaddy_chart_modal_distribution",
            chart_container_attr="modal_distribution_container",
            chart_layout_attr="modal_distribution_container_layout",
            dropdown_options=[
                ("Dominant Modes", "dominant_modes"),
                ("Modal Prevalence", "modal_prevalence"),
            ],
            expanded=False,
        )
        self.add_section(
            panel=panel,
            section_key="chart_type",
            section_title="Chart Type",
            header_title="Chart Type",
            subtitle_text="Jones distribution type + detected aspect pattern motifs.",
            default_filename="ephemeraldaddy_chart_type",
            chart_container_attr="chart_type_container",
            chart_layout_attr="chart_type_container_layout",
            expanded=False,
        )
        self._install_quadrants_refresh_hook()


class RetconDialogController:
    """Owns Retcon dialog lifecycle for MainWindow composition."""

    def __init__(self, dialog_factory: Callable[[QWidget], QWidget]) -> None:
        self._dialog_factory = dialog_factory
        self._dialog: QWidget | None = None

    def show(self, parent: QWidget) -> None:
        if self._dialog is None:
            self._dialog = self._dialog_factory(parent)
        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()


class ChartsController:
    """Owns Manage Charts dialog lifecycle for MainWindow composition."""

    def __init__(
        self,
        confirm_discard_or_save: Callable[[], bool],
        get_or_create_manage_dialog: Callable[[], QWidget],
        raise_manage_dialog: Callable[[], None],
        get_pending_changed_refreshes: Callable[[], tuple[set[int], set[int], bool]],
        clear_pending_changed_refreshes: Callable[[], None],
    ) -> None:
        self._confirm_discard_or_save = confirm_discard_or_save
        self._get_or_create_manage_dialog = get_or_create_manage_dialog
        self._raise_manage_dialog = raise_manage_dialog
        self._get_pending_changed_refreshes = get_pending_changed_refreshes
        self._clear_pending_changed_refreshes = clear_pending_changed_refreshes

    def confirm_manage_charts_open(
        self,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> bool:
        if progress_callback:
            progress_callback("Checking unsaved changes…", 68)
        if not self._confirm_discard_or_save():
            logger.debug("Cancelled Database View open due to unsaved-change prompt.")
            return False
        return True

    def open_manage_charts(
        self,
        *,
        open_timing: DatabaseViewOpenTiming,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> bool:
        if progress_callback:
            progress_callback("Preparing Database View shell…", 72)
        dialog = self._get_or_create_manage_dialog()
        open_timing.phase("dialog_shell")
        pending_metric_ids, pending_lightweight_ids, force_full_refresh = (
            self._get_pending_changed_refreshes()
        )
        pending_ids = set(pending_metric_ids) | set(pending_lightweight_ids)
        pending_refresh_metrics = bool(pending_metric_ids)
        was_visible = dialog.isVisible()
        logger.debug(
            "Opening Database View dialog (visible=%s pending_changed_ids=%s pending_metric_ids=%s).",
            was_visible,
            len(pending_ids),
            len(pending_metric_ids),
        )

        refresh_after_show: Callable[[], None] | None = None
        refresh_reason = "none"
        if force_full_refresh:
            refresh_reason = "deleted_chart"
            def refresh_after_show() -> None:
                dialog._refresh_charts(
                    refresh_metrics=True,
                    defer_metrics_refresh=progress_callback is None,
                    refresh_tag_completers=True,
                    progress_callback=progress_callback,
                )
        elif pending_ids:
            refresh_reason = "pending_changes"
            def refresh_after_show() -> None:
                dialog._refresh_charts(
                    refresh_metrics=pending_refresh_metrics,
                    changed_ids=pending_ids,
                    defer_metrics_refresh=pending_refresh_metrics and progress_callback is None,
                    refresh_tag_completers=pending_refresh_metrics,
                    progress_callback=progress_callback,
                )
        elif not getattr(dialog, "_chart_rows", None):
            refresh_reason = "initial_population"
            def refresh_after_show() -> None:
                dialog._refresh_charts(
                    refresh_metrics=True,
                    defer_metrics_refresh=progress_callback is None,
                    progress_callback=progress_callback,
                )
        if progress_callback:
            progress_callback("Showing Database View shell…", 88)
        self._clear_pending_changed_refreshes()
        apply_launch_window_policy = getattr(dialog, "apply_launch_window_policy", None)
        use_launch_pulse = not bool(getattr(dialog, "_launch_foreground_completed", False))
        if was_visible:
            if callable(apply_launch_window_policy):
                apply_launch_window_policy(use_topmost_pulse=use_launch_pulse)
            self._raise_manage_dialog()
        else:
            if callable(apply_launch_window_policy):
                apply_launch_window_policy(use_topmost_pulse=use_launch_pulse)
            else:
                dialog.show()
            self._raise_manage_dialog()
        open_timing.phase(
            "show_shell",
            was_visible=was_visible,
            refresh_reason=refresh_reason,
        )
        if refresh_after_show is not None:
            if progress_callback:
                progress_callback("Loading Database rows…", 89)
                app = QApplication.instance()
                if app is not None:
                    app.processEvents()
                try:
                    refresh_after_show()
                    if app is not None:
                        app.processEvents()
                except BaseException:
                    open_timing.complete(
                        was_visible=was_visible,
                        refresh_reason=refresh_reason,
                        status="error",
                    )
                    raise
                open_timing.phase("refresh", refresh_reason=refresh_reason)
                open_timing.complete(
                    was_visible=was_visible,
                    refresh_reason=refresh_reason,
                )
                progress_callback("Database View is ready.", 99)
            else:
                def refresh_and_record() -> None:
                    try:
                        refresh_after_show()
                    except BaseException:
                        open_timing.complete(
                            was_visible=was_visible,
                            refresh_reason=refresh_reason,
                            status="error",
                        )
                        raise
                    open_timing.phase("refresh", refresh_reason=refresh_reason)
                    open_timing.complete(
                        was_visible=was_visible,
                        refresh_reason=refresh_reason,
                    )

                QTimer.singleShot(0, refresh_and_record)
        else:
            open_timing.complete(
                was_visible=was_visible,
                refresh_reason=refresh_reason,
            )

        logger.debug(
            "Database View dialog foreground request complete (topmost_pulse=%s).",
            use_launch_pulse,
        )
        return True


class EphemerisPrefetchController:
    """Manages Swiss Ephemeris prefetch worker/thread lifecycle."""

    def __init__(
        self,
        owner: QWidget,
        offline_mode_checker: Callable[[], bool],
        on_failure: Callable[[str], None],
    ) -> None:
        self._owner = owner
        self._offline_mode_checker = offline_mode_checker
        self._on_failure = on_failure
        self._thread: QThread | None = None
        self._worker: SwissEphemerisPrefetchWorker | None = None

    def start(self) -> None:
        if self._offline_mode_checker() or self._thread is not None:
            return
        thread = QThread(self._owner)
        worker = SwissEphemerisPrefetchWorker()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_refs)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _clear_refs(self) -> None:
        self._thread = None
        self._worker = None

    def _on_finished(self, ok: bool, message: str) -> None:
        if not ok:
            self._on_failure(message)
