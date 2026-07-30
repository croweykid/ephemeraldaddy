from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
MAIN_WINDOW_SOURCE = APP_SOURCE[APP_SOURCE.index("class MainWindow"):]


def _method_source(method_name: str) -> str:
    start = MAIN_WINDOW_SOURCE.index(f"    def {method_name}")
    next_method = MAIN_WINDOW_SOURCE.index("\n    def ", start + 1)
    return MAIN_WINDOW_SOURCE[start:next_method]


def test_main_window_initializes_manage_dialog_before_widget_setup():
    initializer = _method_source("__init__")

    dialog_slot = initializer.index("self._manage_charts_dialog = None")
    widget_setup = initializer.index("self.setWindowFlag")

    assert dialog_slot < widget_setup


def test_manage_dialog_factory_tolerates_a_missing_lazy_slot():
    factory = _method_source("_get_or_create_manage_charts_dialog")

    assert 'getattr(self, "_manage_charts_dialog", None)' in factory
    assert "self._manage_charts_dialog = ManageChartsDialog(self)" in factory
