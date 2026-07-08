from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_trait_prediction_debug_logs_use_uids_not_chart_names():
    source = (ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "trait_predictions.py").read_text(
        encoding="utf-8"
    )
    assert 'Trait metadata start chart_uid=%s' in source
    assert 'Trait metadata memory cache hit chart_uid=%s' in source
    assert 'Trait metadata start chart=%s' not in source
    assert 'Trait metadata memory cache hit chart=%s' not in source


def test_weighted_predictor_debug_labels_are_uid_only_and_parse_errors_do_not_print():
    source = (ROOT / "ephemeraldaddy" / "analysis" / "weighted_chart_predictor.py").read_text(encoding="utf-8")
    assert "def _privacy_safe_chart_label" in source
    assert 'return f"chart_uid={chart_uid}"' in source
    assert "chart_debug_label = _privacy_safe_chart_label(chart)" in source
    assert "getattr(chart, \"name\"" not in source
    assert "print(f\"{parse_error_prefix}" not in source


def test_chart_serializes_derived_traits_in_metadata():
    source = (ROOT / "ephemeraldaddy" / "core" / "chart.py").read_text(encoding="utf-8")
    assert 'self.traits = []' in source
    assert '"traits": list(getattr(self, "traits", []) or [])' in source
    assert '"traits_above_average": list(getattr(self, "traits_above_average", []) or [])' in source
    assert '"traits_below_average": list(getattr(self, "traits_below_average", []) or [])' in source
    assert '"trait_likelihoods": dict(getattr(self, "trait_likelihoods", {}) or {})' in source
