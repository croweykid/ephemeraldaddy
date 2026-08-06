from ephemeraldaddy.gui.features.charts.similarities_algorithm_log import (
    build_similarity_algorithm_snapshot,
)
from ephemeraldaddy.gui.features.charts.similarity_custom_presets import (
    build_custom_astro_twin_preset_manager_rows,
)


def test_preset_manager_rows_include_weights_and_associated_data_points():
    settings = {"use_placement": True, "weight_placement": 0.75}
    snapshot = build_similarity_algorithm_snapshot("custom", settings)
    snapshot["settings"]["demographic_match_mode"] = "gender"

    rows = build_custom_astro_twin_preset_manager_rows(
        [{"name": "Custom 1", "settings": settings}],
        [
            {
                "algorithm_mode": "custom",
                "algorithm_snapshot": snapshot,
                "sample_count": 4,
            }
        ],
    )

    assert rows == [
        {
            "label": "Custom 1",
            "key": "Custom 1",
            "count": 4,
            "algorithm": "Placement: 0.75",
            "editable": False,
        }
    ]


def test_property_manager_source_has_requested_preset_columns_and_placeholder():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/dev_tools.py").read_text(
        encoding="utf-8"
    )
    manager = source.split("class ManageMetadataLabelsDialog", 1)[1]

    assert 'field_options = [("Astro Twin Presets", self.FIELD_ASTRO_TWIN_PRESETS)]' in manager
    assert 'QLabel("Astro Twin Presets Manager")' in manager
    assert 'setHeaderLabels(["Preset Name", "Algorithm", "Data Points"])' in manager
    assert '"select a preset to see its algorithmic weights"' in manager
    assert 'row_item.setText(1, "")' in manager
