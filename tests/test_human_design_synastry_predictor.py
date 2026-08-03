from ephemeraldaddy.analysis.human_design_synastry import (
    HD_SYNASTRY_GENDER_METHOD_IDENTITY,
    HD_SYNASTRY_GENDER_METHOD_SEX,
    HumanDesignSynastryCandidate,
    filter_hd_synastry_candidates,
    normalize_gates,
    rank_human_design_synastry,
)


def _hd_synastry_module():
    import pytest

    return pytest.importorskip(
        "ephemeraldaddy.gui.features.predictions.hd_synastry",
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
    hd_synastry = _hd_synastry_module()
    chart = type("Chart", (), {"human_design_gates": []})()
    monkeypatch.setattr(
        hd_synastry,
        "derive_human_design_profile",
        lambda _chart: ([64, 47], [1], ["47-64"], "Projector"),
    )

    assert hd_synastry.resolve_hd_synastry_gates(chart) == frozenset({47, 64})
    assert chart.human_design_gates == [47, 64]


def test_synastry_hypothetical_warning_includes_chart_name():
    hd_synastry = _hd_synastry_module()
    chart = type(
        "Chart",
        (),
        {"name": "A & B", "birthtime_unknown": True, "retcon_time_used": True},
    )()

    subheader = hd_synastry.hd_synastry_subheader(chart)

    assert "Since A &amp; B's birth time is hypothetical" in subheader
    assert "results may be dodgier than usual" in subheader


def test_synastry_known_time_uses_standard_subheader():
    hd_synastry = _hd_synastry_module()
    chart = type("Chart", (), {"name": "Known", "birthtime_unknown": False})()

    assert hd_synastry.hd_synastry_subheader(chart) == hd_synastry.HD_SYNASTRY_SUBHEADER


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
    hd_synastry = _hd_synastry_module()
    chart = type("Chart", (), {"chart_uid": "UID", "human_design_gates": [47]})()
    owner = type("Owner", (), {"hd_synastry_gender_filter": "all"})()
    all_token = hd_synastry.hd_synastry_render_token(owner, chart)

    owner.hd_synastry_gender_filter = "female"

    assert hd_synastry.hd_synastry_render_token(owner, chart) != all_token


def test_right_panel_checks_synastry_revision_before_reranking():
    from pathlib import Path

    source = Path("ephemeraldaddy/gui/features/controllers/chart_right_panel.py").read_text()
    predictions_branch = source.split('if active_panel == "predictions":', 1)[1].split(
        'if active_panel == "time_sensitivity":', 1
    )[0]

    stale_check = predictions_branch.index("hd_synastry_predictions_are_current")
    render_call = predictions_branch.index("render_hd_synastry(chart)")
    assert stale_check < render_call
    assert "if predictions_are_current and hd_synastry_is_current:" in predictions_branch


def test_predicted_synastry_builds_gender_radios_with_refresh_callback():
    from pathlib import Path

    source = Path("ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()
    synastry_branch = source.split('title="Predicted Synastry"', 1)[1].split(
        'title="Traits"', 1
    )[0]

    assert '(("All", "all"), ("Male", "male"), ("Female", "female"))' in synastry_branch
    assert "QRadioButton(label)" in synastry_branch
    assert "on_hd_synastry_gender_filter_changed(owner, selected, checked)" in synastry_branch


def test_chart_calculation_settings_builds_gender_method_radios():
    from pathlib import Path

    source = Path("ephemeraldaddy/gui/app.py").read_text()
    settings_branch = source.split('"Chart Calculation Methods"', 1)[1].split(
        '"Data Visualization"', 1
    )[0]

    assert 'QLabel("For gendered results, use:")' in settings_branch
    assert '"Assigned-at-birth sex"' in settings_branch
    assert '"Gender identity"' in settings_branch
    assert "on_gendered_results_method_changed" in settings_branch
