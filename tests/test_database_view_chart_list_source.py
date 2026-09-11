from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py")
WIDGET_SOURCE = Path("ephemeraldaddy/gui/features/database_view/chart_list.py")


def test_chart_list_widget_is_owned_by_database_view_workflow() -> None:
    app_source = APP_SOURCE.read_text(encoding="utf-8")
    widget_source = WIDGET_SOURCE.read_text(encoding="utf-8")

    assert "class ChartListWidget(" not in app_source
    assert (
        "from ephemeraldaddy.gui.features.database_view.chart_list "
        "import ChartListWidget"
    ) in app_source
    assert "class ChartListWidget(QListWidget):" in widget_source
    assert "chart_drag_mime_data" in widget_source
    assert "handle_list_letter_jump" in widget_source
