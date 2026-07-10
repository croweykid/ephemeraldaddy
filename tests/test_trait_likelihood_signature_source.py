from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions.py").read_text()
DATABASE_ANALYTICS_SOURCE = (
    REPO_ROOT / "ephemeraldaddy/gui/features/charts/database_analytics.py"
).read_text()
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()


def test_chart_local_likelihood_rows_use_active_trait_set_signature():
    persistence_block = SOURCE.split('rows_for_persistence = [', 1)[1].split('db.upsert_chart_trait_likelihoods', 1)[0]

    assert '"trait_signature": trait_signature' in persistence_block
    assert '"trait_signature": _trait_definition_signature' not in persistence_block


def test_trait_norm_tokens_ignore_non_scoring_row_text_fields():
    token_helper = SOURCE.split('def _database_norm_chart_token_payload', 1)[1].split('def _database_norm_state', 1)[0]

    assert 'repr(normalized)' not in SOURCE.split('def _database_norm_chart_token_source', 1)[1].split('def _database_norm_state', 1)[0]
    assert '"datetime_iso"' in token_helper
    assert '"birth_place"' in token_helper
    assert '"birthtime_unknown"' in token_helper
    assert '"retcon_time_used"' in token_helper
    assert '"birth_month"' in token_helper
    assert '"birth_day"' in token_helper
    assert '"birth_year"' in token_helper
    assert '"retcon_hour"' in token_helper
    assert '"retcon_minute"' in token_helper
    assert '"tags"' not in token_helper
    assert '"biography"' not in token_helper
    assert '"source"' not in token_helper


def test_traits_distribution_tokens_ignore_non_scoring_row_text_fields():
    token_helper = DATABASE_ANALYTICS_SOURCE.split(
        'def _traits_distribution_chart_token_payload', 1
    )[1].split('def _traits_distribution_chart_tokens', 1)[0]
    token_source = DATABASE_ANALYTICS_SOURCE.split(
        'def _traits_distribution_chart_tokens', 1
    )[1].split('def _traits_distribution_likelihood_cache_path', 1)[0]

    assert 'repr(encoded)' not in token_source
    assert '_encode_database_metrics_cache_value' not in token_source
    assert '"datetime_iso"' in token_helper
    assert '"birth_place"' in token_helper
    assert '"birthtime_unknown"' in token_helper
    assert '"retcon_time_used"' in token_helper
    assert '"birth_month"' in token_helper
    assert '"birth_day"' in token_helper
    assert '"birth_year"' in token_helper
    assert '"retcon_hour"' in token_helper
    assert '"retcon_minute"' in token_helper
    assert '"tags"' not in token_helper
    assert '"biography"' not in token_helper
    assert '"source"' not in token_helper


def test_prediction_norm_render_token_ignores_non_scoring_row_text_fields():
    token_helper = APP_SOURCE.split(
        'def _prediction_norm_row_token_payload', 1
    )[1].split('def _prediction_norms_render_token', 1)[0]
    token_source = APP_SOURCE.split(
        'def _prediction_norms_render_token', 1
    )[1].split('def _prediction_norm_charts', 1)[0]

    assert 'repr(row)' not in token_source
    assert '_prediction_norms_revision' not in token_source
    assert '"datetime_iso"' in token_helper
    assert '"birth_place"' in token_helper
    assert '"birthtime_unknown"' in token_helper
    assert '"retcon_time_used"' in token_helper
    assert '"birth_month"' in token_helper
    assert '"birth_day"' in token_helper
    assert '"birth_year"' in token_helper
    assert '"retcon_hour"' in token_helper
    assert '"retcon_minute"' in token_helper
    assert '"tags"' not in token_helper
    assert '"biography"' not in token_helper
    assert '"source"' not in token_helper
