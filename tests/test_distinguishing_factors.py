from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_distinguishing_factor_html_does_not_truncate_significant_factors():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/charts/distinguishing_factors.py").read_text()

    assert "for factor in factors:" in source
    assert "for factor in factors[:12]:" not in source
