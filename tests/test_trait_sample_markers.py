from __future__ import annotations

import html
from types import ModuleType, SimpleNamespace

from ephemeraldaddy.gui.features.charts import trait_sample_markers


def _fake_core() -> tuple[ModuleType, dict[str, object]]:
    core = ModuleType("fake_trait_predictions_core")
    captured: dict[str, object] = {}

    def rows_from_metadata(_traits, _metadata):
        return [
            {"name": "Ascribed", "likelihood": 90.0, "deviation": 40.0},
            {"name": "Other", "likelihood": 70.0, "deviation": 20.0},
        ]

    def rank_row(name, percentage, *, color, db_average, db_deviation):
        escaped = html.escape(name)
        return f"<a href='trait:{escaped}'>{escaped}</a>"

    def show_trait_chart_info(_owner, name):
        captured["chart_info_name"] = name

    def apply_metadata(owner, traits, metadata, *, prefix_html=""):
        captured["rows"] = core._trait_prediction_rows_from_metadata(traits, metadata)
        captured["rank_html"] = core._trait_rank_row(
            "Ascribed",
            90.0,
            color="#cc99ff",
            db_average=50.0,
            db_deviation=40.0,
        )
        captured["prefix_html"] = prefix_html
        captured["owner"] = owner

    core._trait_prediction_rows_from_metadata = rows_from_metadata
    core._trait_rank_row = rank_row
    core._show_trait_chart_info = show_trait_chart_info
    core._apply_traits_prediction_metadata = apply_metadata
    return core, captured


def test_marker_installer_marks_table_and_html_without_changing_trait_target(monkeypatch) -> None:
    core, captured = _fake_core()
    owner = SimpleNamespace(_traits_prediction_chart=SimpleNamespace(chart_uid="UID-1"))

    monkeypatch.setattr(
        trait_sample_markers,
        "ascribed_trait_names_for_chart",
        lambda chart, traits: {"Ascribed"},
    )
    monkeypatch.setattr(
        trait_sample_markers,
        "predictions_exclude_ascribed_enabled",
        lambda owner: False,
    )

    trait_sample_markers.install_trait_sample_markers(core)
    core._apply_traits_prediction_metadata(owner, [], {}, prefix_html="prefix")

    rows = captured["rows"]
    assert rows[0]["name"] == "🧚 Ascribed"
    assert rows[1]["name"] == "Other"
    assert captured["rank_html"] == "<a href='trait:Ascribed'>🧚 Ascribed</a>"

    core._show_trait_chart_info(owner, "🧚 Ascribed")
    assert captured["chart_info_name"] == "Ascribed"


def test_marker_installer_emits_no_marker_when_exclusion_policy_is_enabled(monkeypatch) -> None:
    core, captured = _fake_core()
    owner = SimpleNamespace(_traits_prediction_chart=SimpleNamespace(chart_uid="UID-1"))

    monkeypatch.setattr(
        trait_sample_markers,
        "ascribed_trait_names_for_chart",
        lambda chart, traits: {"Ascribed"},
    )
    monkeypatch.setattr(
        trait_sample_markers,
        "predictions_exclude_ascribed_enabled",
        lambda owner: True,
    )

    trait_sample_markers.install_trait_sample_markers(core)
    core._apply_traits_prediction_metadata(owner, [], {})

    assert captured["rows"][0]["name"] == "Ascribed"
    assert captured["rank_html"] == "<a href='trait:Ascribed'>Ascribed</a>"
