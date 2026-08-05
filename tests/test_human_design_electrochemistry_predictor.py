from ephemeraldaddy.analysis.human_design_synastry import (
    HD_SYNASTRY_GENDER_METHOD_IDENTITY,
    HD_SYNASTRY_GENDER_METHOD_SEX,
    HumanDesignSynastryCandidate,
    filter_hd_synastry_candidates,
    human_design_electrochemistry_score,
    human_design_profile_relation,
    normalize_gates,
    rank_human_design_synastry,
    rank_human_design_synastry_ideal,
)


def _hd_electrochemistry_module():
    import pytest

    return pytest.importorskip(
        "ephemeraldaddy.gui.features.predictions.hd_electrochemistry",
        exc_type=ImportError,
    )


def candidate(uid, gates, name="Candidate", profile=None):
    return HumanDesignSynastryCandidate(uid, name, None, frozenset(gates), profile=profile)


def gendered_candidate(uid, gender):
    return HumanDesignSynastryCandidate(uid, uid, None, frozenset({47}), gender=gender)



def test_profile_relation_classifies_resonance_and_harmonics():
    assert human_design_profile_relation("2/4", "2/4") == ("fully resonant profile", 2)
    assert human_design_profile_relation("2/4", "5/1") == ("fully harmonic profile", 2)
    assert human_design_profile_relation("2/4", "5/4") == ("resonant & harmonic profile", 2)
    assert human_design_profile_relation("2/4", "2/6") == ("partially resonant profile", 1)
    assert human_design_profile_relation("2/4", "3/1") == ("partially harmonic profile", 1)
    assert human_design_profile_relation("2/4", "3/6") == (None, 0)


def test_ideal_rank_adds_profile_bonus_to_score_and_tiebreaking():
    source_gates = {64}
    results = rank_human_design_synastry_ideal(
        "SOURCE",
        source_gates,
        [
            candidate("PLAIN", {47}, "Plain", profile="3/6"),
            candidate("HARMONIC", {47}, "Harmonic", profile="5/1"),
        ],
        source_profile="2/4",
    )

    assert [match.chart_uid for match in results] == ["HARMONIC", "PLAIN"]
    assert results[0].profile_match == "fully harmonic profile"
    assert results[0].profile_bonus == 2
    assert results[0].score == results[1].score + 2


def test_ideal_rank_accepts_one_pass_candidate_iterables():
    results = rank_human_design_synastry_ideal(
        "SOURCE",
        {64},
        (
            candidate(uid, {47}, uid.title(), profile=profile)
            for uid, profile in (("PLAIN", "3/6"), ("HARMONIC", "5/1"))
        ),
        source_profile="2/4",
    )

    assert results[0].chart_uid == "HARMONIC"
    assert results[0].profile_bonus == 2

def test_rank_uses_summed_channel_and_center_score():
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
    assert results[0].score == 4


def test_electrochemistry_score_sums_cross_chart_channels_and_combined_centers():
    score, maximum = human_design_electrochemistry_score(
        {64, 61, 24},
        {47},
    )

    assert score == 3
    assert maximum == 37


def test_ideal_rank_prefers_exactly_eight_defined_centers_over_nine():
    source_gates = {64}
    all_gates = set(range(1, 65))
    head_gate_options = {47, 24, 4}
    eight_center_gates = all_gates - head_gate_options

    results = rank_human_design_synastry_ideal(
        "SOURCE",
        source_gates,
        [
            candidate("NINE", all_gates, "Nine centers"),
            candidate("EIGHT", eight_center_gates, "Eight centers"),
        ],
    )

    assert [match.chart_uid for match in results] == ["EIGHT", "NINE"]
    assert results[0].defined_centers == 8
    assert results[1].defined_centers == 9

def test_ideal_rank_breaks_eight_center_ties_by_completed_channels():
    source_gates = {1}
    all_gates = set(range(1, 65))
    eight_center_gates = all_gates - {64, 61, 63, 1, 8}

    results = rank_human_design_synastry_ideal(
        "SOURCE",
        source_gates,
        [
            candidate("FEWER", eight_center_gates, "Fewer channels"),
            candidate("MORE", eight_center_gates | {8}, "More channels"),
        ],
    )

    assert [match.chart_uid for match in results] == ["MORE", "FEWER"]
    assert results[0].defined_centers == 8
    assert results[1].defined_centers == 8
    assert results[0].completed_channels > results[1].completed_channels

def test_rank_reports_population_median_and_empirical_percentile():
    results = rank_human_design_synastry(
        "SOURCE",
        {64, 61},
        [candidate("ONE", {47}), candidate("TWO", {47, 24})],
    )

    assert [match.score for match in results] == [4, 3]
    assert all(match.population_median == 3.5 for match in results)
    assert [match.percentile for match in results] == [100.0, 50.0]


def test_rank_percentiles_use_one_cumulative_score_pass():
    from inspect import getsource

    ranking_source = getsource(rank_human_design_synastry)

    assert "score_counts = Counter(scores)" in ranking_source
    assert "percentile_by_score[match.score]" in ranking_source
    assert "sum(score <= match.score" not in ranking_source


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


def test_synastry_custom_collection_membership_is_part_of_render_token():
    from ephemeraldaddy.gui.features.charts.collections import CustomCollection

    hd_electrochemistry = _hd_electrochemistry_module()
    chart = type("Chart", (), {"chart_uid": "UID", "human_design_gates": [47]})()
    memberships = {"UID-A"}

    class Owner:
        hd_electrochemistry_gender_filter = "all"
        hd_electrochemistry_collection_filter = "favorites"

        def _load_custom_collections_from_settings(self):
            return {
                "favorites": CustomCollection(
                    "favorites", "Favorites", frozenset(), frozenset(memberships)
                )
            }

    owner = Owner()
    first_token = hd_electrochemistry.hd_electrochemistry_render_token(owner, chart)
    memberships.add("UID-B")

    assert hd_electrochemistry.hd_electrochemistry_render_token(owner, chart) != first_token


def test_collection_refresh_reloads_options_and_invalidates_ranking_source():
    from pathlib import Path

    source = Path("ephemeraldaddy/gui/features/predictions/hd_electrochemistry.py").read_text()
    refresh_branch = source.split("def refresh_hd_electrochemistry_collections", 1)[1].split(
        "def normalize_gendered_results_method", 1
    )[0]

    assert "reload_hd_electrochemistry_custom_collections(owner)" in refresh_branch
    assert "populate_hd_electrochemistry_collection_combo(owner, combo)" in refresh_branch
    assert 'setattr(owner, "_hd_electrochemistry_last_render_token", None)' in refresh_branch


def test_match_collection_updates_existing_database_view_state_source():
    from pathlib import Path

    source = Path("ephemeraldaddy/gui/features/predictions/hd_electrochemistry.py").read_text()
    create_branch = source.split(
        "def make_hd_electrochemistry_matches_collection", 1
    )[1].split("def on_gendered_results_method_changed", 1)[0]

    copy_index = create_branch.index(
        "manage_dialog._custom_collections = dict(custom_collections)"
    )
    refresh_index = create_branch.index("dialog_refresh_controls()")
    populate_index = create_branch.index("populate_list()")
    assert copy_index < refresh_index < populate_index


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

    assert 'addItem("🪷HD Electrochemistry", HD_ELECTROCHEMISTRY_MODE_STANDARD)' in synastry_branch
    assert 'addItem("🪷HD Electrochemical Ideal", HD_ELECTROCHEMISTRY_MODE_IDEAL)' in synastry_branch
    assert "on_hd_electrochemistry_mode_changed" in synastry_branch

    assert '(("All", "all"), ("Male", "male"), ("Female", "female"))' in synastry_branch
    assert "QRadioButton(label)" in synastry_branch
    assert "on_hd_electrochemistry_gender_filter_changed(owner, selected, checked)" in synastry_branch
    assert 'QLabel("Collection:")' in synastry_branch
    assert "populate_hd_electrochemistry_collection_combo" in synastry_branch
    assert "on_hd_electrochemistry_collection_changed" in synastry_branch
    assert '"Make collection from matches"' in synastry_branch
    assert "make_hd_electrochemistry_matches_collection(owner)" in synastry_branch


def test_match_collection_combines_top_ten_from_both_gender_groups(monkeypatch):
    hd_electrochemistry = _hd_electrochemistry_module()
    candidates = [
        gendered_candidate(f"M{index:02}", "M") for index in range(12)
    ] + [
        gendered_candidate(f"F{index:02}", "F") for index in range(12)
    ]
    monkeypatch.setattr(
        hd_electrochemistry,
        "list_human_design_electrochemistry_candidates",
        lambda: candidates,
    )
    monkeypatch.setattr(
        hd_electrochemistry,
        "load_gendered_results_method",
        lambda: HD_SYNASTRY_GENDER_METHOD_SEX,
    )
    owner = type("Owner", (), {"hd_electrochemistry_collection_filter": "all"})()
    chart = type("Chart", (), {"chart_uid": "SOURCE", "human_design_gates": [64]})()

    chart_uids = hd_electrochemistry.hd_electrochemistry_match_collection_uids(
        owner, chart
    )

    assert len(chart_uids) == 20
    assert len([uid for uid in chart_uids if uid.startswith("M")]) == 10
    assert len([uid for uid in chart_uids if uid.startswith("F")]) == 10



def test_match_collection_honors_selected_ideal_mode(monkeypatch):
    hd_electrochemistry = _hd_electrochemistry_module()
    candidates = [gendered_candidate("M01", "M"), gendered_candidate("F01", "F")]
    calls = []

    def standard_ranker(*_args, **_kwargs):
        calls.append("standard")
        return []

    def ideal_ranker(_chart_uid, _gates, filtered_candidates, **_kwargs):
        calls.append("ideal")
        return [
            type(
                "Match",
                (),
                {"chart_uid": candidate.chart_uid},
            )()
            for candidate in filtered_candidates
        ]

    monkeypatch.setattr(
        hd_electrochemistry,
        "list_human_design_electrochemistry_candidates",
        lambda: candidates,
    )
    monkeypatch.setattr(
        hd_electrochemistry,
        "load_gendered_results_method",
        lambda: HD_SYNASTRY_GENDER_METHOD_SEX,
    )
    monkeypatch.setattr(hd_electrochemistry, "rank_human_design_electrochemistry", standard_ranker)
    monkeypatch.setattr(hd_electrochemistry, "rank_human_design_electrochemistry_ideal", ideal_ranker)
    owner = type(
        "Owner",
        (),
        {
            "hd_electrochemistry_collection_filter": "all",
            "hd_electrochemistry_prediction_mode": hd_electrochemistry.HD_ELECTROCHEMISTRY_MODE_IDEAL,
        },
    )()
    chart = type("Chart", (), {"chart_uid": "SOURCE", "human_design_gates": [64]})()

    chart_uids = hd_electrochemistry.hd_electrochemistry_match_collection_uids(owner, chart)

    assert chart_uids == frozenset({"M01", "F01"})
    assert calls == ["ideal", "ideal"]

def test_match_collection_synchronizes_existing_database_view_dialog(monkeypatch):
    hd_electrochemistry = _hd_electrochemistry_module()

    class ManageDialog:
        def __init__(self):
            self._custom_collections = {}
            self.refresh_count = 0
            self.populate_count = 0

        def _refresh_collection_controls(self):
            self.refresh_count += 1

        def _populate_list(self):
            self.populate_count += 1

    class Owner:
        def __init__(self):
            self._latest_chart = object()
            self._custom_collections = {}
            self._manage_charts_dialog = ManageDialog()
            self.save_count = 0

        def _load_custom_collections_from_settings(self):
            return dict(self._custom_collections)

        def _save_custom_collections_to_settings(self):
            self.save_count += 1

    owner = Owner()
    monkeypatch.setattr(
        hd_electrochemistry,
        "hd_electrochemistry_match_collection_uids",
        lambda _owner, _chart: frozenset({"M01", "F01"}),
    )
    monkeypatch.setattr(
        hd_electrochemistry.QInputDialog,
        "getText",
        lambda *_args: ("Best Matches", True),
    )

    hd_electrochemistry.make_hd_electrochemistry_matches_collection(owner)

    dialog = owner._manage_charts_dialog
    assert owner.save_count == 1
    assert dialog._custom_collections == owner._custom_collections
    assert dialog._custom_collections["best_matches"].chart_uids == frozenset(
        {"M01", "F01"}
    )
    assert dialog.refresh_count == 1
    assert dialog.populate_count == 1


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



def test_electrochemistry_display_keeps_database_norms_on_unboosted_score():
    from pathlib import Path

    source = Path("ephemeraldaddy/gui/features/predictions/hd_electrochemistry.py").read_text()

    assert "score {match.score}/{score_maximum}" in source
    assert "norms.percentile_for_score(electrochemistry_score)" in source
    assert "percentile before profile bonus" in source

def test_electrochemistry_copy_distinguishes_chart_and_database_percentiles():
    from pathlib import Path

    source = Path("ephemeraldaddy/gui/features/predictions/hd_electrochemistry.py").read_text()

    assert "th percentile for this chart" in source
    assert "top 10% for this chart" in source
    assert "norms.percentile_for_score(electrochemistry_score)" in source
    assert "Database-wide norms are being calculated in the background." in source


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
        'self._build_settings_subheader_label("Chart Data Output")', show_hide_index
    )
    assert show_hide_index < database_header_index < chart_data_header_index
    assert "_build_settings_header_label" not in settings_source
    assert 'content_layout,\n            "Database View"' not in settings_source

    chart_methods_index = settings_source.index('"Chart Calculation Methods"')
    statistics_header_index = settings_source.index(
        'self._build_settings_subheader_label("Statistics")', chart_methods_index
    )
    significance_index = settings_source.index(
        'QLabel("Choose statistical-significance handling for analytics:")'
    )
    assert chart_methods_index < statistics_header_index < significance_index
    assert 'content_layout,\n            "Data Visualization"' not in settings_source


def test_settings_builder_call_sites_are_defined():
    import ast
    from pathlib import Path

    source = Path("ephemeraldaddy/gui/app.py").read_text()
    tree = ast.parse(source)

    settings_builder_calls = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
        and node.attr.startswith("_build_settings")
    }
    settings_builder_definitions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith("_build_settings")
    }

    assert settings_builder_calls <= settings_builder_definitions
    assert "_build_settings_header_label" not in settings_builder_calls


def test_candidate_loader_tolerates_legacy_database_without_hd_profile(monkeypatch, tmp_path):
    import sqlite3

    from ephemeraldaddy.core import db

    database_path = tmp_path / "legacy_hd_profile.sqlite"
    conn = sqlite3.connect(database_path)
    conn.execute(
        """
        CREATE TABLE charts (
            id INTEGER PRIMARY KEY,
            chart_uid TEXT,
            name TEXT,
            alias TEXT,
            human_design_gates TEXT,
            birthtime_unknown INTEGER,
            retcon_time_used INTEGER,
            gender TEXT,
            source TEXT,
            chart_type TEXT,
            relationship_types TEXT,
            derived_birth_data_signature TEXT,
            is_placeholder INTEGER DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        INSERT INTO charts (
            chart_uid, name, human_design_gates, birthtime_unknown, retcon_time_used
        ) VALUES ('0123456789ABCDEF', 'Legacy HD', '[1, 2, 3]', 0, 0)
        """
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "_get_conn", lambda: sqlite3.connect(database_path))

    candidates = db.list_human_design_synastry_candidates()

    assert len(candidates) == 1
    assert candidates[0].chart_uid == "0123456789ABCDEF"
    assert candidates[0].gates == frozenset({1, 2, 3})
    assert candidates[0].profile is None
