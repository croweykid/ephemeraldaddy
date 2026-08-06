from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_predictions_panel_has_contextual_panel_subheader_and_reordered_synastry():
    source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
    ).read_text()

    assert 'owner.predictions_panel_subheader = QLabel()' in source
    assert 'pronouns_for_gender(gender, default=THEY_THEM_THEIR)' in source
    assert '"predictions_panel_subheader": (' in source
    assert "Fwiw, here are various factors about" in source
    assert '"traits_prediction_subheader"' not in source
    assert source.index('section_title="Gender Guesser"') < source.index(
        'title="Predicted Synastry"'
    )


def test_traits_status_uses_cached_timestamp_and_centered_ellipsis_loader():
    view_source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
    ).read_text()
    traits_source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions.py"
    ).read_text()

    assert "Current results last updated on" in traits_source
    assert '_set_traits_updated_label(owner, str(metadata.get("updated_at"' in traits_source
    assert "Current results last updated: {timestamp} ♻️" not in traits_source
    assert "start_prediction_loading_ellipsis" in view_source
    assert 'Qt.AlignHCenter | Qt.AlignTop' in view_source
    assert '"Loading trait predictions…"' not in view_source
