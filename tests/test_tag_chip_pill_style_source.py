from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_tag_chip_style_uses_universal_wrapping_list_with_nowrap_pills_and_three_pixel_gap():
    style_source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text(encoding="utf-8")

    assert "TAG_CHIP_GAP_PX = 3" in style_source
    assert "def configure_tag_chip_label" in style_source
    assert 're.sub(r"\\s+", "&nbsp;", html.escape(str(tag or "")))' in style_source
    assert '"</span> "' in style_source
    assert "label.setWordWrap(True)" in style_source
    assert "label.setTextFormat(Qt.RichText)" in style_source
    assert '"white-space:nowrap;"' in style_source
    assert '"border-radius:999px;"' in style_source
    assert 'f"margin:2px {TAG_CHIP_GAP_PX}px 2px 0;"' in style_source
    assert 'f"margin-left:{TAG_CHIP_GAP_PX}px;"' in style_source


def test_batch_and_chart_info_assigned_tag_lists_use_universal_chip_label_style():
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    chart_view_source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
    ).read_text(encoding="utf-8")
    tagging_source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/charts/tagging.py"
    ).read_text(encoding="utf-8")

    assert "configure_tag_chip_label(self.batch_tags_selection_label)" in app_source
    assert "self.batch_tags_selection_label.setText(\"\".join(chips))" in app_source
    assert 'chart_tags_toggle_button = QPushButton("🏷️")' in chart_view_source
    assert 'lambda: owner._set_chart_info_panel_mode("tags")' in chart_view_source
    assert 'has_content_by_mode[mode] = bool(getattr(owner, "_chart_tags_current", []))' in chart_view_source
    assert "configure_tag_chip_label(owner.chart_tags_selection_label)" in chart_view_source
    assert "owner.chart_tags_selection_label.setText(\"\".join(chips))" in chart_view_source
    assert "configure_tag_chip_label(preview_label)" in tagging_source
    assert "preview_label.setText(\"\".join(chips))" in tagging_source


def test_chart_tags_live_in_chart_info_stack_not_subjective_notes_panel():
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")

    assert "self.chart_tags_panel_widget = QWidget()" in app_source
    assert "self.chart_info_content_stack.addWidget(self.chart_tags_panel_widget)" in app_source
    assert '"tags": 2' in app_source
    assert "tags_box = QFrame()" not in app_source
    assert "self.tags_panel_toggle" not in app_source


def test_event_chart_save_paths_persist_visible_chart_tags():
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")

    assert "chart.tags = [] if is_event_chart else get_chart_view_tags(self)" not in app_source
    assert app_source.count("chart.tags = get_chart_view_tags(self)") >= 2
