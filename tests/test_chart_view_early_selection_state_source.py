from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()


def test_chart_view_selection_state_exists_before_qt_widget_setup():
    init_start = APP_SOURCE.index("    def __init__(self):", APP_SOURCE.index("class MainWindow"))
    window_flag = APP_SOURCE.index("        self.setWindowFlag(Qt.Window, True)", init_start)
    early_init = APP_SOURCE[init_start:window_flag]

    assert "self.sentiment_checkboxes = {}" in early_init
    assert "self.relationship_type_checkboxes = {}" in early_init
