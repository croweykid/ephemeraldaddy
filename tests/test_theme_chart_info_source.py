from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FACADE_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions.py"
).read_text(encoding="utf-8")
CHART_INFO_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/charts/theme_chart_info.py"
).read_text(encoding="utf-8")
EVIDENCE_SOURCE = (
    ROOT / "ephemeraldaddy/analysis/theme_evidence.py"
).read_text(encoding="utf-8")


def test_chart_info_extension_installs_after_theme_predictions():
    assert "install_theme_chart_info" in FACADE_SOURCE
    assert "_install_theme_predictions(_core)" in FACADE_SOURCE
    assert "_install_theme_chart_info(_theme_predictions)" in FACADE_SOURCE
    assert FACADE_SOURCE.index("_install_theme_predictions(_core)") < FACADE_SOURCE.index(
        "_install_theme_chart_info(_theme_predictions)"
    )


def test_theme_click_uses_stable_family_key_and_standard_chart_info_surface():
    assert "THEME_ROW_KEY_ROLE" in CHART_INFO_SOURCE
    assert 'index.column()) != 0' in CHART_INFO_SOURCE
    assert '_set_chart_info_panel_mode' in CHART_INFO_SOURCE
    assert 'set_mode("chart_info")' in CHART_INFO_SOURCE
    assert 'chart_info_output' in CHART_INFO_SOURCE
    assert 'set_chart_info_html(output, rendered)' in CHART_INFO_SOURCE


def test_theme_chart_info_resolves_taxonomy_at_render_time():
    assert "THEME_FAMILIES[family_key]" in CHART_INFO_SOURCE
    assert "themes_in_family(family_key)" in CHART_INFO_SOURCE
    assert "THEMES[theme_key]" in CHART_INFO_SOURCE
    assert 'family.get("description", "")' in CHART_INFO_SOURCE


def test_theme_evidence_reuses_prominence_activation_resolver():
    assert "prominence._activation_context(chart)" in EVIDENCE_SOURCE
    assert "prominence._activation_for_item(property_name, item, context)" in EVIDENCE_SOURCE
