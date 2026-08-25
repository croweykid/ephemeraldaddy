from ephemeraldaddy.gui.features.chart_editor.related_chart_choices import (
    RelatedChartChoiceRecord,
    build_related_chart_choice_map,
    build_related_chart_choices,
)


def test_related_chart_choices_are_user_facing_deduplicated_and_exclude_current():
    records = [
        RelatedChartChoiceRecord("CURRENTUID", "Current", "Me"),
        RelatedChartChoiceRecord("NEWUID", "New Chart", "New Alias"),
        RelatedChartChoiceRecord("THIRDUID", "new chart", "Third Alias"),
    ]

    assert build_related_chart_choices(
        records, current_chart_uid="currentuid"
    ) == ["New Chart — New Alias", "New Alias", "new chart — Third Alias", "Third Alias"]


def test_duplicate_labels_resolve_to_distinct_uids_without_displaying_uids():
    records = [
        RelatedChartChoiceRecord("FIRSTUID", "Alex", "", "Boston"),
        RelatedChartChoiceRecord("SECONDUID", "Alex", "", "", 27),
    ]

    choices = build_related_chart_choice_map(records, current_chart_uid=None)

    assert choices == {
        "Alex — Boston": "FIRSTUID",
        "Alex — Chart ID #27": "SECONDUID",
    }
    assert all(uid not in label for label, uid in choices.items())
