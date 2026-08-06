from pathlib import Path

from ephemeraldaddy.gui.features.chart_editor.exit_performance import (
    should_block_database_view_open_for_prediction_flush,
    should_defer_prediction_flush_until_prediction_view,
)

APP_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text()


def _method_source(name: str) -> str:
    marker = f"    def {name}"
    start = APP_SOURCE.index(marker)
    next_start = APP_SOURCE.find("\n    def ", start + len(marker))
    return APP_SOURCE[start:] if next_start == -1 else APP_SOURCE[start:next_start]


def test_database_view_open_does_not_block_for_classified_birth_data_prediction_flush():
    assert not should_block_database_view_open_for_prediction_flush(
        pending_prediction_flush=True,
        changed_fields={"birth_data"},
        active_right_panel="analytics",
    )
    assert should_defer_prediction_flush_until_prediction_view(
        pending_prediction_flush=True,
        changed_fields={"birth_data"},
    )


def test_database_view_open_only_blocks_for_unclassified_prediction_panel_save():
    assert should_block_database_view_open_for_prediction_flush(
        pending_prediction_flush=True,
        changed_fields=None,
        active_right_panel="predictions",
    )
    assert not should_block_database_view_open_for_prediction_flush(
        pending_prediction_flush=True,
        changed_fields=None,
        active_right_panel="analytics",
    )


def test_chart_editor_flush_uses_exit_performance_policy():
    decision = _method_source("_should_flush_predictions_before_database_view")
    open_method = _method_source("on_manage_charts")
    assert "should_block_database_view_open_for_prediction_flush" in decision
    assert "should_defer_prediction_flush_until_prediction_view" in open_method
    assert "Deferred Chart Editor prediction cache flush" in open_method
