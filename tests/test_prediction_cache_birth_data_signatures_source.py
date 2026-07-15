from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRAIT_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions.py").read_text(encoding="utf-8")
DND_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/dnd_predictions.py").read_text(encoding="utf-8")
ENNEAGRAM_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/enneagram_predictions.py").read_text(encoding="utf-8")


def test_trait_chart_signature_uses_only_essential_birth_data_not_derived_payloads():
    helper = TRAIT_SOURCE.split("def _chart_trait_metadata_signature", 1)[1].split(
        "def _database_norm_refresh_threshold", 1
    )[0]

    assert '"birth_date"' in helper
    assert '"birth_time"' in helper
    assert '"birth_place"' in helper
    assert '"retcon_time_used"' in helper
    assert '"retcon_hour"' in helper
    assert '"retcon_minute"' in helper
    assert '"rectification_range_used"' in helper
    assert '"rectification_range_start_minute"' in helper
    assert '"rectification_range_end_minute"' in helper
    assert '"chart_uses_houses"' in helper
    assert '"scoring_payload"' not in helper
    assert '"positions"' not in helper
    assert '"aspects"' not in helper
    assert '"human_design_gates"' not in helper
    assert '"bazi_sign_weights"' not in helper


def test_dnd_cache_tokens_ignore_chart_name_and_include_rectification_range():
    stat_helper = DND_SOURCE.split("def _chart_state_cache_token", 1)[1].split(
        "def _statblock_cache_key", 1
    )[0]
    alignment_helper = DND_SOURCE.split("def _dnd_alignment_cache_key", 1)[1].split(
        "def _dnd_alignment_score_parts", 1
    )[0]

    for helper in (stat_helper, alignment_helper):
        assert '"name"' not in helper
        assert '"birth_date"' in helper
        assert '"birth_time"' in helper
        assert '"datetime_iso"' in helper
        assert '"rectification_range_used"' in helper
        assert '"rectification_range_start_minute"' in helper
        assert '"rectification_range_end_minute"' in helper


def test_enneagram_cache_token_includes_rectification_range_birth_data():
    helper = ENNEAGRAM_SOURCE.split("def _enneagram_chart_state_token", 1)[1].split(
        "def _load_persisted_enneagram_prediction_payload", 1
    )[0]

    assert '"birth_date"' in helper
    assert '"birth_time"' in helper
    assert '"datetime_iso"' in helper
    assert '"rectification_range_used"' in helper
    assert '"rectification_range_start_minute"' in helper
    assert '"rectification_range_end_minute"' in helper
