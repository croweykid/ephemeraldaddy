from ephemeraldaddy.core import material_facts


def test_personal_identifiers_are_saved_by_chart_uid(tmp_path, monkeypatch):
    monkeypatch.setattr(material_facts, "DB_PATH", tmp_path / "charts.db")

    material_facts.save_personal_identifiers_by_uid(
        "abc12345uid",
        {"addresses": "  123 Main  ", "emails": "", "websites": "https://example.com", "phone_numbers": ""},
    )

    payload = material_facts._load_sidecar(material_facts.personal_identifiers_path())
    assert "ABC12345UID" in payload
    assert "123" not in payload
    assert material_facts.load_personal_identifiers_by_uid("ABC12345UID") == {
        "addresses": "123 Main",
        "emails": "",
        "websites": "https://example.com",
        "phone_numbers": "",
    }


def test_legacy_personal_identifier_id_key_migrates_to_uid(tmp_path, monkeypatch):
    monkeypatch.setattr(material_facts, "DB_PATH", tmp_path / "charts.db")
    monkeypatch.setattr(material_facts, "get_chart_uid", lambda chart_id: "MIGRATEDUID00001" if chart_id == 7 else None)
    material_facts._save_sidecar(
        material_facts.personal_identifiers_path(),
        {"7": {"addresses": "Old Address", "emails": "", "websites": "", "phone_numbers": ""}},
    )

    facts = material_facts.load_personal_identifiers(7)
    payload = material_facts._load_sidecar(material_facts.personal_identifiers_path())

    assert facts["addresses"] == "Old Address"
    assert "7" not in payload
    assert payload["MIGRATEDUID00001"]["addresses"] == "Old Address"
