from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FACADE_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/trait_predictions.py").read_text(encoding="utf-8")
CONTEXT_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/trait_prediction_context.py").read_text(encoding="utf-8")
PREDICTION_CONTEXT_SOURCE = (REPO_ROOT / "ephemeraldaddy/analysis/prediction_context.py").read_text(encoding="utf-8")


def test_trait_predictions_installs_effective_prediction_context():
    assert "install_trait_prediction_context" in FACADE_SOURCE
    assert "_install_trait_prediction_context(_core)" in FACADE_SOURCE


def test_trait_score_and_explanation_share_one_context():
    assert "matched_criteria_out" in PREDICTION_CONTEXT_SOURCE
    assert "prediction_context=context" in CONTEXT_SOURCE
    assert 'result["factor_matches"] = _ensure_trait_matches' in CONTEXT_SOURCE
    assert "_cached_trait_matches" in CONTEXT_SOURCE


def test_effective_context_rejects_persisted_derived_weights():
    assert 'setattr(effective, attr, {})' in PREDICTION_CONTEXT_SOURCE
    assert "apply_time_specific_metadata_policy(effective)" in PREDICTION_CONTEXT_SOURCE
    assert "effective.dominant_sign_weights = dict(sign_weights)" in PREDICTION_CONTEXT_SOURCE
