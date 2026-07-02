from pathlib import Path

from ephemeraldaddy.analysis import traits


def test_parse_similarities_python_export_preserves_trait_profile(tmp_path):
    source = tmp_path / "trait.py"
    source.write_text(
        '''{
    "Selection": {
        "name": "Selection",
        "signs": {"Aries": 2},
        "channels": {(1, 8): 3},
    },
}
''',
        encoding="utf-8",
    )

    parsed = traits.parse_trait_file(source)

    assert parsed["Selection"]["signs"] == {"Aries": 2}
    assert parsed["Selection"]["channels"] == {(1, 8): 3}


def test_parse_exact_similarities_python_export_assignment(tmp_path):
    source = tmp_path / "similarities_export.py"
    source.write_text(
        '''TRAITS = {
    "Selection": {
        "name": "Selection",
        "gates": {
            34: 5,
            20: 5,
        },
        "channels": {
            (20, 34): 4,
        },
        "quotes": {},
    },
}
''',
        encoding="utf-8",
    )

    parsed = traits.parse_trait_file(source)

    assert parsed["Selection"]["gates"] == {34: 5, 20: 5}
    assert parsed["Selection"]["channels"] == {(20, 34): 4}


def test_parse_enneagram_style_assignment_with_int_keys_sets_and_inline_comments(tmp_path):
    source = tmp_path / "enneagram.py"
    source.write_text(
        '''ENNEAGRAM = {
    1: { # sample size was 77
        "name": "Idealist",
        "signs": {"Scorpio": 6, "Virgo": 4},
        "antisigns": {"Sagittarius": 4,},
        "houses": {1: 8},
        "positions": {"Sun in Scorpio": 6, "Moon in H8": 9,},
        "gates": {7: 13, 62: 12},
        "channels": {
            (24, 61): 1,
        },
    },
}
''',
        encoding="utf-8",
    )

    parsed = traits.parse_trait_file(source)

    assert parsed["Idealist"]["signs"] == {"Scorpio": 6, "Virgo": 4}
    assert parsed["Idealist"]["houses"] == {1: 8}
    assert parsed["Idealist"]["channels"] == {(24, 61): 1}


def test_parse_json_named_similarities_export_with_python_comments_and_trailing_commas(tmp_path):
    source = tmp_path / "trait.json"
    source.write_text(
        '''{
    "Selection": {
        "name": "Selection",
        "houses": {
            "11": 4,
            "7": -3,
        },
        "antihouses": {
            "9": 4, // inline note from Similarities Analysis
        },
        "channels": {
            (20, 34): 4, // tuple channel key from Similarities Analysis
        },
        "positions": {
            //"Neptune in Taurus": -1,
            "Neptune in H3": 4,
        },
    },
}
''',
        encoding="utf-8",
    )

    parsed = traits.parse_trait_file(source)

    assert parsed["Selection"]["houses"] == {"11": 4, "7": -3}
    assert parsed["Selection"]["antihouses"] == {"9": 4}
    assert parsed["Selection"]["channels"] == {(20, 34): 4}
    assert parsed["Selection"]["positions"] == {"Neptune in H3": 4}


def test_install_rename_delete_trait_uses_local_traits_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(traits, "TRAIT_DIR", tmp_path)
    source = tmp_path / "upload.py"
    source.write_text('{"Original": {"name": "Original", "bodies": {"Moon": 1}}}', encoding="utf-8")

    installed = traits.install_trait_file(source, "My Trait")
    assert installed.exists()
    assert traits.list_traits()[0]["name"] == "My Trait"

    renamed = traits.rename_trait(installed, "New Trait")
    assert renamed.exists()
    assert not installed.exists()
    assert traits.list_traits()[0]["name"] == "New Trait"

    traits.delete_trait(renamed)
    assert traits.list_traits() == []


def test_install_trait_file_serializes_python_tuple_channel_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(traits, "TRAIT_DIR", tmp_path / "traits")
    source = tmp_path / "upload.py"
    source.write_text(
        '{"Original": {"name": "Original", "channels": {(1, 8): 3}}}',
        encoding="utf-8",
    )

    installed = traits.install_trait_file(source, "Channel Trait")
    saved_text = installed.read_text(encoding="utf-8")

    assert "1-8" in saved_text
    assert traits.list_traits()[0]["profile"]["channels"] == {"1-8": 3}


def test_trait_color_and_archive_metadata_are_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr(traits, "TRAIT_DIR", tmp_path / "traits")
    source = tmp_path / "upload.py"
    source.write_text('{"Original": {"name": "Original", "bodies": {"Moon": 1}}}', encoding="utf-8")

    installed = traits.install_trait_file(source, "Color Trait", color="#12ABef")
    item = traits.list_traits()[0]
    assert item["color"] == "#12abef"
    assert item["profile"]["color"] == "#12abef"
    assert item["archived"] is False

    traits.set_trait_color(installed, "bad-color")
    assert traits.list_traits()[0]["color"] == traits.DEFAULT_TRAIT_COLOR

    traits.set_trait_archived(installed, True)
    assert traits.list_traits()[0]["archived"] is True
    assert traits.list_traits(active_only=True) == []

    traits.set_trait_archived(installed, False)
    renamed = traits.rename_trait(installed, "Renamed Color Trait")
    renamed_item = traits.list_traits()[0]
    assert renamed_item["path"] == renamed
    assert renamed_item["color"] == traits.DEFAULT_TRAIT_COLOR
    assert renamed_item["archived"] is False


def test_trait_description_metadata_is_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr(traits, "TRAIT_DIR", tmp_path / "traits")
    source = tmp_path / "upload.py"
    source.write_text('{"Original": {"name": "Original", "bodies": {"Moon": 1}}}', encoding="utf-8")

    installed = traits.install_trait_file(source, "Described Trait")
    traits.set_trait_description(installed, "  A custom trait description.  ")

    item = traits.list_traits()[0]
    assert item["description"] == "A custom trait description."
    assert item["profile"]["description"] == "A custom trait description."

    renamed = traits.rename_trait(installed, "Renamed Described Trait")
    assert traits.list_traits()[0]["path"] == renamed
    assert traits.list_traits()[0]["description"] == "A custom trait description."


def test_install_trait_file_preserves_samples_description_and_hash_comments(tmp_path, monkeypatch):
    monkeypatch.setattr(traits, "TRAIT_DIR", tmp_path / "traits")
    source = tmp_path / "upload.py"
    source.write_text(
        '''TRAITS = {
    "Original": {  # cohort note
        "name": "Original",
        "description": "Uploaded description.",
        "samples": 14,
        "houses": {
            "9": 4,  # dogmatic sample note
        },
    },
}
''',
        encoding="utf-8",
    )

    installed = traits.install_trait_file(source, "Uploaded Trait")
    saved_text = installed.read_text(encoding="utf-8")
    item = traits.list_traits()[0]

    assert item["profile"]["samples"] == 14
    assert item["description"] == "Uploaded description."
    assert item["profile"]["description"] == "Uploaded description."
    assert "// # cohort note" in saved_text
    assert "// # dogmatic sample note" in saved_text

    renamed = traits.rename_trait(installed, "Renamed Uploaded Trait")
    renamed_text = renamed.read_text(encoding="utf-8")

    assert traits.list_traits()[0]["profile"]["samples"] == 14
    assert "// # cohort note" in renamed_text
    assert "// # dogmatic sample note" in renamed_text


def test_install_trait_file_ignores_hashes_inside_multiline_strings(tmp_path, monkeypatch):
    monkeypatch.setattr(traits, "TRAIT_DIR", tmp_path / "traits")
    source = tmp_path / "upload.py"
    source.write_text(
        '''TRAITS = {
    "Original": {
        "name": "Original",
        "description": """Line one
# this is part of the description, not a comment
Line three""",
        "samples": 3,  # real sample note
    },
}
''',
        encoding="utf-8",
    )

    installed = traits.install_trait_file(source, "Multiline Trait")
    saved_text = installed.read_text(encoding="utf-8")

    assert "// # real sample note" in saved_text
    assert "// # this is part of the description" not in saved_text
    assert traits.list_traits()[0]["profile"]["description"].startswith("Line one\n# this is part")


def test_list_traits_logs_and_skips_corrupt_trait_files(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(traits, "TRAIT_DIR", tmp_path)
    good = tmp_path / "good.json"
    good.write_text('{"Good": {"name": "Good", "bodies": {"Moon": 1}}}', encoding="utf-8")
    corrupt = tmp_path / "broken.json"
    corrupt.write_text('{"Broken": ', encoding="utf-8")

    caplog.set_level("DEBUG", logger="ephemeraldaddy.analysis.traits")

    items = traits.list_traits(skip_corrupt=True)

    assert [item["name"] for item in items] == ["Good"]
    assert "Traits panel skipped corrupt trait file" in caplog.text
    assert str(corrupt) in caplog.text


def test_list_traits_can_raise_for_corrupt_trait_files(tmp_path, monkeypatch):
    monkeypatch.setattr(traits, "TRAIT_DIR", tmp_path)
    corrupt = tmp_path / "broken.json"
    corrupt.write_text('{"Broken": ', encoding="utf-8")

    try:
        traits.list_traits(skip_corrupt=False)
    except Exception:
        pass
    else:
        raise AssertionError("Expected corrupt trait file to raise when skip_corrupt is False")
