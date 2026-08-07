from pathlib import Path

from ephemeraldaddy.gui.features.database_view.analytics.optional_modules import (
    database_analytics_section_is_visible,
)

APP_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text()


def _lookup(values):
    return lambda key: values.get(key, True)


def test_enneagram_analytics_follows_enneagram_predictor_module():
    assert database_analytics_section_is_visible(
        "enneagram",
        configured_visible=True,
        visibility=_lookup({"predictions.enneagram": True}),
    )
    assert not database_analytics_section_is_visible(
        "enneagram",
        configured_visible=True,
        visibility=_lookup({"predictions.enneagram": False}),
    )


def test_fantasy_archetypes_follows_fantasy_rpg_typing_module():
    assert database_analytics_section_is_visible(
        "species_distribution",
        configured_visible=True,
        visibility=_lookup({"database_metrics_visibility.species_distribution": True}),
    )
    assert not database_analytics_section_is_visible(
        "species_distribution",
        configured_visible=True,
        visibility=_lookup({"database_metrics_visibility.species_distribution": False}),
    )


def test_configured_hidden_state_still_wins_for_optional_sections():
    assert not database_analytics_section_is_visible(
        "enneagram",
        configured_visible=False,
        visibility=_lookup({"predictions.enneagram": True}),
    )


def test_database_analytics_widgets_apply_effective_visibility_immediately():
    assert "section.setVisible(self._is_database_metrics_section_visible(section_key))" in APP_SOURCE
    assert 'self._set_database_metrics_section_expanded("enneagram", False)' in APP_SOURCE
    assert "self._sync_database_metrics_section_visibility()" in APP_SOURCE
