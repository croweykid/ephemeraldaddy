from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_tag_chip_style_uses_universal_nowrap_pills_with_three_pixel_gap():
    style_source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text(encoding="utf-8")

    assert "TAG_CHIP_GAP_PX = 3" in style_source
    assert "def configure_tag_chip_label" in style_source
    assert "label.setWordWrap(False)" in style_source
    assert "label.setTextFormat(Qt.RichText)" in style_source
    assert '"white-space:nowrap;"' in style_source
    assert '"border-radius:999px;"' in style_source
    assert 'f"margin:2px {TAG_CHIP_GAP_PX}px 2px 0;"' in style_source
    assert 'f"margin-left:{TAG_CHIP_GAP_PX}px;"' in style_source


def test_batch_and_chart_view_assigned_tag_lists_use_universal_chip_label_style():
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    chart_view_source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
    ).read_text(encoding="utf-8")
    tagging_source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/charts/tagging.py"
    ).read_text(encoding="utf-8")

    assert "configure_tag_chip_label(self.batch_tags_selection_label)" in app_source
    assert "self.batch_tags_selection_label.setText(\"\".join(chips))" in app_source
    assert "configure_tag_chip_label(owner.chart_tags_selection_label)" in chart_view_source
    assert "owner.chart_tags_selection_label.setText(\"\".join(chips))" in chart_view_source
    assert "configure_tag_chip_label(preview_label)" in tagging_source
    assert "preview_label.setText(\"\".join(chips))" in tagging_source
