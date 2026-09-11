from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py")
WIDGET_SOURCE = Path(
    "ephemeraldaddy/gui/features/chart_editor/segmented_time_edit.py"
)


def test_segmented_time_edit_is_owned_by_chart_editor_workflow() -> None:
    app_source = APP_SOURCE.read_text(encoding="utf-8")
    widget_source = WIDGET_SOURCE.read_text(encoding="utf-8")

    assert "class SegmentedTimeEdit(" not in app_source
    assert (
        "from ephemeraldaddy.gui.features.chart_editor.segmented_time_edit "
        "import SegmentedTimeEdit"
    ) in app_source
    assert "class SegmentedTimeEdit(QLineEdit):" in widget_source
