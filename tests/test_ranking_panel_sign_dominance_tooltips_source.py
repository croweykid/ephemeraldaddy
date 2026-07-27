from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "ephemeraldaddy/gui/ranking_panel.py").read_text(
    encoding="utf-8"
)
TOOLTIPS_SOURCE = (ROOT / "ephemeraldaddy/gui/tooltips.py").read_text(encoding="utf-8")


def test_sign_dominance_rows_install_color_coded_hover_tooltips():
    assert "SIGN_COLORS" in SOURCE
    assert "rankings_signs_label.linkHovered.connect" in SOURCE
    assert "set_link_hover_tooltip(" in SOURCE
    assert 'dominance_tooltips[f"chart:{chart_uid}"]' in SOURCE
    assert "sign_dominance_tooltip_html(" in SOURCE


def test_sign_dominance_tooltip_definitions_live_in_tooltips_module():
    assert "def sign_dominance_tooltip_html(" in TOOLTIPS_SOURCE
    assert "def set_link_hover_tooltip(" in TOOLTIPS_SOURCE
    assert "def _sign_dominance_tooltip_html(" not in SOURCE
    assert "def _on_sign_dominance_rank_chart_link_hovered(" not in SOURCE


def test_sign_dominance_tooltips_cover_big_three_combinations():
    helper = TOOLTIPS_SOURCE.split("def sign_dominance_tooltip_html", 1)[1].split(
        "def set_link_hover_tooltip", 1
    )[0]

    assert "sun_matches and moon_matches and rising_matches" in helper
    assert "sun_matches and rising_matches" in helper
    assert "moon_matches and rising_matches" in helper
    assert "sun_matches and moon_matches" in helper
    assert "matching_bodies" in helper
    assert "dominant despite" not in helper  # assembled as a colored HTML sentence
    assert "f\"{prefix} despite" in helper
    assert "PLANET_COLORS.get" in helper
    assert "SIGN_COLORS.get" in helper


def test_sign_dominance_subheader_contains_five_item_visual_key():
    helper = SOURCE.split("def _sign_dominance_key_html", 1)[1].split(
        "def _refresh_sign_dominance_rankings", 1
    )[0]

    assert "Sun/Moon/AS all in" in helper
    assert "Sun/Moon in" in helper
    assert "AS only, but still dominant in" in helper
    assert "Sun only, but still dominant in" in helper
    assert "Moon only, but still dominant in" in helper
    assert "font-weight:700; color:#39ff14" in helper
    assert "font-style:italic; color:#5dade2" in helper
    assert 'key.count' not in helper
    assert 'f"{self._sign_dominance_key_html(selected_sign)}"' in SOURCE
