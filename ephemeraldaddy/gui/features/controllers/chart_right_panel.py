"""Controller/view-model for Chart View's right-hand panel behaviors."""

from __future__ import annotations

from typing import Literal

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QAbstractButton, QScrollArea, QWidget

from ephemeraldaddy.gui.features.charts.cv_right_panel_stack import (
    ChartRightPanelStack,
    build_chart_right_panel_stack,
    prepare_chart_right_panel_for_loading,
    reveal_chart_right_panel_after_loading,
)

RightPanelSection = Literal[
    "analytics",
    "predictions",
    "subjective_notes",
    "material_facts",
    "time_sensitivity",
    "photo_gallery",
    "anagrams",
    "similar_charts",
]


class ChartRightPanelController:
    """Owns Chart View right-panel tab state, visibility, and render scheduling."""

    _PANEL_ATTRS: dict[str, tuple[str, str]] = {
        "analytics": ("chart_analytics_panel_scroll", "chart_analytics_panel_button"),
        "predictions": ("predictions_panel_scroll", "predictions_panel_button"),
        "subjective_notes": ("subjective_notes_panel_scroll", "subjective_notes_panel_button"),
        "material_facts": ("material_facts_panel_scroll", "material_facts_panel_button"),
        "time_sensitivity": ("time_sensitivity_panel_scroll", "time_sensitivity_panel_button"),
        "photo_gallery": ("photo_gallery_panel_scroll", "photo_gallery_panel_button"),
    }

    def __init__(self, owner: object) -> None:
        self._owner = owner
        self._stack: ChartRightPanelStack | None = None
        self._chart: object | None = None
        self._section_visible: dict[str, bool] = {key: True for key in self._PANEL_ATTRS}
        self._expand_autoscroll_installed = False

    def build_stack(
        self,
        *,
        analytics_content_widget: QWidget,
        predictions_content_widget: QWidget,
        subjective_notes_content_widget: QWidget,
        material_facts_content_widget: QWidget,
        time_sensitivity_content_widget: QWidget,
        photo_gallery_content_widget: QWidget,
        scrollbar_style: str,
    ) -> ChartRightPanelStack:
        """Build and retain the right-panel stack with controller-owned callbacks."""
        self._stack = build_chart_right_panel_stack(
            analytics_content_widget=analytics_content_widget,
            predictions_content_widget=predictions_content_widget,
            subjective_notes_content_widget=subjective_notes_content_widget,
            material_facts_content_widget=material_facts_content_widget,
            time_sensitivity_content_widget=time_sensitivity_content_widget,
            photo_gallery_content_widget=photo_gallery_content_widget,
            on_show_analytics=lambda: self.set_active_panel("analytics"),
            on_show_predictions=lambda: self.set_active_panel("predictions"),
            on_show_subjective_notes=lambda: self.set_active_panel("subjective_notes"),
            on_show_material_facts=lambda: self.set_active_panel("material_facts"),
            on_show_time_sensitivity=lambda: self.set_active_panel("time_sensitivity"),
            on_show_photo_gallery=lambda: self.set_active_panel("photo_gallery"),
            scrollbar_style=scrollbar_style,
        )
        return self._stack

    def set_chart(self, chart: object | None) -> None:
        """Set the active chart and synchronize right-panel availability."""
        self._chart = chart
        self.sync_placeholder_state()

    def set_container_visible(self, visible: bool) -> None:
        """Show/hide Chart View's full right-side container."""
        panel = getattr(self._owner, "metrics_panel", None)
        if panel is None:
            return
        panel.setVisible(visible)
        if not visible:
            return
        main_splitter = getattr(self._owner, "_main_splitter", None)
        configure_splitter = getattr(self._owner, "_configure_main_splitter", None)
        if main_splitter is not None and callable(configure_splitter):
            sizes = main_splitter.sizes()
            if len(sizes) >= 3 and sizes[2] == 0:
                configure_splitter()

    def set_active_panel(self, panel_key: str) -> None:
        """Activate one right-panel section and schedule only its needed renders."""
        self._install_expand_autoscroll()
        panel_key = self._resolve_panel_key(panel_key)
        scroll_attr, _button_attr = self._PANEL_ATTRS[panel_key]
        active_scroll = getattr(self._owner, scroll_attr, None)
        panel_stack = self._stack.stack if self._stack is not None else getattr(self._owner, "chart_right_panel_stack", None)
        if panel_stack is None or active_scroll is None:
            return
        panel_stack.setCurrentWidget(active_scroll)
        setattr(self._owner, "metrics_scroll", active_scroll)
        state = getattr(self._owner, "_chart_right_panel_state", None)
        if state is not None:
            state.active_tab = panel_key
        for tab_key, (_scroll, button_attr) in self._PANEL_ATTRS.items():
            button = getattr(self._owner, button_attr, None)
            if button is not None:
                button.setChecked(panel_key == tab_key)
        if panel_key == "analytics":
            self.set_section_visible("similar_charts", False)
        if panel_key == "subjective_notes":
            self._scroll_panel_to_top(active_scroll)
        self.schedule_render(panel_key)

    def set_section_visible(self, section: RightPanelSection, visible: bool) -> None:
        """Update tracked right-panel section visibility without scattering checks."""
        self._section_visible[section] = visible
        if section == "similar_charts" and not visible:
            collapse = getattr(self._owner, "_collapse_similar_charts_section", None)
            if callable(collapse):
                collapse()
            return
        attrs = self._PANEL_ATTRS.get(section)
        if attrs is None:
            return
        scroll_attr, button_attr = attrs
        for attr in (scroll_attr, button_attr):
            widget = getattr(self._owner, attr, None)
            if widget is not None:
                widget.setVisible(visible)
                if hasattr(widget, "setEnabled"):
                    widget.setEnabled(visible)

    def schedule_render_for_active_panel(self) -> None:
        """Backward-compatible wrapper around schedule_render()."""
        self.schedule_render()

    def schedule_render(self, section: RightPanelSection | None = None) -> None:
        """Queue render work for one right-panel section if it is visible and stale."""
        chart = self._chart or getattr(self._owner, "_latest_chart", None)
        if chart is None:
            return
        state = getattr(self._owner, "_chart_right_panel_state", None)
        active_panel = section or getattr(state, "active_tab", None)
        if active_panel == "analytics":
            render_distinguishing = getattr(self._owner, "_render_distinguishing_factors", None)
            if callable(render_distinguishing) and bool(getattr(self._owner, "_chart_analytics_distinguishing_factors_expanded", False)):
                render_distinguishing(chart)
            schedule_chart_render = getattr(self._owner, "_schedule_chart_render", None)
            if self._analytics_has_stale_sections(chart) and callable(schedule_chart_render):
                schedule_chart_render(chart)
            return
        if active_panel == "predictions":
            render_token = self._prediction_render_token(chart)
            if state is not None and state.last_render_chart_token == render_token:
                return
            render_enneagram = getattr(self._owner, "_render_enneagram_predictions", None)
            render_dndification = getattr(self._owner, "_render_dndification_predictions", None)
            if callable(render_enneagram):
                render_enneagram(chart)
            if callable(render_dndification):
                render_dndification(chart)
            if state is not None:
                state.last_render_chart_token = render_token
            return
        if active_panel in {"subjective_notes", "anagrams"} and self._is_analysis_section_visible("anagrams"):
            schedule_chart_render = getattr(self._owner, "_schedule_chart_render", None)
            if callable(schedule_chart_render):
                schedule_chart_render(chart, sections={"anagrams"})

    def sync_placeholder_state(self) -> None:
        """Sync tab availability for the current chart without clearing it implicitly."""
        current_chart = self._chart
        is_placeholder = self._is_placeholder_chart(current_chart)
        is_saved_chart = bool(current_chart is not None and getattr(self._owner, "current_chart_id", None) is not None)
        analytics_available = bool(is_saved_chart and not is_placeholder)
        self.set_section_visible("analytics", analytics_available)
        self.set_section_visible("predictions", analytics_available)
        self.set_section_visible("time_sensitivity", is_saved_chart)
        if not analytics_available:
            self.set_active_panel("subjective_notes")

    def prepare_for_loading(self) -> None:
        prepare_chart_right_panel_for_loading(self._owner)

    def reveal_after_loading(self) -> None:
        reveal_chart_right_panel_after_loading(self._owner)

    def _resolve_panel_key(self, panel_key: str) -> str:
        normalized = panel_key if panel_key in self._PANEL_ATTRS else "analytics"
        if normalized == "analytics" and not self._section_visible.get("analytics", True):
            return "subjective_notes"
        return normalized

    def _is_placeholder_chart(self, chart: object | None) -> bool:
        if chart is None:
            return False
        if bool(getattr(chart, "is_placeholder", False)):
            return True
        chart_type = str(getattr(chart, "chart_type", None) or getattr(chart, "source", None) or "").strip().lower()
        return chart_type == "placeholder"

    def _is_analysis_section_visible(self, section: str) -> bool:
        visible = getattr(self._owner, "_is_chart_analysis_section_visible", None)
        return bool(visible(section)) if callable(visible) else True

    def _analytics_has_stale_sections(self, chart: object) -> bool:
        cache_token = getattr(self._owner, "_chart_analytics_cache_token", None)
        render_tokens = getattr(self._owner, "_chart_analytics_render_tokens", None)
        dirty_sections = getattr(self._owner, "_chart_analytics_lucy_goosey_sections", None)
        if not callable(cache_token) or not isinstance(render_tokens, dict):
            return True
        current_token = str(cache_token(chart))
        for section in ("signs", "planets", "houses", "elements", "nakshatra", "modal", "gender", "planet_dynamics", "chart_type", "similar_charts"):
            if not self._is_analysis_section_visible(section):
                continue
            if dirty_sections is not None and section in dirty_sections:
                return True
            if render_tokens.get(section) != current_token:
                return True
        return False

    def _prediction_render_token(self, chart: object) -> str:
        cache_token = getattr(self._owner, "_chart_analytics_cache_token", None)
        if callable(cache_token):
            chart_token = str(cache_token(chart))
        else:
            chart_id = getattr(self._owner, "current_chart_id", None)
            chart_token = f"id:{chart_id}" if chart_id is not None else f"object:{id(chart)}"
        norms_token_fn = getattr(self._owner, "_prediction_norms_render_token", None)
        norms_token = str(norms_token_fn()) if callable(norms_token_fn) else "prediction_norms:unavailable"
        return f"{chart_token}|{norms_token}"

    def _install_expand_autoscroll(self) -> None:
        if self._expand_autoscroll_installed:
            return
        self._expand_autoscroll_installed = True
        for scroll_attr, _button_attr in self._PANEL_ATTRS.values():
            scroll_area = getattr(self._owner, scroll_attr, None)
            if not isinstance(scroll_area, QScrollArea):
                continue
            content_widget = scroll_area.widget()
            if content_widget is None:
                continue
            for toggle in content_widget.findChildren(QAbstractButton):
                if not toggle.isCheckable():
                    continue
                toggle.toggled.connect(
                    lambda checked, current_toggle=toggle: (
                        QTimer.singleShot(0, lambda t=current_toggle: self._scroll_expanded_section_into_view(t))
                        if checked
                        else None
                    )
                )

    def _scroll_panel_to_top(self, scroll_area: QScrollArea) -> None:
        def _apply() -> None:
            scroll_area.verticalScrollBar().setValue(scroll_area.verticalScrollBar().minimum())

        _apply()
        QTimer.singleShot(0, _apply)

    def _scroll_expanded_section_into_view(self, toggle: QAbstractButton) -> None:
        # Import lazily to keep the public stack builder independent of controller state.
        from ephemeraldaddy.gui.features.charts.cv_right_panel_stack import _scroll_expanded_section_into_view

        _scroll_expanded_section_into_view(toggle)
