from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions.py").read_text()


def test_chart_local_likelihood_rows_use_active_trait_set_signature():
    persistence_block = SOURCE.split('rows_for_persistence = [', 1)[1].split('db.upsert_chart_trait_likelihoods', 1)[0]

    assert '"trait_signature": trait_signature' in persistence_block
    assert '"trait_signature": _trait_definition_signature' not in persistence_block
