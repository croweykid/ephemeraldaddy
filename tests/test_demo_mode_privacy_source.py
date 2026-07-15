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
    assert '"search_sentiment_section"' in app
    assert '"batch_sentiment_section"' in app
    assert 'window.search_sentiment_section = sentiment_section' in search
    assert 'self.batch_sentiment_section = sentiment_section' in app


def test_demo_mode_uses_analytics_or_hidden_right_panel_instead_of_observations():
    right_panel = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()

    assert 'normalized == "subjective_notes"' in right_panel
    assert 'getattr(owner, "_demo_mode_enabled", False)' in right_panel
    assert 'set_chart_right_panel_container_visible(owner, analytics_available)' in right_panel
    assert 'set_chart_right_panel(owner, "analytics")' in right_panel


def test_demo_mode_new_chart_paths_do_not_reopen_private_right_panel():
    app = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert 'if not bool(getattr(self, "_demo_mode_enabled", DEMO_MODE_DEFAULT)):\n            self._set_chart_right_panel("subjective_notes")' in app
    assert 'sync_placeholder = getattr(self, "_sync_chart_right_panel_placeholder_state", None)' in app
    assert 'if callable(sync_placeholder):\n            sync_placeholder(current_chart)' in app
