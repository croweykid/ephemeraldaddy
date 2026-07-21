from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/ranking_panel.py").read_text(
    encoding="utf-8"
)


def test_sign_dominance_rankings_style_names_by_selected_sign_big_three():
    helper = SOURCE.split("def _sign_dominance_chart_name_style", 1)[1].split(
        "def _refresh_sign_dominance_rankings", 1
    )[0]
    refresh = SOURCE.split("def _refresh_sign_dominance_rankings", 1)[1]

    assert 'self._rankings_chart_body_sign(chart, "Sun") == selected_sign' in helper
    assert 'self._rankings_chart_body_sign(chart, "Moon") == selected_sign' in helper
    assert 'self._rankings_chart_body_sign(chart, "AS") == selected_sign' in helper
    assert "bool(chart_uses_houses(chart))" in helper
    assert 'css_parts.append("font-style:italic")' in helper
    assert 'css_parts.append("color:#5dade2")' in helper
    assert 'css_parts.append("color:#39ff14")' in helper
    assert 'css_parts.append("font-weight:700")' in helper
    assert '"name_style": self._sign_dominance_chart_name_style(chart, selected_sign)' in refresh
    assert "style='{name_style}'" in refresh
