from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from ephemeraldaddy.gui.features.similarities.collection_contrast import (
    CollectionNorm,
    aggregate_collection_norms,
    collection_norm_counts,
    collection_trait_export_sections,
    contrast_collection_norms,
    filter_aggregable_charts,
)
from ephemeraldaddy.gui.features.charts.similarities_export import (
    build_similarities_json_export_payload,
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


def test_collection_column_export_uses_trait_import_profile_format():
    sun = CollectionNorm("Placements", "Sun in Aries")
    gate = CollectionNorm("Human Design Gates", "Gate 12")
    sections = collection_trait_export_sections(
        (sun, gate),
        Counter({sun: 8, gate: 7}),
        Counter({sun: 10, gate: 10}),
        Counter({sun: 20, gate: 10}),
        Counter({sun: 100, gate: 100}),
    )

    profile = build_similarities_json_export_payload("Collection A only", sections)[
        "Collection A only"
    ]

    assert profile["positions"] == {"Sun in Aries": 60}
    assert profile["gates"] == {12: 60}
    assert profile["samples"] == [10, 0]


def test_shared_column_export_combines_both_collections_independently():
    sun = CollectionNorm("Placements", "Sun in Aries")
    sections = collection_trait_export_sections(
        (sun,),
        Counter({sun: 14}),
        Counter({sun: 20}),
        Counter({sun: 20}),
        Counter({sun: 100}),
    )

    profile = build_similarities_json_export_payload("Shared", sections)["Shared"]

    assert profile["positions"] == {"Sun in Aries": 50}
    assert profile["samples"] == [20, 0]


def test_collection_export_accepts_every_similarities_analysis_factor_section():
    factors = (
        CollectionNorm("Top 3 Dominant Signs in common", "Aries"),
        CollectionNorm("Top 3 Dominant Bodies in common", "Sun"),
        CollectionNorm("Dominant nakshatras in common", "Ashwini"),
        CollectionNorm("Aspects in common", "Sun trine Moon"),
        CollectionNorm("Defined Centers in common", "Sacral"),
        CollectionNorm("Profiles in common", "1/3"),
        CollectionNorm("Authorities in common", "Sacral"),
        CollectionNorm("BaZi signs in common", "Yang Wood Rat"),
        CollectionNorm("Signs in houses in common", "Aries in H1"),
    )
    counts = Counter({factor: 8 for factor in factors})
    totals = Counter({factor: 10 for factor in factors})
    db_counts = Counter({factor: 20 for factor in factors})
    db_totals = Counter({factor: 100 for factor in factors})

    sections = collection_trait_export_sections(
        factors, counts, totals, db_counts, db_totals
    )
    profile = build_similarities_json_export_payload("Complete", sections)["Complete"]

    assert profile["signs"] == {"Aries": 60}
    assert profile["bodies"] == {"Sun": 60}
    assert profile["nakshatras"] == {"Ashwini": 60}
    assert profile["aspects"] == {"Sun trine Moon": 60}
    assert profile["centers"] == {"Sacral": 60}
    assert profile["profiles"] == {"1/3": 60}
    assert profile["authorities"] == {"Sacral": 60}
    assert profile["bazisigns"] == {"Yang Wood Rat": 60}
    assert profile["positions"]["Aries in H1"] == 60
    assert profile["model"] == ""
    assert profile["archived"] is False


def test_unknown_signs_are_not_counted_as_factual_collection_norms():
    norms = aggregate_collection_norms(
        [
            chart(unknown_signs={"Moon"}, Sun=1, Moon=31),
            chart(unknown_signs={"moon"}, Sun=2, Moon=32),
        ]
    )

    assert CollectionNorm("Placements", "Sun in Aries") in norms
    assert CollectionNorm("Placements", "Moon in Taurus") not in norms


def test_collection_norm_counts_reports_factor_and_usable_chart_totals():
    counts, known_totals, total = collection_norm_counts(
        [chart(Sun=1, Moon=31), chart(Sun=2, Moon=61), SimpleNamespace(positions={})]
    )

    assert total == 2
    assert counts[CollectionNorm("Placements", "Sun in Aries")] == 2
    assert counts[CollectionNorm("Placements", "Moon in Taurus")] == 1
    assert known_totals[CollectionNorm("Placements", "Sun in Aries")] == 2


def test_collection_norm_counts_uses_factor_specific_known_denominators():
    counts, known_totals, total = collection_norm_counts(
        [
            chart(Sun=1, Moon=31),
            chart(unknown_signs={"Moon"}, Sun=2, Moon=32),
            chart(Sun=3),
        ]
    )

    moon = CollectionNorm("Placements", "Moon in Taurus")
    assert total == 3
    assert counts[moon] == 1
    assert known_totals[moon] == 1


def test_house_norm_denominator_includes_only_charts_with_usable_house_data():
    timed = [
        SimpleNamespace(
            positions={"Sun": 1},
            houses=[1] * 12,
            birthtime_unknown=False,
            retcon_time_used=False,
            human_design_gates=[],
            human_design_channels=[],
            unknown_signs=(),
        )
        for _ in range(2)
    ]
    untimed = [chart(Sun=index) for index in range(8)]

    counts, known_totals, total = collection_norm_counts(timed + untimed)

    house_one = CollectionNorm("House Signs", "House 1: Aries")
    assert total == 10
    assert counts[house_one] == 2
    assert known_totals[house_one] == 2


def test_filter_aggregable_charts_reports_placeholder_and_hypothetical_omissions():
    included = chart(Sun=1)
    hypothetical = chart(Sun=2)
    hypothetical.source = "hypothetical"
    placeholder = chart(Sun=3)
    placeholder.is_placeholder = True

    aggregable, omitted = filter_aggregable_charts(
        [included, hypothetical, placeholder, None]
    )

    assert aggregable == [included]
    assert omitted == 2


def test_compare_dialog_imports_shared_similarity_indicator_template():
    source = Path(
        "ephemeraldaddy/gui/features/similarities/compare_collections.py"
    ).read_text(encoding="utf-8")

    assert (
        "from ephemeraldaddy.gui.features.charts.db_info_panel import add_similarity_match_row"
        in source
    )
    assert "similarity_delta_rgb(percent, db_percent, known_total)" in source
    assert 'selection_label="collection"' in source
    assert 'database_label="database"' in source
    assert "filter_aggregable_charts" in source
    assert "placeholder/hypothetical" in source


def test_dialog_initializes_button_before_populating_and_loads_population_once():
    source = Path(
        "ephemeraldaddy/gui/features/similarities/compare_collections.py"
    ).read_text(encoding="utf-8")

    assert source.index(
        'self.compare_button = QPushButton("Compare & Contrast!", self)'
    ) < source.index("self._populate_combos()")
    compare_body = source.split("    def _compare(self) -> None:", 1)[1].split(
        "    @staticmethod", 1
    )[0]
    assert compare_body.count("self._load_chart_population()") == 1
