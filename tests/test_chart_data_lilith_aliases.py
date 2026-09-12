import pytest

from ephemeraldaddy.gui.features.charts.text_summary import _display_body_with_glyph


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Lilith", "⚸🌝 M. Lilith"),
        ("Mean Lilith", "⚸🌝 M. Lilith"),
        ("Osculating Lilith", "⚸🌚 O. Lilith"),
        ("Natural Lilith", "⚸🌜 N. Lilith"),
    ],
)
def test_chart_data_lilith_aliases(body: str, expected: str) -> None:
    assert _display_body_with_glyph(body, use_lilith_alias=True) == expected
