from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_demo_mode_setting_and_private_widget_targets_are_wired():
    dev_tools = (REPO_ROOT / "ephemeraldaddy/gui/dev_tools.py").read_text()
    app = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    search = (REPO_ROOT / "ephemeraldaddy/gui/dbv_search_panel.py").read_text()

    assert 'SETTINGS_KEY_DEMO_MODE = "dev_tools/demo_mode"' in dev_tools
    assert 'def load_demo_mode_enabled' in dev_tools
    assert 'def add_demo_mode_setting' in dev_tools
    assert 'add_demo_mode_setting(' in app
    assert 'def _on_demo_mode_toggled' in app
    assert 'def _sync_demo_mode_visibility' in app
    assert '"chart_comments_toggle_button"' in app
    assert '"subjective_notes_panel_button"' in app
    assert '"subjective_notes_panel_scroll"' in app
    assert '"material_facts_panel_button"' in app
    assert '"material_facts_panel_scroll"' in app
    assert '"photo_gallery_panel_button"' in app
    assert '"photo_gallery_panel_scroll"' in app
    assert '"search_sentiment_section"' in app
    assert '"search_alignment_section"' in app
    assert '"search_relationship_section"' in app
    assert '"search_predictability_section"' in app
    assert '"search_notes_section"' in app
    assert '"batch_sentiment_section"' in app
    assert '"batch_relationship_section"' in app
    assert '"batch_alignment_section"' in app
    assert '"batch_predictability_section"' in app
    assert 'window.search_sentiment_section = sentiment_section' in search
    assert 'window.search_alignment_section = alignment_section' in search
    assert 'window.search_relationship_section = relationship_section' in search
    assert 'window.search_notes_section = notes_section' in search
    assert 'self.batch_sentiment_section = sentiment_section' in app
    assert 'self.batch_relationship_section = relationship_section' in app
    assert 'self.batch_alignment_section = alignment_section' in app


def test_demo_mode_uses_analytics_or_hidden_right_panel_instead_of_observations():
    right_panel = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()

    assert 'normalized in {"subjective_notes", "material_facts", "photo_gallery"}' in right_panel
    assert 'getattr(owner, "_demo_mode_enabled", False)' in right_panel
    assert 'set_chart_right_panel_container_visible(owner, analytics_available)' in right_panel
    assert 'set_chart_right_panel(owner, "analytics")' in right_panel


def test_demo_mode_new_chart_paths_do_not_reopen_private_right_panel():
    app = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert 'if not bool(getattr(self, "_demo_mode_enabled", DEMO_MODE_DEFAULT)):\n            self._set_chart_right_panel("subjective_notes")' in app
    assert 'sync_placeholder = getattr(self, "_sync_chart_right_panel_placeholder_state", None)' in app
    assert 'if callable(sync_placeholder):\n            sync_placeholder(current_chart)' in app


def test_demo_mode_controller_path_does_not_fallback_to_observations():
    controller = (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_right_panel.py").read_text()
    app = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert 'demo_mode_enabled = self._demo_mode_enabled()' in controller
    assert 'self.set_section_visible("subjective_notes", not demo_mode_enabled)' in controller
    assert 'self.set_section_visible("material_facts", not demo_mode_enabled)' in controller
    assert 'self.set_section_visible("photo_gallery", not demo_mode_enabled)' in controller
    assert 'self.set_container_visible(analytics_available)' in controller
    assert 'normalized in {"subjective_notes", "material_facts", "photo_gallery"}' in controller
    assert 'return "analytics" if self._demo_mode_enabled() else "subjective_notes"' in controller
    assert 'def _demo_mode_enabled(self) -> bool:' in controller
    assert 'SETTINGS_KEY_BATCH_TAGGING_TERMINAL_DEBUG,\n                int(self._batch_tagging_terminal_debug),' in app
    batch_toggle_start = app.index('    def _on_batch_tagging_terminal_debug_toggled')
    batch_toggle = app[batch_toggle_start : app.index('    def _batch_tagging_debug_log', batch_toggle_start)]
    assert 'SETTINGS_KEY_DEMO_MODE' not in batch_toggle


def test_demo_mode_uses_latest_chart_and_hides_social_score_sort():
    app = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert 'current_chart = getattr(self, "_latest_chart", None)' in app
    assert 'def _sync_demo_mode_sort_visibility(self, enabled: bool) -> None:' in app
    assert 'action = getattr(self, "sort_action_social_score", None)' in app
    assert 'action.setVisible(not enabled)' in app
    assert 'if enabled and getattr(self, "_sort_mode", None) == "social_score":' in app
    assert 'self._set_sort_mode("alpha")' in app
    assert 'if mode == "social_score" and bool(getattr(self, "_demo_mode_enabled", DEMO_MODE_DEFAULT)):' in app
