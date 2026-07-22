from pathlib import Path


PROPERTY_MANAGER_SOURCE = Path("ephemeraldaddy/gui/property_manager.py").read_text()


def test_embedded_property_manager_queues_deferred_refresh_after_reload() -> None:
    create_widget_block = PROPERTY_MANAGER_SOURCE.split("def create_widget(", 1)[1].split(
        "collection_actions=", 1
    )[0]
    embedded_helper_block = PROPERTY_MANAGER_SOURCE.split(
        "def _queue_embedded_refresh_after_reload", 1
    )[1].split("def create_widget", 1)[0]

    assert "from PySide6.QtCore import Qt, QTimer" in PROPERTY_MANAGER_SOURCE
    assert "self._queue_embedded_refresh_after_reload" in create_widget_block
    assert "if embedded" in create_widget_block
    assert "else self._mark_needs_refresh_after_close" in create_widget_block
    assert "self._mark_needs_refresh_after_close()" in embedded_helper_block
    assert "QTimer.singleShot(0, self.refresh_after_close)" in embedded_helper_block
