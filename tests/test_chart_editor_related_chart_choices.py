from ephemeraldaddy.gui.features.chart_editor.related_chart_choices import (
    RelatedChartChoiceRecord,
    build_related_chart_choices,
)


def test_related_chart_choices_are_uid_first_deduplicated_and_exclude_current():
    records = [
        RelatedChartChoiceRecord("CURRENTUID", "Current", "Me"),
        RelatedChartChoiceRecord("NEWUID", "New Chart", "New Alias"),
        RelatedChartChoiceRecord("THIRDUID", "new chart", "Third Alias"),
    ]

    assert build_related_chart_choices(
        records, current_chart_uid="currentuid"
    ) == ["New Chart", "New Alias", "NEWUID", "Third Alias", "THIRDUID"]
