from pathlib import Path
from types import SimpleNamespace

from ephemeraldaddy.gui.features.similarities.collection_contrast import (
    CollectionNorm,
    aggregate_collection_norms,
    contrast_collection_norms,
)


def chart(*, unknown_signs=(), **positions):
    return SimpleNamespace(
        positions=positions,
        birthtime_unknown=True,
        retcon_time_used=False,
        human_design_gates=[],
        human_design_channels=[],
        unknown_signs=unknown_signs,
    )


def test_aggregate_norms_uses_similarities_analysis_two_chart_rule():
    norms = aggregate_collection_norms(
        [
            chart(Sun=1, Moon=31),
            chart(Sun=2, Moon=61),
            chart(Sun=35, Moon=91),
            chart(Sun=65, Moon=121),
            chart(Sun=95, Moon=151),
        ]
    )

    assert CollectionNorm("Placements", "Sun in Aries") in norms
    assert CollectionNorm("Placements", "Moon in Taurus") not in norms


def test_minimum_occurrences_can_be_overridden_for_stricter_callers():
    norms = aggregate_collection_norms(
        [chart(Sun=1), chart(Sun=2), chart(Sun=35)],
        minimum_occurrences=3,
    )

    assert CollectionNorm("Placements", "Sun in Aries") not in norms


def test_contrast_partitions_collection_norms_into_three_columns():
    result = contrast_collection_norms(
        [chart(Sun=1, Moon=31), chart(Sun=2, Moon=32)],
        [chart(Sun=3, Moon=61), chart(Sun=4, Moon=62)],
    )

    assert CollectionNorm("Placements", "Moon in Taurus") in result.only_a
    assert CollectionNorm("Placements", "Sun in Aries") in result.overlap
    assert CollectionNorm("Placements", "Moon in Gemini") in result.only_b


def test_unknown_signs_are_not_counted_as_factual_collection_norms():
    norms = aggregate_collection_norms(
        [
            chart(unknown_signs={"Moon"}, Sun=1, Moon=31),
            chart(unknown_signs={"moon"}, Sun=2, Moon=32),
        ]
    )

    assert CollectionNorm("Placements", "Sun in Aries") in norms
    assert CollectionNorm("Placements", "Moon in Taurus") not in norms


def test_dialog_initializes_button_before_populating_and_loads_population_once():
    source = Path(
        "ephemeraldaddy/gui/features/similarities/compare_collections.py"
    ).read_text(encoding="utf-8")

    assert source.index('self.compare_button = QPushButton("Compare & Contrast!", self)') < source.index(
        "self._populate_combos()"
    )
    compare_body = source.split("    def _compare(self) -> None:", 1)[1].split(
        "    @staticmethod", 1
    )[0]
    assert compare_body.count("self._load_chart_population()") == 1
