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
