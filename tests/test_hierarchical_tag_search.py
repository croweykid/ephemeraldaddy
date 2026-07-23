from ephemeraldaddy.gui.features.charts.tag_search import chart_matches_tag_filters, tag_matches_filter


def test_parent_tag_filter_matches_exact_parent_and_children():
    assert tag_matches_filter("occupation.writer", "occupation.writer")
    assert tag_matches_filter("occupation.writer.essayist", "occupation.writer")
    assert not tag_matches_filter("occupation.artist", "occupation.writer")


def test_required_parent_tag_filter_includes_child_tagged_charts():
    assert chart_matches_tag_filters(
        ["occupation.writer.essayist"],
        included_tags=["occupation.writer"],
        excluded_tags=[],
        optional_tags=[],
        untagged_mode=0,
    )
    assert chart_matches_tag_filters(
        ["occupation.writer"],
        included_tags=["occupation.writer"],
        excluded_tags=[],
        optional_tags=[],
        untagged_mode=0,
    )


def test_excluded_parent_tag_filter_excludes_child_tagged_charts():
    assert not chart_matches_tag_filters(
        ["typology.enneagram.e9.e9w8"],
        included_tags=[],
        excluded_tags=["typology.enneagram.e9"],
        optional_tags=[],
        untagged_mode=0,
    )
