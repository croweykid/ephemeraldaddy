from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_distinguishing_factor_html_does_not_truncate_significant_factors():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/distinguishing_factors.py").read_text()

    assert "for factor in factors:" in source
    assert "for factor in factors[:12]:" not in source


def test_incarnation_cross_info_uses_cross_type_for_angle_description():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert 'angle = str(cross_entry.get("cross_type", "")).strip() or "Unknown"' in source
    assert 'get_cross_type_description(angle)' in source
    assert 'cross_entry.get("angle"' not in source
