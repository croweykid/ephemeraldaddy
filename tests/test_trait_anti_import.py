from pathlib import Path

from ephemeraldaddy.analysis import traits
from ephemeraldaddy.gui.features.settings import trait_anti_import


ROOT = Path(__file__).resolve().parents[1]


def test_anti_properties_from_profile_preserves_weights_and_ignores_source_anti_buckets():
    profile = {
        "name": "Opposite cohort",
        "signs": {"Aries": 8, "Virgo": -4},
        "antisigns": {"Taurus": 99},
        "bodies": {"Mars": -6},
        "gate_lines": {"34.2": 5},
        "description": "metadata should not be copied",
    }

    imported = trait_anti_import.anti_properties_from_profile(profile)

    assert imported == {
        "antisigns": {"Aries": 8, "Virgo": -4},
        "antibodies": {"Mars": -6},
        "antigate_lines": {"34.2": 5},
    }
    assert "signs" not in imported
    assert "description" not in imported
    assert imported["antisigns"] != profile["antisigns"]


def test_append_anti_properties_retains_existing_and_new_value_wins_collision(tmp_path):
    target = tmp_path / "target.json"
    target.write_text(
        '''{
  "Target": {
    "name": "Target",
    "signs": {"Cancer": 3},
    "antisigns": {"Taurus": 4},
    "antibodies": {"Saturn": 2},
    "antiaspects": {}
  }
}

// # keep this trait note
''',
        encoding="utf-8",
    )

    trait_anti_import.apply_anti_properties_to_trait(
        target,
        {
            "antisigns": {"Gemini": 6, "Taurus": 9},
            "antiaspects": {"Moon square Saturn": -5},
        },
        replace=False,
    )

    profile = traits.parse_trait_file(target)["Target"]
    saved_text = target.read_text(encoding="utf-8")

    assert profile["signs"] == {"Cancer": 3}
    assert profile["antisigns"] == {"Taurus": 9, "Gemini": 6}
    assert profile["antibodies"] == {"Saturn": 2}
    assert profile["antiaspects"] == {"Moon square Saturn": -5}
    assert "// # keep this trait note" in saved_text


def test_replace_anti_properties_clears_old_categories_not_present_in_new_file(tmp_path):
    target = tmp_path / "target.json"
    target.write_text(
        '''{
  "Target": {
    "name": "Target",
    "antisigns": {"Taurus": 4},
    "antibodies": {"Saturn": 2},
    "antiaspects": {"Sun square Moon": 7}
  }
}
''',
        encoding="utf-8",
    )

    trait_anti_import.apply_anti_properties_to_trait(
        target,
        {"antisigns": {"Aries": 10}},
        replace=True,
    )

    profile = traits.parse_trait_file(target)["Target"]

    assert profile["antisigns"] == {"Aries": 10}
    assert profile["antibodies"] == {}
    assert profile["antiaspects"] == {}


def test_load_anti_properties_accepts_similarities_json_and_uses_only_normal_buckets(tmp_path):
    source = tmp_path / "similarities.json"
    source.write_text(
        '''{
  "Selection": {
    "name": "Selection",
    "signs": {"Scorpio": 12, "Aquarius": -3},
    "antisigns": {"Leo": 88},
    "channels": {"20-34": 4},
    "antichannels": {"16-48": 99},
    "samples": [20, 0],
    "color": "#cc99ff"
  }
}
''',
        encoding="utf-8",
    )

    imported = trait_anti_import.load_anti_properties_from_file(source)

    assert imported == {
        "antisigns": {"Scorpio": 12, "Aquarius": -3},
        "antichannels": {"20-34": 4},
    }


def test_load_anti_properties_accepts_bare_similarities_python_export_with_native_keys(tmp_path):
    source = tmp_path / "fav_writers_all_types_similarities_analysis.py"
    source.write_text(
        '''{
    "fav writers (all types)": {
        "name": "fav writers (all types)",
        "samples": [130, 0],
        "bodies": {"Venus": -11},
        "antibodies": {"Mars": 99},
        "positions": {
            "Moon in Virgo": 7,
            "Jupiter in H2": 8,
            "Neptune in Sagittarius": -9,
        },
        "gates": {31: 10, 40: 8, 9: -9},
        "gate_lines": {"31.4": 10, "28.6": -5},
        "channels": {(37, 40): 6},
        "centers": {"Spleen": -11},
        "antiaspects": {"source anti bucket must be ignored": 99},
    },
}
''',
        encoding="utf-8",
    )

    imported = trait_anti_import.load_anti_properties_from_file(source)

    assert imported["antibodies"] == {"Venus": -11}
    assert imported["antipositions"] == {
        "Moon in Virgo": 7,
        "Jupiter in H2": 8,
        "Neptune in Sagittarius": -9,
    }
    assert imported["antigates"] == {31: 10, 40: 8, 9: -9}
    assert imported["antigate_lines"] == {"31.4": 10, "28.6": -5}
    assert imported["antichannels"] == {(37, 40): 6}
    assert imported["anticenters"] == {"Spleen": -11}
    assert "antiaspects" not in imported


def test_confirmation_uses_standard_messagebox_result(monkeypatch):
    class FakeMessageBox:
        class StandardButton:
            Yes = 1
            No = 2

        @staticmethod
        def question(parent, title, text, buttons, default_button):
            assert title == "Append anti-trait file?"
            assert "sample.py" in text
            assert "Target" in text
            assert buttons == 3
            assert default_button == FakeMessageBox.StandardButton.No
            return FakeMessageBox.StandardButton.Yes

    monkeypatch.setattr(trait_anti_import, "QMessageBox", FakeMessageBox)

    assert trait_anti_import._confirm_selected_file(
        None,
        file_name="sample.py",
        trait_name="Target",
    ) is True


def test_existing_anti_choice_uses_input_dialog_not_qpushbutton_wrappers(monkeypatch):
    class FakeInputDialog:
        @staticmethod
        def getItem(parent, title, text, items, current, editable):
            assert items == ["Append to existing", "Replace"]
            assert current == 0
            assert editable is False
            return "Replace", True

    monkeypatch.setattr(trait_anti_import, "QInputDialog", FakeInputDialog)

    assert trait_anti_import._existing_anti_properties_choice(None, trait_name="Target") == "replace"


def test_traits_facade_installs_anti_trait_extension_and_ui_copy_is_exact():
    facade_source = (
        ROOT / "ephemeraldaddy" / "gui" / "features" / "settings" / "traits.py"
    ).read_text(encoding="utf-8")
    anti_source = (
        ROOT / "ephemeraldaddy" / "gui" / "features" / "settings" / "trait_anti_import.py"
    ).read_text(encoding="utf-8")

    assert "install_trait_anti_import as _install_trait_anti_import" in facade_source
    assert "_install_trait_anti_import(_core)" in facade_source
    assert 'QPushButton("Append anti-trait file")' in anti_source
    assert '"append a JSON file that represents the antithesis of this trait"' in anti_source
    assert 'QMessageBox.question(' in anti_source
    assert 'QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No' in anti_source
    assert 'QInputDialog.getItem(' in anti_source
    assert '["Append to existing", "Replace"]' in anti_source
    assert 'f"Successfully {action_text} {trait_name}!"' in anti_source
    assert '"Trait files (*.json *.py);;JSON files (*.json);;Python files (*.py);;All files (*)"' in anti_source
    assert "button_row.insertWidget(upload_index + 1, owner._traits_append_anti_button)" in anti_source


def test_import_handler_confirms_before_parsing_and_writes_only_after_existing_choice():
    anti_source = (
        ROOT / "ephemeraldaddy" / "gui" / "features" / "settings" / "trait_anti_import.py"
    ).read_text(encoding="utf-8")
    handler = anti_source.split("def on_trait_append_anti_clicked", 1)[1].split(
        "def install_trait_anti_import", 1
    )[0]

    first_confirmation = handler.index("_confirm_selected_file(")
    parse_import = handler.index("load_anti_properties_from_file(file_path)")
    existing_choice = handler.index("_existing_anti_properties_choice(")
    write_change = handler.index("apply_anti_properties_to_trait(")
    success_dialog = handler.index('"Anti-properties updated"')

    assert first_confirmation < parse_import < existing_choice < write_change < success_dialog
    assert "if choice is None:\n            return" in handler[existing_choice:write_change]
