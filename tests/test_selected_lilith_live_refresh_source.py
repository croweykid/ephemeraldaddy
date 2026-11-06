"""Source-level integration checks for live Lilith-mode cache invalidation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def _method(name: str) -> str:
    return APP.split(f"    def {name}(", 1)[1].split("\n    def ", 1)[0]


def test_lilith_settings_have_separate_callback_using_shared_qsettings():
    settings_method = _method("_ensure_settings_dialog")
    call = settings_method.split(
        "self._astrology_mode_buttons = add_astrology_mode_controls(", 1
    )[1].split("\n        )", 1)[0]
    assert "on_changed=self._on_default_astrology_context_changed" in call
    assert "on_lilith_changed=self._on_selected_lilith_mode_changed" in call
    assert "settings=self._settings" in call


def test_mode_switch_invalidates_live_and_persistent_analytics():
    callback = _method("_on_selected_lilith_mode_changed")
    assert "invalidate_all_dominant_weight_caches()" in callback
    assert "self._chart_cache.clear()" in callback
    assert "self._invalidate_database_metrics_cache()" in callback
    assert "self._database_metrics_preloaded_sections.clear()" in callback
    assert "self._database_metrics_background_preload_sections.clear()" in callback
    assert "self._schedule_deferred_database_metrics_refresh(" in callback
    assert "force_full_refresh=True" in callback
    assert "self._rankings_data_dirty = True" in callback
    assert "self._has_active_astrological_filters()" in callback
    assert "self._on_filter_changed()" in callback
    assert callback.index("self._rankings_data_dirty = True") < callback.index("if not self._left_panel_visible")
    assert callback.index("self._on_filter_changed()") < callback.index("if not self._left_panel_visible")
    assert "_on_default_astrology_context_changed" not in callback
    assert "save_astrology_context" not in callback
    token = _method("_database_metrics_config_token")
    assert '"lilith_mode": load_lilith_mode(self._settings)' in token


def test_current_chart_is_not_reloaded_and_analytics_token_tracks_mode():
    callback = _method("_on_selected_lilith_mode_changed")
    assert "_handle_selected_lilith_mode_changed" in callback
    current = _method("_handle_selected_lilith_mode_changed")
    assert "_invalidate_chart_view_navigation_cache()" in current
    assert "_mark_chart_analytics_sections_lucy_goosey(" in current
    assert '"body_dynamics_roles"' in current
    assert "chart._body_dynamics_roles_lilith_mode = None" in current
    assert "_schedule_chart_render(" in current
    assert "load_chart_by_uid(" not in current
    token = _method("_chart_analytics_cache_token")
    assert "load_lilith_mode(self._settings)" in token



def test_lilith_switch_recalculates_quadrants_with_other_house_analytics():
    """Both the visible graph and the collapsed-section dirty flag must update."""
    callback = _method("_handle_selected_lilith_mode_changed")
    assert '"quadrants"' in callback.split(
        "self._mark_chart_analytics_sections_lucy_goosey(", 1
    )[1].split("\n        )", 1)[0]
    assert '"quadrants"' in callback.split(
        "self._schedule_chart_render(", 1
    )[1].split("queue_priority=", 1)[0]
    # The normal render scheduler already recognizes quadrants as a valid
    # section and filters rendering based on visibility/cache state.
    scheduler = _method("_schedule_chart_render")
    assert '"quadrants"' in scheduler
