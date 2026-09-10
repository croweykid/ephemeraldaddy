from __future__ import annotations

from types import SimpleNamespace

from ephemeraldaddy.gui.features.charts.similarities.cohort_controller import (
    SimilaritiesController,
)
from ephemeraldaddy.gui.features.charts.similarities.cohort_metadata import (
    UNSPECIFIED_GENDER_LABEL,
    build_gender_distribution,
    gender_counts,
)


def _chart(gender: object = None) -> SimpleNamespace:
    return SimpleNamespace(gender=gender)


def test_gender_counts_preserves_labels_and_counts_missing_as_unspecified() -> None:
    charts = [
        _chart("Male"),
        _chart("AFAB-M"),
        _chart(None),
        _chart("   "),
        SimpleNamespace(),
    ]

    counts = gender_counts(charts)

    assert counts["Male"] == 1
    assert counts["AFAB-M"] == 1
    assert counts[UNSPECIFIED_GENDER_LABEL] == 3
    assert sum(counts.values()) == len(charts)


def test_gender_distribution_keeps_full_cohort_denominator_with_missing_gender() -> None:
    selected = [_chart("Male") for _ in range(6)] + [_chart(None)]
    database = [_chart("Male") for _ in range(5)] + [_chart("Female") for _ in range(5)]

    distribution = build_gender_distribution(selected, database)

    assert distribution is not None
    assert distribution["total"] == 7
    assert distribution["counts"]["Male"] == 6
    assert distribution["counts"][UNSPECIFIED_GENDER_LABEL] == 1
    assert distribution["percentages"]["Male"] == 85.7
    assert distribution["percentages"][UNSPECIFIED_GENDER_LABEL] == 14.3
    assert sum(distribution["percentages"].values()) == 100.0


def test_gender_distribution_retains_seven_of_seven_prevalence() -> None:
    selected = [_chart("Male") for _ in range(7)]
    database = [_chart("Male") for _ in range(5)] + [_chart("Female") for _ in range(5)]

    distribution = build_gender_distribution(selected, database)

    assert distribution is not None
    assert distribution["total"] == 7
    assert distribution["counts"]["Male"] == 7
    assert distribution["percentages"]["Male"] == 100.0


def test_gender_distribution_can_be_entirely_unspecified() -> None:
    selected = [_chart(None) for _ in range(7)]
    database = [_chart("Male"), _chart("Female"), _chart(None)]

    distribution = build_gender_distribution(selected, database)

    assert distribution is not None
    assert distribution["total"] == 7
    assert distribution["counts"][UNSPECIFIED_GENDER_LABEL] == 7
    assert distribution["percentages"][UNSPECIFIED_GENDER_LABEL] == 100.0


def test_gender_distribution_preserves_canonical_afab_m_label() -> None:
    selected = [_chart("AFAB-M") for _ in range(4)] + [_chart("Male")]
    database = [_chart("AFAB-M"), _chart("Male")]

    distribution = build_gender_distribution(selected, database)

    assert distribution is not None
    assert "AFAB-M" in distribution["counts"]
    assert distribution["counts"]["AFAB-M"] == 4
    assert distribution["percentages"]["AFAB-M"] == 80.0


class _FakeToggle:
    def __init__(self, *, checked: bool = True) -> None:
        self.visible = False
        self._checked = checked

    def setVisible(self, visible: bool) -> None:
        self.visible = bool(visible)

    def isChecked(self) -> bool:
        return self._checked


class _FakeList:
    def __init__(self) -> None:
        self.visible = False
        self.items: list[str] = []
        self.tooltip = ""

    def setVisible(self, visible: bool) -> None:
        self.visible = bool(visible)

    def clear(self) -> None:
        self.items.clear()

    def addItem(self, text: str) -> None:
        self.items.append(text)

    def setToolTip(self, text: str) -> None:
        self.tooltip = text


def test_gender_section_renders_without_adjusted_statistical_significance() -> None:
    controller = SimilaritiesController.__new__(SimilaritiesController)
    toggle = _FakeToggle(checked=True)
    section_list = _FakeList()
    controller.gender_distribution_toggle = toggle
    controller.gender_distribution_list = section_list
    controller._cohort_gender_distribution = {
        "counts": {"Male": 7},
        "percentages": {"Male": 100.0},
        "databasePercentages": {"Male": 50.0},
        "significance": {"Male": {"significant": False}},
        "statisticallySignificant": False,
    }

    controller._render_gender_distribution()

    assert toggle.visible is True
    assert section_list.visible is True
    assert section_list.items == ["Male: 100.0% (DB 50.0%, +50.0 pp)"]
