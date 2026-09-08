from pathlib import Path

from ephemeraldaddy.gui.features.charts.right_panel_state import (
    SECTION_EXPANSION_SETTINGS_PREFIX,
    save_section_expanded,
    saved_section_expanded,
)


class _Settings:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def contains(self, key):
        return key in self.values

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value


class _Owner:
    def __init__(self, settings):
        self._settings = settings


def _key(panel, section):
    return f"{SECTION_EXPANSION_SETTINGS_PREFIX}/{panel}/{section}"


def test_new_chart_editor_sections_default_to_collapsed():
    owner = _Owner(_Settings())

    assert saved_section_expanded(owner, "observations", "typology") is False
    assert saved_section_expanded(owner, "predictions", "ocean") is False


def test_section_expansion_choice_survives_a_new_owner_session():
    settings = _Settings()
    save_section_expanded(_Owner(settings), "observations", "typology", True)

    restored_owner = _Owner(settings)
    assert saved_section_expanded(restored_owner, "observations", "typology") is True

    save_section_expanded(restored_owner, "observations", "typology", False)
    assert settings.values[_key("observations", "typology")] is False
    assert saved_section_expanded(_Owner(settings), "observations", "typology") is False


def test_qsettings_string_booleans_are_coerced_safely():
    owner = _Owner(
        _Settings(
            {
                _key("predictions", "ocean"): "true",
                _key("predictions", "enneagram"): "false",
            }
        )
    )

    assert saved_section_expanded(owner, "predictions", "ocean") is True
    assert saved_section_expanded(owner, "predictions", "enneagram") is False


def test_cached_traits_hydration_does_not_force_open_the_user_collapsed_section():
    source = (
        Path(__file__).parents[1]
        / "ephemeraldaddy/gui/features/charts/trait_predictions.py"
    ).read_text()
    render_source = source.split("def render_traits_predictions", 1)[1]
    cached_branch = render_source.split("if isinstance(cached_metadata, dict):", 1)[1].split(
        "was_expanded = _traits_prediction_section_expanded(owner)", 1
    )[0]

    assert "set_section_checked" not in cached_branch
    assert "_set_traits_prediction_section_expanded" not in cached_branch
