from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_predictions_panel_has_contextual_panel_subheader_and_reordered_synastry():
    source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
    ).read_text()

    assert 'owner.predictions_panel_subheader = QLabel()' in source
    assert 'pronouns_for_gender(gender, default=THEY_THEM_THEIR)' in source
    assert "pronouns.possessive_determiner" in source
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


def test_traits_timestamp_resets_before_every_cache_lookup():
    traits_source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions.py"
    ).read_text()
    render_source = traits_source.split("def render_traits_predictions", 1)[1]

    reset_index = render_source.index("_set_traits_updated_label(owner, None)")
    cache_lookup_index = render_source.index("trait_metadata_for_chart(")
    assert reset_index < cache_lookup_index


def test_predictions_subheader_refreshes_when_gender_changes():
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    connection = (
        "self.gender_combo.currentIndexChanged.connect(\n"
        "            self._update_observations_relationship_subheaders\n"
        "        )"
    )
    assert connection in app_source


def test_pronoun_possessive_determiners_are_attributive():
    from ephemeraldaddy.semantics_formatting import pronouns_for_gender

    assert pronouns_for_gender("F").possessive_determiner == "her"
    assert pronouns_for_gender("M").possessive_determiner == "his"
    assert pronouns_for_gender("AFAB-NB").possessive_determiner == "their"
