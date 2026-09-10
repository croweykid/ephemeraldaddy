from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THEME_UI_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/charts/theme_predictions.py"
).read_text(encoding="utf-8")
TRAIT_FACADE_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions.py"
).read_text(encoding="utf-8")
SNAPSHOT_SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/charts/prediction_norms_snapshot.py"
).read_text(encoding="utf-8")
DEFAULT_SNAPSHOT = json.loads(
    (ROOT / "ephemeraldaddy/analysis/default_prediction_norms.json").read_text(
        encoding="utf-8"
    )
)


def test_traits_facade_installs_theme_predictions_extension():
    assert "install_theme_predictions" in TRAIT_FACADE_SOURCE
    assert "_install_theme_predictions(_core)" in TRAIT_FACADE_SOURCE


def test_themes_section_uses_stable_family_key_role_and_traits_table_shape():
    assert 'title="Themes"' in THEME_UI_SOURCE
    assert 'THEME_ROW_KEY_ROLE = Qt.UserRole + 31' in THEME_UI_SOURCE
    assert 'return str(row.get("key", ""))' in THEME_UI_SOURCE
    assert '_HEADERS = ("Theme", "%", "vs DB")' in THEME_UI_SOURCE
    assert 'addItem("ABOVE AVG", "above")' in THEME_UI_SOURCE
    assert 'addItem("BELOW AVG", "below")' in THEME_UI_SOURCE
    assert "THEME_DEVIATION_ASSIGNMENT_THRESHOLD" in THEME_UI_SOURCE


def test_themes_are_inserted_from_traits_construction_before_later_prediction_sections():
    assert "_ensure_theme_predictions_section(owner, table)" in THEME_UI_SOURCE
    assert "configure_traits_prediction_table = configure_traits_prediction_table" in THEME_UI_SOURCE


def test_theme_render_uses_selected_static_prediction_norm_snapshot():
    render_source = THEME_UI_SOURCE.split("def render_theme_predictions", 1)[1].split(
        "def _theme_predictions_have_rendered_content", 1
    )[0]
    assert "snapshot = load_prediction_norms_snapshot()" in render_source
    assert "theme_family_snapshot_averages(snapshot)" in render_source
    assert "calculate_theme_subtheme_scores(chart)" in render_source
    assert "calculate_theme_family_scores(" in render_source
    assert "_theme_prediction_subtheme_scores" in render_source
    assert "_theme_prediction_family_scores" in render_source


def test_theme_snapshot_baselines_are_native_full_db_norm_payload_fields():
    assert "calculate_database_theme_family_averages(charts)" in SNAPSHOT_SOURCE
    assert '"theme_family_raw_averages"' in SNAPSHOT_SOURCE
    assert '"theme_family_definition_signature"' in SNAPSHOT_SOURCE
    assert DEFAULT_SNAPSHOT["theme_family_raw_averages"] == {}
    assert DEFAULT_SNAPSHOT["theme_family_definition_signature"] == ""


def test_themes_have_independent_prediction_render_token_tracking():
    assert "_theme_prediction_last_render_chart_token" in THEME_UI_SOURCE
    assert "_render_theme_predictions" in THEME_UI_SOURCE
    assert "schedule_chart_render_for_active_right_panel" in THEME_UI_SOURCE
