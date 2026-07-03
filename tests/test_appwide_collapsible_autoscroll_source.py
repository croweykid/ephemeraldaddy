from pathlib import Path

STYLE_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/style.py").read_text()


def test_collapsible_header_installs_appwide_autoscroll_handler():
    assert "collapsible_header_autoscroll_installed" in STYLE_SOURCE
    assert "toggle.toggled.connect" in STYLE_SOURCE
    assert "_schedule_collapsible_section_autoscroll(header_toggle) if checked else None" in STYLE_SOURCE


def test_collapsible_autoscroll_targets_nearest_scroll_area_section_bottom():
    assert "def _scroll_collapsible_section_bottom_into_view" in STYLE_SOURCE
    assert "def _nearest_scroll_area" in STYLE_SOURCE
    assert "isinstance(parent, QScrollArea)" in STYLE_SOURCE
    assert "section.mapTo(scroll_widget, QPoint(0, section.height())).y()" in STYLE_SOURCE
    assert "current_value = scrollbar.value()" in STYLE_SOURCE
    assert "viewport_bottom_y = current_value + viewport.height()" in STYLE_SOURCE
    assert "if section_bottom_y <= viewport_bottom_y:" in STYLE_SOURCE
    assert "target_value = section_bottom_y - viewport.height()" in STYLE_SOURCE
    assert "max(current_value, min(target_value, scrollbar.maximum()))" in STYLE_SOURCE


def test_collapsible_autoscroll_waits_for_layout_and_lazy_refreshes():
    assert "QTimer.singleShot(" in STYLE_SOURCE
    assert "0," in STYLE_SOURCE
    assert "50," in STYLE_SOURCE
