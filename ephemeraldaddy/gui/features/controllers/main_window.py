from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThread, Qt, QSize
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from ephemeraldaddy.gui.features.retcon.workers import SwissEphemerisPrefetchWorker
from ephemeraldaddy.gui.style import (
    DATABASE_ANALYTICS_CHART_CONTENT_MARGINS,
    DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE,
    DATABASE_ANALYTICS_CONTENT_MARGINS,
    DATABASE_ANALYTICS_CONTENT_SPACING,
    DATABASE_ANALYTICS_DROPDOWN_STYLE,
    DATABASE_ANALYTICS_DROPDOWN_TOP_PADDING,
    DATABASE_ANALYTICS_EXPORT_BUTTON_SIZE,
    DATABASE_ANALYTICS_EXPORT_ICON_SIZE,
    DATABASE_ANALYTICS_HEADER_SPACING,
    DATABASE_ANALYTICS_SUBHEADER_STYLE,
    configure_collapsible_header_toggle,
)


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
        dropdown.setStyleSheet(DATABASE_ANALYTICS_DROPDOWN_STYLE)
        for option_label, option_value in options:
            dropdown.addItem(option_label.upper(), option_value)
        dropdown.currentIndexChanged.connect(
            lambda _index, key=chart_key: self._on_dropdown_changed(key)
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
        export_button.setCursor(Qt.PointingHandCursor)
        export_button.setToolTip(f"Export {title_text} as CSV")
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
        mode = self._owner._chart_analysis_selected_mode(chart_key, chart_key)
        subtitle_text = subtitle_by_mode.get(mode)
        if subtitle_text:
            subtitle.setText(subtitle_text)

    def set_section_expanded(self, section_key: str, expanded: bool) -> None:
        self._owner._chart_analysis_section_expanded[section_key] = expanded

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

        toggle = QToolButton()
        configure_collapsible_header_toggle(
            toggle,
            title=title,
            expanded=expanded,
            style_sheet=DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE,
        )

        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(*DATABASE_ANALYTICS_CONTENT_MARGINS)
        content_layout.setSpacing(DATABASE_ANALYTICS_CONTENT_SPACING)
        content.setLayout(content_layout)
        content.setVisible(expanded)

        def toggle_content(checked: bool) -> None:
            content.setVisible(checked)
            toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
            if on_toggled is not None:
                on_toggled(checked)
            content.adjustSize()
            section.adjustSize()
            panel.adjustSize()
            panel.updateGeometry()

        toggle.toggled.connect(toggle_content)

        section_layout.addWidget(toggle)
        section_layout.addWidget(content)
        layout.addWidget(section)
        if section_key is not None:
            self._owner._chart_analysis_section_widgets[section_key] = section
        return content_layout

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
    ) -> None:
        section_layout = self.add_collapsible_section(
            panel=panel,
            layout=self._owner.metrics_layout,
            title=section_title,
            expanded=expanded,
            on_toggled=lambda checked, key=section_key: (
                self._on_section_toggled(key, checked)
                if self._on_section_toggled is not None
                else self.set_section_expanded(key, checked)
            ),
            section_key=section_key,
        )
        self._owner._chart_analysis_section_expanded[section_key] = expanded

        subtitle = QLabel(subtitle_text)
        subtitle.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
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
        chart_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        chart_container.setLayout(chart_layout)
        section_layout.addWidget(chart_container)
        self._owner._chart_analysis_section_layouts[section_key] = chart_layout
        setattr(self._owner, chart_container_attr, chart_container)
        setattr(self._owner, chart_layout_attr, chart_layout)

        if footer_text is not None:
            footer_label = QLabel(footer_text)
            footer_label.setStyleSheet(DATABASE_ANALYTICS_SUBHEADER_STYLE)
            footer_label.setWordWrap(True)
            section_layout.addWidget(footer_label)
            self._owner._chart_analysis_footer_labels[section_key] = footer_label

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
            footer_text="Chart Ruler: Unknown",
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
                "house_prevalence": "Total distribution of houses across chart, equally weighted.",
            },
            default_filename="ephemeraldaddy_chart_dominant_houses",
            chart_container_attr="house_chart_container",
            chart_layout_attr="house_chart_container_layout",
            dropdown_options=[
                ("Dominant Houses", "dominant_houses"),
                ("House Prevalence", "house_prevalence"),
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
            header_title="Nakshatra Prevalence",
            subtitle_text="Nakshatras evaluated equally based on prevalence alone (no weights).",
            subtitle_by_mode={
                "nakshatra_prevalence": "Nakshatras evaluated equally based on prevalence alone (no weights).",
                "dominant_nakshatras": "Nakshatras evaluated with weighted dominance scoring.",
            },
            default_filename="ephemeraldaddy_chart_nakshatra_prevalence",
            chart_container_attr="nakshatra_wordcloud_container",
            chart_layout_attr="nakshatra_wordcloud_container_layout",
            dropdown_options=[
                ("Nakshatra Prevalence", "nakshatra_prevalence"),
                ("Dominant Nakshatras", "dominant_nakshatras"),
            ],
            expanded=False,
        )
        self.add_section(
            panel=panel,
            section_key="modal_distribution",
            section_title="Modes",
            header_title="Mode Prevalence",
            subtitle_text="Signs grouped by modality (cardinal, mutable, fixed) with equal weights.",
            default_filename="ephemeraldaddy_chart_modal_distribution",
            chart_container_attr="modal_distribution_container",
            chart_layout_attr="modal_distribution_container_layout",
            expanded=False,
        )
        self.add_section(
            panel=panel,
            section_key="planet_dynamics",
            section_title="Body Dynamics",
            header_title="Body Dynamics",
            subtitle_text="Per-body trait scoring derived from dignity, house/sect/aspect context, dispositors, rulership, and thematic repetition.",
            default_filename="ephemeraldaddy_chart_planet_dynamics",
            chart_container_attr="planet_dynamics_container",
            chart_layout_attr="planet_dynamics_container_layout",
            expanded=False,
        )
        self.add_section(
            panel=panel,
            section_key="gender_guesser",
            section_title="Gender Guesser",
            header_title="Gender Guesser",
            subtitle_text="For the hell of it, just curious.",
            default_filename="ephemeraldaddy_chart_gender_guesser",
            chart_container_attr="gender_guesser_container",
            chart_layout_attr="gender_guesser_container_layout",
            expanded=False,
        )


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
        get_pending_changed_ids: Callable[[], set[int]],
        clear_pending_changed_ids: Callable[[], None],
    ) -> None:
        self._confirm_discard_or_save = confirm_discard_or_save
        self._get_or_create_manage_dialog = get_or_create_manage_dialog
        self._raise_manage_dialog = raise_manage_dialog
        self._get_pending_changed_ids = get_pending_changed_ids
        self._clear_pending_changed_ids = clear_pending_changed_ids

    def open_manage_charts(self) -> bool:
        if not self._confirm_discard_or_save():
            return False
        dialog = self._get_or_create_manage_dialog()
        pending_ids = set(self._get_pending_changed_ids())

        if pending_ids:
            dialog._refresh_charts(
                refresh_metrics=True,
                changed_ids=pending_ids,
            )
        elif not getattr(dialog, "_chart_rows", None):
            # Ensure first-open (or reset) state has populated rows/metrics,
            # while still skipping passive refreshes when nothing changed.
            dialog._refresh_charts(refresh_metrics=True)
        self._clear_pending_changed_ids()
        apply_launch_window_policy = getattr(dialog, "apply_launch_window_policy", None)
        use_launch_pulse = not bool(getattr(dialog, "_launch_foreground_completed", False))
        if dialog.isVisible():
            if callable(apply_launch_window_policy):
                apply_launch_window_policy(use_topmost_pulse=use_launch_pulse)
            self._raise_manage_dialog()
        else:
            dialog.show()
            if callable(apply_launch_window_policy):
                apply_launch_window_policy(use_topmost_pulse=use_launch_pulse)
            self._raise_manage_dialog()
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
