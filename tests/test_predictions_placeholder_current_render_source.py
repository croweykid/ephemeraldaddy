from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/cv_right_panel_stack.py").read_text()


def test_predictions_placeholders_are_skipped_when_render_token_is_current():
    panel_switch = SOURCE.split('def set_chart_right_panel', 1)[1].split('def _predictions_panel_render_is_current', 1)[0]

    assert '_predictions_panel_render_is_current(owner, latest_chart)' in panel_switch
    current_branch = panel_switch.split('if _predictions_panel_render_is_current(owner, latest_chart):', 1)[1].split('else:', 1)[0]
    stale_branch = panel_switch.split('else:', 1)[1]

    assert 'schedule()' in current_branch
    assert '_show_predictions_panel_pending_placeholders' not in current_branch
    assert '_show_predictions_panel_pending_placeholders(owner, latest_chart)' in stale_branch
    assert 'QTimer.singleShot(0, schedule)' in stale_branch
