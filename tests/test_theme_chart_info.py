from __future__ import annotations

import pytest

from ephemeraldaddy.analysis.theme_evidence import ThemeFactorEvidence
from ephemeraldaddy.analysis.theme_norms import theme_factor_distribution_key
from ephemeraldaddy.gui.features.chart_information import theme_family_presenter as info
from ephemeraldaddy.gui.features.charts import theme_chart_info as adapter


def _install_reference(monkeypatch: pytest.MonkeyPatch) -> None:
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
            "lower": {"label": "Lower Subtheme", "description": ["Lower description."]},
            "higher": {"label": "Higher Subtheme", "description": ["Higher description."]},
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


def _share_norms() -> dict[str, object]:
    return {
        "subtheme_values": {
            "lower": [20.0, 30.0, 40.0],
            "higher": [40.0, 50.0, 60.0],
        },
        "family_values": {"family": [100.0, 100.0, 100.0]},
        "factor_values": {
            theme_factor_distribution_key("bodies", "Sun"): [0.2, 0.6, 0.9],
            theme_factor_distribution_key("signs", "Leo"): [0.2, 0.75, 0.9],
        },
    }


def test_theme_chart_info_renders_chart_shares_percentiles_and_supporting_bullets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_reference(monkeypatch)

    rendered = info.build_theme_family_chart_info_html(
        object(),
        "family",
        subtheme_scores={"lower": 25.0, "higher": 80.0},
        subtheme_shares={"lower": 40.0, "higher": 60.0},
        family_shares={"family": 100.0},
        share_norms=_share_norms(),
    )

    assert f"color:{info.CHART_DATA_HIGHLIGHT_COLOR}" in rendered
    assert "font-weight:700" in rendered
    assert "font-style:italic" in rendered
    assert "An editable family description." in rendered
    assert "Higher Subtheme" in rendered and "60.0% of chart" in rendered
    assert "Lower Subtheme" in rendered and "40.0% of chart" in rendered
    assert rendered.index("Higher Subtheme") < rendered.index("Lower Subtheme")
    assert "<ul" in rendered and "<li" in rendered
    assert "Body: Sun" in rendered
    assert "Sign: Leo" in rendered
    assert "100th p vs DB" in rendered
    assert "50th p vs DB" in rendered
    assert "(100%)" not in rendered
    assert "(75%)" not in rendered
    assert "No configured factors are active above baseline" in rendered


def test_subtheme_chart_info_shows_only_clicked_subtheme(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_reference(monkeypatch)
    monkeypatch.setattr(
        info,
        "calculate_theme_factor_evidence_from_context",
        lambda _context, _keys: {
            "higher": (ThemeFactorEvidence("bodies", "Sun", 1.0, 1.0, 1.0),)
        },
    )

    rendered = info.build_theme_family_chart_info_html(
        object(),
        "family",
        theme_key="higher",
        subtheme_scores={"lower": 25.0, "higher": 80.0},
        subtheme_shares={"lower": 40.0, "higher": 60.0},
        family_shares={"family": 100.0},
        share_norms=_share_norms(),
        activation_context={"available": True},
    )

    assert "Higher Subtheme" in rendered
    assert "Higher description." in rendered
    assert "60.0% of chart" in rendered
    assert "Lower Subtheme" not in rendered
    assert "Macro Theme" not in rendered


def test_theme_chart_info_omits_empty_family_description(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(info, "THEME_FAMILIES", {"family": {"label": "Macro Theme", "description": ""}})
    monkeypatch.setattr(info, "THEMES", {"only": {"label": "Only Subtheme"}})
    monkeypatch.setattr(info, "themes_in_family", lambda _key: {"only": info.THEMES["only"]})
    monkeypatch.setattr(info, "calculate_theme_family_factor_evidence", lambda *_args: {"only": ()})

    rendered = info.build_theme_family_chart_info_html(
        object(),
        "family",
        subtheme_scores={"only": 0.0},
        subtheme_shares={"only": 100.0},
        family_shares={"family": 100.0},
        share_norms={"subtheme_values": {}, "family_values": {}, "factor_values": {}},
    )

    assert "Macro Theme" in rendered
    assert "font-style:italic" not in rendered


class _FakeIndex:
    def __init__(
        self,
        column: int,
        *,
        family_key: str = "family",
        theme_key: str | None = None,
        scope_role: int = 124,
    ) -> None:
        self._column = column
        self._family_key = family_key
        self._theme_key = theme_key
        self._scope_role = scope_role

    def isValid(self) -> bool:  # noqa: N802
        return True

    def column(self) -> int:
        return self._column

    def data(self, role):
        if role == self._scope_role:
            return {
                "family_key": self._family_key,
                "theme_key": self._theme_key,
                "kind": "subtheme" if self._theme_key else "family",
            }
        return self._family_key


def test_only_theme_name_column_opens_selected_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(
        adapter,
        "show_theme_family_chart_info",
        lambda owner, family_key, theme_key=None: calls.append((owner, family_key, theme_key)),
    )
    theme_predictions = type(
        "ThemePredictions",
        (),
        {"THEME_ROW_KEY_ROLE": 123, "THEME_ROW_SCOPE_ROLE": 124},
    )()
    owner = object()

    adapter._handle_theme_prediction_row_clicked(
        owner,
        _FakeIndex(1, theme_key="higher"),
        theme_predictions,
    )
    assert calls == []

    adapter._handle_theme_prediction_row_clicked(
        owner,
        _FakeIndex(0, theme_key="higher"),
        theme_predictions,
    )
    assert calls == [(owner, "family", "higher")]


def test_factor_labels_cover_cross_system_theme_properties():
    assert info._factor_label("houses", 8) == "House 8"
    assert info._factor_label("gates", 55) == "Gate 55"
    assert info._factor_label("channels", "39-55") == "Channel 39-55"
    assert info._factor_label("crosses", "the Sphinx") == "Incarnation Cross: the Sphinx"
    assert info._factor_label("centers", "G") == "G Center"
    assert info._factor_label("profiles", "1/3") == "Profile 1/3"
    assert info._factor_label("authorities", "Emotional") == "Emotional Authority"
    assert info._factor_label("bazisigns", "dragon") == "BaZi: Dragon"
