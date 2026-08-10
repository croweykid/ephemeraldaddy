from types import SimpleNamespace

from ephemeraldaddy.gui.features.similarities.collection_contrast import (
    CollectionNorm,
    aggregate_collection_norms,
    contrast_collection_norms,
)


def chart(**positions):
    return SimpleNamespace(
        positions=positions,
        birthtime_unknown=True,
        retcon_time_used=False,
        human_design_gates=[],
        human_design_channels=[],
    )


def test_aggregate_norms_requires_half_of_usable_collection():
    norms = aggregate_collection_norms(
        [chart(Sun=1, Moon=31), chart(Sun=2, Moon=61), chart(Sun=35, Moon=91)]
    )

    assert CollectionNorm("Placements", "Sun in Aries") in norms
    assert CollectionNorm("Placements", "Moon in Taurus") not in norms


def test_contrast_partitions_collection_norms_into_three_columns():
    result = contrast_collection_norms(
        [chart(Sun=1, Moon=31), chart(Sun=2, Moon=32)],
        [chart(Sun=3, Moon=61), chart(Sun=4, Moon=62)],
    )

    assert CollectionNorm("Placements", "Moon in Taurus") in result.only_a
    assert CollectionNorm("Placements", "Sun in Aries") in result.overlap
    assert CollectionNorm("Placements", "Moon in Gemini") in result.only_b
