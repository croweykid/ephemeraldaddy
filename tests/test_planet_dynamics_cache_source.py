from pathlib import Path


def test_planet_dynamics_cache_signature_includes_aspects_and_rectified_time():
    source = Path("ephemeraldaddy/gui/app.py").read_text()
    method = source.split("def _planet_dynamics_cache_signature", 1)[1].split(
        "def _precompute_planet_dynamics_if_needed", 1
    )[0]

    assert "aspect_signature" in method
    assert 'aspect.get("p1", "")' in method
    assert 'aspect.get("p2", "")' in method
    assert 'aspect.get("type", "")' in method
    assert 'aspect.get("delta", 0.0)' in method
    assert 'getattr(chart, "retcon_time_used", False)' in method
    assert 'getattr(chart, "retcon_hour", None)' in method
    assert 'getattr(chart, "retcon_minute", None)' in method
    assert "_chart_uses_houses(chart)" in method
    assert "bool(chart_uses_houses(chart))" not in method
