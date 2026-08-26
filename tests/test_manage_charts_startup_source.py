from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
MAIN_WINDOW_SOURCE = APP_SOURCE[APP_SOURCE.index("class MainWindow(AspectPopoutMixin, QMainWindow):"):]


def _method_source(method_name: str) -> str:
    start = MAIN_WINDOW_SOURCE.index(f"    def {method_name}")
    next_method = MAIN_WINDOW_SOURCE.index("\n    def ", start + 1)
    return MAIN_WINDOW_SOURCE[start:next_method]


def test_main_window_does_not_expose_database_dialog_before_chart_view_setup():
    initializer = _method_source("__init__")

    dialog_slot = initializer.index("self._manage_charts_dialog = None")
    tag_editor = initializer.index("self.chart_tags_input = QLineEdit()")
    chart_view_setup = initializer.index("self.chart_type_label = None")

    assert tag_editor < dialog_slot
    assert chart_view_setup < dialog_slot


def test_contextual_subheader_helper_does_not_truncate_main_window_init():
    initializer = _method_source("__init__")

    assert "def _update_observations_relationship_subheaders" not in initializer
    assert "self.sentiment_checkboxes = {}" in initializer
    assert "self.chart_tags_input = QLineEdit()" in initializer


def test_manage_dialog_factory_tolerates_a_missing_lazy_slot():
    factory = _method_source("_get_or_create_manage_charts_dialog")

    assert 'getattr(self, "_manage_charts_dialog", None)' in factory
    assert "self._manage_charts_dialog = ManageChartsDialog(self)" in factory
