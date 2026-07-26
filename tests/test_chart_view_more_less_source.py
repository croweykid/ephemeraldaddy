from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_chart_analytics_more_info_link_toggles_details_and_link_text():
    source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/controllers/main_window.py"
    ).read_text(encoding="utf-8")

    assert "expanded = not container.isVisible()" in source
    assert "container.setVisible(expanded)" in source
    assert 'f\'{"show less" if expanded else "more info..."}</a>\'' in source
    assert "link.setVisible(False)" not in source


def test_prediction_more_links_offer_show_less_and_restore_summaries():
    source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/charts/dnd_predictions.py"
    ).read_text(encoding="utf-8")

    assert '_dnd_label_link("Show Less", "dnd-species-less:0")' in source
    assert '_dnd_label_link("Show Less", "dnd-class-less:0")' in source
    assert 'prefix in {"dnd-species-less", "dnd-class-less"}' in source
    assert "summary_html = build_dnd_top_three_summary_html(" in source


def test_euphonics_details_button_uses_show_less_while_expanded():
    source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
    ).read_text(encoding="utf-8")

    assert 'setText("Show Less" if checked else "Details")' in source
