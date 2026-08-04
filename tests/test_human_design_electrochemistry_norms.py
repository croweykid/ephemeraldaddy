from ephemeraldaddy.analysis.human_design_electrochemistry_norms import (
    calculate_human_design_electrochemistry_norms,
    electrochemistry_chart_tokens,
    electrochemistry_norms_freshness,
    electrochemistry_norms_refresh_threshold,
    load_human_design_electrochemistry_norms,
    save_human_design_electrochemistry_norms,
)
from ephemeraldaddy.analysis.human_design_synastry import HumanDesignSynastryCandidate


def candidate(uid, gates, *, uses_houses=True, astro_data_signature=None):
    return HumanDesignSynastryCandidate(
        uid,
        uid,
        None,
        frozenset(gates),
        uses_houses=uses_houses,
        astro_data_signature=astro_data_signature,
    )


def test_norms_use_each_unordered_pair_once_and_persist_compact_histogram(tmp_path):
    norms = calculate_human_design_electrochemistry_norms(
        [candidate("A", {64}), candidate("B", {47}), candidate("C", {61, 24})]
    )

    assert norms.sample_size == 3
    assert sum(norms.histogram) == 3
    assert len(norms.histogram) == 38
    assert dict(norms.percentile_thresholds).keys() == {50, 75, 90, 95}

    cache_path = tmp_path / "norms.json"
    save_human_design_electrochemistry_norms(cache_path, norms)
    assert load_human_design_electrochemistry_norms(cache_path) == norms
    assert "chart_uid" not in cache_path.read_text()


def test_norms_refresh_at_fifteen_percent_new_or_astro_changed_only():
    saved_candidates = [candidate(f"UID-{index}", {index % 64 + 1}) for index in range(20)]
    saved_tokens = electrochemistry_chart_tokens(saved_candidates)

    two_changed = list(saved_candidates)
    two_changed[0] = candidate("UID-0", {1}, astro_data_signature="changed-astro-data")
    two_changed.append(candidate("NEW", {61, 24}))
    freshness = electrochemistry_norms_freshness(
        saved_tokens,
        electrochemistry_chart_tokens(two_changed),
    )
    assert freshness.added_or_changed_uid_count == 2
    assert freshness.refresh_threshold == 3
    assert not freshness.requires_refresh

    three_changed = [*two_changed, candidate("NEW-2", {17, 62})]
    assert electrochemistry_norms_freshness(
        saved_tokens,
        electrochemistry_chart_tokens(three_changed),
    ).requires_refresh

    # Deletions alone are intentionally excluded from this cache's trigger.
    deleted = electrochemistry_chart_tokens(saved_candidates[:-5])
    deletion_freshness = electrochemistry_norms_freshness(saved_tokens, deleted)
    assert deletion_freshness.added_or_changed_uid_count == 0
    assert not deletion_freshness.requires_refresh


def test_norms_threshold_rounds_up_to_avoid_refreshing_before_fifteen_percent():
    assert electrochemistry_norms_refresh_threshold(20) == 3
    assert electrochemistry_norms_refresh_threshold(21) == 4
