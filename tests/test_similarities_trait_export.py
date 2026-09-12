from __future__ import annotations

from collections import OrderedDict

from ephemeraldaddy.analysis.traits import parse_trait_file
from ephemeraldaddy.gui.features.charts import exporters
from ephemeraldaddy.gui.features.charts.similarities.trait_export import (
    build_similarities_trait_export_payload,
    compact_gender_distribution_weights,
)
from ephemeraldaddy.gui.features.charts.similarities_export import (
    format_similarities_json_export_payload,
)


def _export_sections():
    return [
        (
            "Top 3 Dominant Signs in common",
            [("Aries", 10, 10, 0, 100, "A, B")],
        )
    ]


def _gender_distribution():
    return OrderedDict(
        [
            ("counts", OrderedDict([("Female", 9), ("Male", 1)])),
            ("total", 10),
            ("percentages", OrderedDict([("Female", 90.0), ("Male", 10.0)])),
            ("databaseCounts", OrderedDict([("Female", 50), ("Male", 50)])),
            ("databaseTotal", 100),
            ("databasePercentages", OrderedDict([("Female", 50.0), ("Male", 50.0)])),
            ("statisticallySignificant", True),
            ("significantCategories", ["Female", "Male"]),
        ]
    )


def test_final_trait_builder_formats_sample_uids_and_compact_gender_weights() -> None:
    payload = build_similarities_trait_export_payload(
        "Sample Trait",
        _export_sections(),
        sample_uids=["uid-b", "UID-A", "uid-a"],
        gender_distribution=_gender_distribution(),
    )

    profile = payload["Sample Trait"]
    assert profile["sample_uids"] == ["UID-A", "UID-B"]
    assert "chartUIDs" not in profile
    assert profile["genderDistribution"] == {"Female": 40, "Male": -40}
    assert "counts" not in profile["genderDistribution"]
    assert "significance" not in profile["genderDistribution"]

    text = format_similarities_json_export_payload(payload)
    assert '"sample_uids": [' in text
    assert '"UID-A"' in text
    assert '"genderDistribution": {' in text
    assert '"Female": 40' in text
    assert '"Male": -40' in text
    assert '"chartUIDs"' not in text


def test_gender_export_uses_similarity_standard_error_gate_and_signed_weights() -> None:
    distribution = OrderedDict(
        [
            (
                "counts",
                OrderedDict(
                    [
                        ("AFAB-M", 1),
                        ("AFAB-NB", 0),
                        ("AMAB-F", 1),
                        ("AMAB-NB", 3),
                        ("F", 182),
                        ("M", 462),
                        ("n/a", 0),
                        ("Unspecified", 7),
                    ]
                ),
            ),
            ("total", 656),
            (
                "databaseCounts",
                OrderedDict(
                    [
                        ("AFAB-M", 3),
                        ("AFAB-NB", 3),
                        ("AMAB-F", 7),
                        ("AMAB-NB", 7),
                        ("F", 853),
                        ("M", 1654),
                        ("n/a", 3),
                        ("Unspecified", 30),
                    ]
                ),
            ),
            ("databaseTotal", 2560),
        ]
    )

    assert compact_gender_distribution_weights(distribution) == {
        "F": -6,
        "M": 6,
    }


def test_final_builder_omits_gender_distribution_when_no_weight_clears_gate() -> None:
    distribution = OrderedDict(
        [
            ("counts", OrderedDict([("Female", 6), ("Male", 4)])),
            ("total", 10),
            ("databaseCounts", OrderedDict([("Female", 50), ("Male", 50)])),
            ("databaseTotal", 100),
        ]
    )

    payload = build_similarities_trait_export_payload(
        "Quiet Trait",
        _export_sections(),
        gender_distribution=distribution,
    )

    assert "genderDistribution" not in payload["Quiet Trait"]


def test_final_builder_keeps_dissimilarity_bundle_metadata_free() -> None:
    payload = build_similarities_trait_export_payload(
        "Pair",
        [
            (
                "Top 3 Dominant Signs in contrast",
                [
                    ("Aries", 1, 2, 10, 100, "A", "chart_1", 2),
                    ("Taurus", 1, 2, 10, 100, "B", "chart_2", 2),
                ],
            )
        ],
        sample_uids=["UID-A", "UID-B"],
        gender_distribution=_gender_distribution(),
    )

    bundle = payload["Pair"]
    assert "sample_uids" not in bundle
    assert "chartUIDs" not in bundle
    assert "genderDistribution" not in bundle


def test_trait_parser_preserves_compact_export_metadata(tmp_path) -> None:
    payload = build_similarities_trait_export_payload(
        "Parser Trait",
        _export_sections(),
        sample_uids=["UID-A", "UID-B"],
        gender_distribution=_gender_distribution(),
    )
    export_path = tmp_path / "parser_trait.py"
    export_path.write_text(
        format_similarities_json_export_payload(payload),
        encoding="utf-8",
    )

    profile = parse_trait_file(export_path)["Parser Trait"]

    assert profile["sample_uids"] == ["UID-A", "UID-B"]
    assert profile["genderDistribution"] == {"Female": 40, "Male": -40}


def test_python_export_dialog_writes_source_sample_metadata(tmp_path, monkeypatch) -> None:
    export_path = tmp_path / "sample_trait.py"

    class FakeSettings:
        def value(self, _key, default=""):
            return default

        def setValue(self, _key, _value):
            return None

    monkeypatch.setattr(exporters, "QSettings", FakeSettings)
    monkeypatch.setattr(
        exporters.QInputDialog,
        "getText",
        lambda *args, **kwargs: ("Dialog Trait", True),
    )
    monkeypatch.setattr(
        exporters.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(export_path), "Python Files (*.py)"),
    )
    monkeypatch.setattr(exporters.QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(exporters.QMessageBox, "critical", lambda *args, **kwargs: None)

    exporters.export_similarities_analysis_json_dialog(
        None,
        _export_sections(),
        sample_uids=["uid-2", "UID-1"],
        gender_distribution=_gender_distribution(),
    )

    text = export_path.read_text(encoding="utf-8")
    assert '"sample_uids": [' in text
    assert '"UID-1"' in text
    assert '"UID-2"' in text
    assert '"genderDistribution": {' in text
    assert '"Female": 40' in text
    assert '"counts"' not in text
    assert '"databaseCounts"' not in text
    assert '"significance"' not in text
    assert '"chartUIDs"' not in text

    parsed = parse_trait_file(export_path)["Dialog Trait"]
    assert parsed["sample_uids"] == ["UID-1", "UID-2"]
    assert parsed["genderDistribution"] == {"Female": 40, "Male": -40}
