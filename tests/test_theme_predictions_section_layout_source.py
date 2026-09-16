from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAYOUT_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/charts/theme_predictions_section_layout.py"
).read_text(encoding="utf-8")
TRAIT_FACADE_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions.py"
).read_text(encoding="utf-8")


def test_theme_layout_adapter_is_installed_after_runtime_and_chart_info():
    assert "install_theme_predictions_section_layout" in TRAIT_FACADE_SOURCE
    assert "_install_theme_predictions_section_layout(_theme_predictions)" in TRAIT_FACADE_SOURCE
    assert TRAIT_FACADE_SOURCE.index("_install_theme_prediction_runtime(_theme_predictions)") < TRAIT_FACADE_SOURCE.index(
        "_install_theme_predictions_section_layout(_theme_predictions)"
    )
    assert TRAIT_FACADE_SOURCE.index("_install_theme_chart_info(_theme_predictions)") < TRAIT_FACADE_SOURCE.index(
        "_install_theme_predictions_section_layout(_theme_predictions)"
    )


def test_theme_dropdown_defaults_to_chart_dominance_and_combines_db_comparison():
    assert 'combo.addItem("DOMINANT IN CHART", _CHART_MODE)' in LAYOUT_SOURCE
    assert 'combo.addItem("DOMINANT VS DB", _DB_MODE)' in LAYOUT_SOURCE
    assert "combo.setCurrentIndex(0)" in LAYOUT_SOURCE
    assert 'QLabel("Above DB Avg", content)' in LAYOUT_SOURCE
    assert 'QLabel("Below DB Avg", content)' in LAYOUT_SOURCE


def test_theme_chart_share_column_is_fixed_while_theme_name_stretches():
    assert "header.setSectionResizeMode(0, QHeaderView.Stretch)" in LAYOUT_SOURCE
    assert "header.setSectionResizeMode(1, QHeaderView.Fixed)" in LAYOUT_SOURCE
    assert 'metrics.horizontalAdvance("0000000000")' in LAYOUT_SOURCE
    assert 'metrics.horizontalAdvance("% of chart")' in LAYOUT_SOURCE


def test_theme_caption_precedes_right_aligned_controls_and_export_is_live():
    assert "layout.insertWidget(0, caption)" in LAYOUT_SOURCE
    assert "layout.insertWidget(1, header_row)" in LAYOUT_SOURCE
    assert "font.setItalic(True)" in LAYOUT_SOURCE
    assert "configure_share_export_icon_button(" in LAYOUT_SOURCE
    assert "export_button.clicked.connect(lambda: _export_themes(owner))" in LAYOUT_SOURCE
    assert '"share_icon2.png"' in LAYOUT_SOURCE


def test_db_fallback_status_is_kept_in_the_caption_slot():
    assert "No themes are at least" in LAYOUT_SOURCE
    assert "showing the five closest differences" in LAYOUT_SOURCE
    assert "_set_caption(owner, _fallback_caption(owner))" in LAYOUT_SOURCE
