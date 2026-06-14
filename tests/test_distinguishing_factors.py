from pathlib import Path

from ephemeraldaddy.analysis.hd_incarnation_crosses import (
    HD_INCARNATION_CROSSES,
    find_cross_by_name,
    get_cross_theme_description,
)


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


def test_incarnation_cross_lookup_accepts_chart_display_label_with_gates():
    cross = find_cross_by_name("Right Angle Cross of the Sphinx 4 (gates 1/2 • 7/13)")

    assert cross is not None
    assert cross["full_name"] == "Right Angle Cross of the Sphinx 4"


def test_all_incarnation_cross_themes_have_descriptions():
    missing = sorted(
        {
            str(entry["theme"])
            for entry in HD_INCARNATION_CROSSES
            if not get_cross_theme_description(str(entry["theme"]))
        }
    )

    assert missing == []
