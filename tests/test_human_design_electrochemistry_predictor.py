from ephemeraldaddy.analysis.human_design_synastry import (
    HD_SYNASTRY_GENDER_METHOD_IDENTITY,
    HD_SYNASTRY_GENDER_METHOD_SEX,
    HumanDesignSynastryCandidate,
    filter_hd_synastry_candidates,
    human_design_electrochemistry_score,
    normalize_gates,
    rank_human_design_synastry,
)


def _hd_electrochemistry_module():
    import pytest

    return pytest.importorskip(
        "ephemeraldaddy.gui.features.predictions.hd_electrochemistry",
        exc_type=ImportError,
    )


def candidate(uid, gates, name="Candidate"):
    return HumanDesignSynastryCandidate(uid, name, None, frozenset(gates))


def gendered_candidate(uid, gender):
    return HumanDesignSynastryCandidate(uid, uid, None, frozenset({47}), gender=gender)


def test_rank_prioritizes_new_completed_channels_then_center_bonus():
    # Gate 64 can be completed by 47; gate 61 can be completed by 24.
    results = rank_human_design_synastry(
        "SOURCE",
        {64, 61},
        [
            candidate("ONE", {47}, "One channel"),
            candidate("TWO", {47, 24}, "Two channels"),
        ],
    )

    assert [match.chart_uid for match in results] == ["TWO", "ONE"]
    assert results[0].completed_channels == 2
    assert results[0].defined_centers == 2


def test_electrochemistry_score_counts_only_cross_chart_channel_completions():
    score, maximum = human_design_electrochemistry_score(
        {64, 61, 24},
        {47},
    )

    assert score == 1
    assert maximum == 36


def test_rank_excludes_source_and_is_deterministic_for_ties():
    results = rank_human_design_synastry(
        "source",
        {64},
        [
            candidate("SOURCE", {47}, "Self"),
            candidate("B", {47}, "Zed"),
            candidate("A", {47}, "Alpha"),
        ],
    )

    assert [match.chart_uid for match in results] == ["A", "B"]


def test_candidate_natal_channels_are_not_counted_as_synastry_completions():
    results = rank_human_design_synastry(
        "SOURCE",
        {64},
        [
            candidate("NATAL", {61, 24, 17, 62}, "Unrelated natal channels"),
            candidate("CROSS", {47}, "Cross-chart completion"),
        ],
    )

    assert [match.chart_uid for match in results] == ["CROSS", "NATAL"]
    assert results[0].completed_channels == 1
    assert results[1].completed_channels == 0


def test_normalize_gates_ignores_invalid_cache_values():
    assert normalize_gates(["1", 64, 0, 65, "oops", None]) == frozenset({1, 64})


def test_synastry_derives_missing_gate_cache(monkeypatch):
    hd_electrochemistry = _hd_electrochemistry_module()
    chart = type("Chart", (), {"human_design_gates": []})()
    monkeypatch.setattr(
        hd_electrochemistry,
        "derive_human_design_profile",
        lambda _chart: ([64, 47], [1], ["47-64"], "Projector"),
    )

    assert hd_electrochemistry.resolve_hd_electrochemistry_gates(chart) == frozenset({47, 64})
    assert chart.human_design_gates == [47, 64]


def test_synastry_hypothetical_warning_includes_chart_name():
    hd_electrochemistry = _hd_electrochemistry_module()
    chart = type(
        "Chart",
        (),
        {"name": "A & B", "birthtime_unknown": True, "retcon_time_used": True},
    )()

    subheader = hd_electrochemistry.hd_electrochemistry_subheader(chart)

    assert "Since A &amp; B's birth time is hypothetical" in subheader
    assert "results may be dodgier than usual" in subheader


def test_synastry_known_time_uses_standard_subheader():
    hd_electrochemistry = _hd_electrochemistry_module()
    chart = type("Chart", (), {"name": "Known", "birthtime_unknown": False})()

    assert (
        hd_electrochemistry.hd_electrochemistry_subheader(chart)
        == hd_electrochemistry.HD_ELECTROCHEMISTRY_SUBHEADER
    )


def test_synastry_gender_filter_can_group_by_assigned_sex_or_gender_identity():
    candidates = [
        gendered_candidate("MALE", "M"),
        gendered_candidate("FEMALE", "female"),
        gendered_candidate("AMAB_F", "AMAB-F"),
        gendered_candidate("AFAB_M", "AFAB-M"),
        gendered_candidate("AFAB_NB", "AFAB-NB"),
        gendered_candidate("AMAB_NB", "AMAB-NB"),
        gendered_candidate("BLANK", None),
    ]

    assert [
        item.chart_uid
        for item in filter_hd_synastry_candidates(
            candidates, "male", HD_SYNASTRY_GENDER_METHOD_SEX
        )
    ] == ["MALE", "AMAB_F", "AMAB_NB"]
    assert [
        item.chart_uid
        for item in filter_hd_synastry_candidates(
            candidates, "female", HD_SYNASTRY_GENDER_METHOD_SEX
        )
    ] == ["FEMALE", "AFAB_M", "AFAB_NB"]
    assert [
        item.chart_uid
        for item in filter_hd_synastry_candidates(
            candidates, "male", HD_SYNASTRY_GENDER_METHOD_IDENTITY
        )
    ] == ["MALE", "AFAB_M"]
    assert [
        item.chart_uid
        for item in filter_hd_synastry_candidates(
            candidates, "female", HD_SYNASTRY_GENDER_METHOD_IDENTITY
        )
    ] == ["FEMALE", "AMAB_F"]
    assert filter_hd_synastry_candidates(candidates, "all") == candidates


def test_synastry_gender_filter_defaults_to_assigned_at_birth_sex():
    candidates = [
        gendered_candidate("MALE", "M"),
        gendered_candidate("AMAB_F", "AMAB-F"),
        gendered_candidate("AFAB_M", "AFAB-M"),
    ]

    assert [item.chart_uid for item in filter_hd_synastry_candidates(candidates, "male")] == [
        "MALE",
        "AMAB_F",
    ]


def test_synastry_gender_filter_is_part_of_render_token():
    hd_electrochemistry = _hd_electrochemistry_module()
    chart = type("Chart", (), {"chart_uid": "UID", "human_design_gates": [47]})()
    owner = type("Owner", (), {"hd_electrochemistry_gender_filter": "all"})()
    all_token = hd_electrochemistry.hd_electrochemistry_render_token(owner, chart)

    owner.hd_electrochemistry_gender_filter = "female"

    assert hd_electrochemistry.hd_electrochemistry_render_token(owner, chart) != all_token


def test_synastry_collection_filter_is_part_of_render_token():
    hd_electrochemistry = _hd_electrochemistry_module()
    chart = type("Chart", (), {"chart_uid": "UID", "human_design_gates": [47]})()
    owner = type(
        "Owner",
        (),
        {"hd_electrochemistry_gender_filter": "all", "hd_electrochemistry_collection_filter": "all"},
    )()
    all_token = hd_electrochemistry.hd_electrochemistry_render_token(owner, chart)

    owner.hd_electrochemistry_collection_filter = "personal"

    assert hd_electrochemistry.hd_electrochemistry_render_token(owner, chart) != all_token


def test_right_panel_checks_synastry_revision_before_reranking():
    from pathlib import Path

    source = Path("ephemeraldaddy/gui/features/controllers/chart_right_panel.py").read_text()
    predictions_branch = source.split('if active_panel == "predictions":', 1)[1].split(
        'if active_panel == "time_sensitivity":', 1
    )[0]

    stale_check = predictions_branch.index("hd_electrochemistry_predictions_are_current")
    render_call = predictions_branch.index("render_hd_electrochemistry(chart)")
    assert stale_check < render_call
    assert "if predictions_are_current and hd_electrochemistry_is_current:" in predictions_branch


def test_predicted_synastry_builds_gender_radios_with_refresh_callback():
    from pathlib import Path

    source = Path("ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()
    synastry_branch = source.split('title="Predicted Synastry"', 1)[1].split(
        'title="Traits"', 1
    )[0]

    assert 'addItem("🪷HD Electrochemistry", "hd_electrochemistry")' in synastry_branch

    assert '(("All", "all"), ("Male", "male"), ("Female", "female"))' in synastry_branch
    assert "QRadioButton(label)" in synastry_branch
    assert "on_hd_electrochemistry_gender_filter_changed(owner, selected, checked)" in synastry_branch
    assert 'QLabel("Collection:")' in synastry_branch
    assert "populate_hd_electrochemistry_collection_combo" in synastry_branch
    assert "on_hd_electrochemistry_collection_changed" in synastry_branch


def test_synastry_candidates_carry_collection_metadata():
    item = HumanDesignSynastryCandidate(
        "UID", "Name", None, frozenset({47}), source="public", chart_type="public"
    )

    assert item.source == "public"
    assert item.chart_type == "public"


def test_chart_calculation_settings_builds_gender_method_radios():
    from pathlib import Path

    source = Path("ephemeraldaddy/gui/app.py").read_text()
    settings_branch = source.split('"Chart Calculation Methods"', 1)[1].split(
        '"Data Visualization"', 1
    )[0]

    assert 'QLabel("For gendered results, use:")' in settings_branch
    assert '"Assigned-at-birth sex"' in settings_branch
    assert '"Gender identity"' in settings_branch
    assert "on_gendered_results_method_changed(\n                    self._owner_window()" in settings_branch


def test_synastry_filtered_empty_state_is_distinct_from_empty_database():
    from pathlib import Path

    source = Path("ephemeraldaddy/gui/features/predictions/hd_electrochemistry.py").read_text()
    render_branch = source.split("def render_hd_electrochemistry_predictions", 1)[1].split(
        "def on_hd_electrochemistry_gender_filter_changed", 1
    )[0]

    filter_empty_index = render_branch.index('if gender_filter != "all" and other_candidates_are_available:')
    generic_empty_index = render_branch.index(
        'label.setText("No other charts with Human Design gate data are available.")'
    )
    assert filter_empty_index < generic_empty_index
    assert "No charts matching the {html.escape(gender_filter.title())} filter" in render_branch


def test_settings_consolidates_database_and_visualization_controls():
    from pathlib import Path

    source = Path("ephemeraldaddy/gui/app.py").read_text()
    settings_source = source.split("def _ensure_settings_dialog", 1)[1].split(
        "def _refresh_settings_footer_note", 1
    )[0]

    show_hide_index = settings_source.index('"Show/Hide Modules"')
    database_header_index = settings_source.index(
        'self._build_settings_subheader_label("Database View")', show_hide_index
    )
    chart_data_header_index = settings_source.index(
        'self._build_settings_subheader_label("Chart Data (Chart Editor)")', show_hide_index
    )
    assert show_hide_index < database_header_index < chart_data_header_index
    assert 'content_layout,\n            "Database View"' not in settings_source

    chart_methods_index = settings_source.index('"Chart Calculation Methods"')
    visualization_header_index = settings_source.index(
        'self._build_settings_subheader_label("Data Visualization")', chart_methods_index
    )
    significance_index = settings_source.index('QLabel("Significance correction:")')
    assert chart_methods_index < visualization_header_index < significance_index
    assert 'content_layout,\n            "Data Visualization"' not in settings_source
