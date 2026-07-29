import json

from ephemeraldaddy.gui.features.charts.similarity_custom_presets import (
    CUSTOM_ASTRO_TWIN_PRESETS_FILENAME,
    load_custom_astro_twin_presets,
    next_custom_astro_twin_preset_name,
    save_custom_astro_twin_preset,
)


def test_next_custom_name_follows_highest_numbered_custom_preset():
    presets = [
        {"name": "Custom 2"},
        {"name": "Experiment"},
        {"name": "Custom 6"},
        {"name": "custom 20"},
    ]

    assert next_custom_astro_twin_preset_name(presets) == "Custom 7"
    assert next_custom_astro_twin_preset_name([]) == "Custom 1"


def test_save_custom_preset_uses_extensionless_local_file_and_preserves_weights(tmp_path):
    path = tmp_path / CUSTOM_ASTRO_TWIN_PRESETS_FILENAME
    settings = {
        "use_placement": True,
        "weight_placement": 0.42,
        "placement_weighting_mode": "hybrid",
    }

    saved_path = save_custom_astro_twin_preset("Custom 1", settings, path=path)
    save_custom_astro_twin_preset("My weights", {"weight_big_3": 0.75}, path=path)

    assert saved_path.name == "custom_astro_twin_presets"
    assert load_custom_astro_twin_presets(path) == [
        {"name": "Custom 1", "settings": settings},
        {"name": "My weights", "settings": {"weight_big_3": 0.75}},
    ]
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 1
