from ephemeraldaddy.gui.features.charts.similarities_layout import (
    bounded_similarity_section_height,
)


def test_similarity_section_height_shrinks_to_rendered_rows():
    assert bounded_similarity_section_height([34], 100, frame_padding=4) == 38


def test_similarity_section_height_caps_at_configured_expanded_height():
    assert bounded_similarity_section_height([34, 34, 34, 34], 100, frame_padding=4) == 100


def test_similarity_section_height_returns_zero_without_rows():
    assert bounded_similarity_section_height([], 100, frame_padding=4) == 0
