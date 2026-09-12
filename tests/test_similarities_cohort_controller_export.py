from __future__ import annotations

from types import SimpleNamespace

from ephemeraldaddy.gui.features.charts.similarities import cohort_controller


def test_export_json_snapshots_current_selected_chart_uids(monkeypatch) -> None:
    captured: dict[str, object] = {}
    host = SimpleNamespace(
        # The visible/persistent UID accessor can lag the row selection that
        # actually drove Similarities Analysis; export must use the latter.
        _selected_chart_uids=lambda: ["UID-A"],
        _selected_local_row_ids=lambda: [3, 1, 2, 99],
        _exclude_similarities_placeholder_local_row_ids=lambda ids: [
            chart_id for chart_id in ids if chart_id != 99
        ],
        _chart_uids_by_local_row_id=lambda ids: {
            chart_id: {1: " uid-b ", 2: "UID-A", 3: "uid-a"}[chart_id]
            for chart_id in ids
        },
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


def test_gender_distribution_passes_empty_matches_when_all_rows_fail_delta() -> None:
    captured: dict[str, object] = {}

    def render(_list, _toggle, matches, **kwargs) -> None:
        captured["matches"] = matches
        captured.update(kwargs)

    controller = object.__new__(cohort_controller.SimilaritiesController)
    controller.host = SimpleNamespace(_set_similarities_section_matches=render)
    controller.gender_distribution_toggle = object()
    controller.gender_distribution_list = object()
    controller._cohort_gender_distribution = {
        "counts": {"Female": 5, "Male": 5},
        "databaseCounts": {"Female": 50, "Male": 50},
        "total": 10,
        "databaseTotal": 100,
    }

    controller._render_gender_distribution()

    assert captured["matches"] == []
