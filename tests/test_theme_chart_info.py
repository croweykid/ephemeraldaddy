from __future__ import annotations

import pytest

from ephemeraldaddy.analysis.theme_evidence import ThemeFactorEvidence
from ephemeraldaddy.gui.features.charts import theme_chart_info as info


def test_theme_chart_info_renders_header_description_scores_and_supporting_bullets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        info,
        "THEME_FAMILIES",
        {
            "family": {
                "label": "Macro Theme",
                "description": "An editable family description.",
            }
        },
    )
    monkeypatch.setattr(
        info,
        "THEMES",
        {
            "lower": {"label": "Lower Subtheme"},
            "higher": {"label": "Higher Subtheme"},
        },
    )
    monkeypatch.setattr(
        info,
        "themes_in_family",
        lambda family_key: {"lower": info.THEMES["lower"], "higher": info.THEMES["higher"]}
        if family_key == "family"
        else {},
    )
    monkeypatch.setattr(
        info,
        "calculate_theme_family_factor_evidence",
        lambda _chart, _family_key: {
            "lower": (),
            "higher": (
                ThemeFactorEvidence("bodies", "Sun", 1.0, 1.0, 1.0),
                ThemeFactorEvidence("signs", "Leo", 0.75, 1.0, 0.75),
            ),
        },
    )

    rendered = info.build_theme_family_chart_info_html(
        object(),
        "family",
        subtheme_scores={"lower": 25.0, "higher": 80.0},
    )

    assert f"color:{info.CHART_DATA_HIGHLIGHT_COLOR}" in rendered
    assert "font-weight:700" in rendered
    assert "font-style:italic" in rendered
    assert "An editable family description." in rendered
    assert "Higher Subtheme" in rendered and "80.0%" in rendered
    assert "Lower Subtheme" in rendered and "25.0%" in rendered
    assert rendered.index("Higher Subtheme") < rendered.index("Lower Subtheme")
    assert "<ul" in rendered and "<li" in rendered
    assert "Body: Sun" in rendered
    assert "Sign: Leo" in rendered
    assert "(100%)" in rendered
    assert "(75%)" in rendered
    assert "No configured factors are active above baseline" in rendered


def test_theme_chart_info_omits_empty_family_description(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(info, "THEME_FAMILIES", {"family": {"label": "Macro Theme", "description": ""}})
    monkeypatch.setattr(info, "THEMES", {"only": {"label": "Only Subtheme"}})
    monkeypatch.setattr(info, "themes_in_family", lambda _key: {"only": info.THEMES["only"]})
    monkeypatch.setattr(info, "calculate_theme_family_factor_evidence", lambda *_args: {"only": ()})

    rendered = info.build_theme_family_chart_info_html(
        object(), "family", subtheme_scores={"only": 0.0}
    )

    assert "Macro Theme" in rendered
    assert "font-style:italic" not in rendered


class _FakeIndex:
    def __init__(self, column: int, family_key: str = "family") -> None:
        self._column = column
        self._family_key = family_key

    def isValid(self) -> bool:  # noqa: N802
        return True

    def column(self) -> int:
        return self._column

    def data(self, _role):
        return self._family_key


def test_only_theme_name_column_opens_chart_info(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(info, "show_theme_family_chart_info", lambda owner, key: calls.append((owner, key)))
    theme_predictions = type("ThemePredictions", (), {"THEME_ROW_KEY_ROLE": 123})()
    owner = object()

    info._handle_theme_prediction_row_clicked(owner, _FakeIndex(1), theme_predictions)
    assert calls == []

    info._handle_theme_prediction_row_clicked(owner, _FakeIndex(0), theme_predictions)
    assert calls == [(owner, "family")]


def test_factor_labels_cover_cross_system_theme_properties():
    assert info._factor_label("houses", 8) == "House 8"
    assert info._factor_label("gates", 55) == "Gate 55"
    assert info._factor_label("channels", "39-55") == "Channel 39–55"
    assert info._factor_label("crosses", "the Sphinx") == "Incarnation Cross: the Sphinx"
    assert info._factor_label("centers", "G") == "G Center"
    assert info._factor_label("profiles", "1/3") == "Profile 1/3"
    assert info._factor_label("authorities", "Emotional") == "Emotional Authority"
    assert info._factor_label("bazisigns", "dragon") == "BaZi: Dragon"
