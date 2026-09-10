from __future__ import annotations

from collections import OrderedDict

from ephemeraldaddy.analysis.traits import parse_trait_file
from ephemeraldaddy.gui.features.charts import exporters
from ephemeraldaddy.gui.features.charts.similarities.trait_export import (
    build_similarities_trait_export_payload,
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
            ("counts", OrderedDict([("Female", 8), ("Male", 2)])),
            ("total", 10),
            ("percentages", OrderedDict([("Female", 80.0), ("Male", 20.0)])),
            ("databasePercentages", OrderedDict([("Female", 50.0), ("Male", 50.0)])),
            ("statisticallySignificant", True),
            ("significantCategories", ["Female"]),
        ]
    )


def test_final_trait_builder_formats_sample_uids_and_gender_distribution() -> None:
    payload = build_similarities_trait_export_payload(
        "Sample Trait",
        _export_sections(),
        sample_uids=["uid-b", "UID-A", "uid-a"],
        gender_distribution=_gender_distribution(),
    )

    profile = payload["Sample Trait"]
    assert profile["sample_uids"] == ["UID-A", "UID-B"]
    assert "chartUIDs" not in profile
    assert profile["genderDistribution"]["percentages"]["Female"] == 80.0

    text = format_similarities_json_export_payload(payload)
    assert '"sample_uids": [' in text
    assert '"UID-A"' in text
    assert '"genderDistribution": {' in text
    assert '"chartUIDs"' not in text


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


def test_trait_parser_preserves_new_export_metadata(tmp_path) -> None:
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
    assert profile["genderDistribution"]["counts"] == {"Female": 8, "Male": 2}


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
    assert '"chartUIDs"' not in text

    parsed = parse_trait_file(export_path)["Dialog Trait"]
    assert parsed["sample_uids"] == ["UID-1", "UID-2"]
