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
