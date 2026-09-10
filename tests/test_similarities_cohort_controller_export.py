from __future__ import annotations

from types import SimpleNamespace

from ephemeraldaddy.gui.features.charts.similarities import cohort_controller


def test_export_json_snapshots_current_selected_chart_uids(monkeypatch) -> None:
    captured: dict[str, object] = {}
    host = SimpleNamespace(
        _selected_chart_uids=lambda: [" uid-b ", "UID-A", "uid-a", ""],
        _reactivate_database_view=None,
    )
    controller = object.__new__(cohort_controller.SimilaritiesController)
    controller.host = host
    controller.export_sections = []
    controller._cohort_chart_uids = []
    controller._cohort_gender_distribution = None
    controller.capture_legacy_attributes = lambda: None

    def capture_export(parent, export_sections, **kwargs) -> None:
        captured["parent"] = parent
        captured["export_sections"] = export_sections
        captured.update(kwargs)

    monkeypatch.setattr(
        cohort_controller,
        "export_similarities_analysis_json_dialog",
        capture_export,
    )

    controller.export_json()

    assert controller._cohort_chart_uids == ["UID-A", "UID-B"]
    assert captured["sample_uids"] == ["UID-A", "UID-B"]
