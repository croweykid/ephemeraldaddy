from ephemeraldaddy.gui.features.charts import euphonics


def test_euphonics_matches_sort_by_first_appearance(monkeypatch):
    monkeypatch.setattr(
        euphonics,
        "euphonics_entries",
        lambda: [
            {"id": "A", "title": "A title", "summary": "A summary", "_tokens": {"a"}},
            {"id": "B", "title": "B title", "summary": "B summary", "_tokens": {"b"}},
            {"id": "C", "title": "C title", "summary": "C summary", "_tokens": {"c"}},
        ],
    )

    matches = euphonics.euphonics_matches_for_name("cababa")

    assert [match["id"] for match in matches] == ["C", "A", "B"]
    assert [match["occurrences"] for match in matches] == [1, 3, 2]
    assert all(str(match["color"]).startswith("#") for match in matches)


def test_y_initial_only_matches_name_parts_that_begin_with_y(monkeypatch):
    monkeypatch.setattr(
        euphonics,
        "euphonics_entries",
        lambda: [
            {
                "id": "Y_INITIAL",
                "title": "Initial Y",
                "summary": "Y summary",
                "_tokens": {"y", "yowling", "j"},
            }
        ],
    )

    assert euphonics.euphonics_matches_for_name("Maya") == []

    matches = euphonics.euphonics_matches_for_name("Maya Young")

    assert len(matches) == 1
    assert matches[0]["id"] == "Y_INITIAL"
    assert matches[0]["matched_token"] == "Y"
    assert matches[0]["first_index"] == 4


def test_y_final_only_matches_when_name_ends_with_y(monkeypatch):
    monkeypatch.setattr(
        euphonics,
        "euphonics_entries",
        lambda: [
            {
                "id": "Y_FINAL",
                "title": "Final Y",
                "summary": "Y summary",
                "_tokens": {"y", "merry", "familiarity"},
            }
        ],
    )

    assert euphonics.euphonics_matches_for_name("Yvonne Merrick") == []

    matches = euphonics.euphonics_matches_for_name("Yvonne Merry")

    assert len(matches) == 1
    assert matches[0]["id"] == "Y_FINAL"
    assert matches[0]["matched_token"] == "Y"
    assert matches[0]["first_index"] == 10


def test_render_euphonics_html_shows_occurrence_count_and_sound_color(monkeypatch):
    monkeypatch.setattr(
        euphonics,
        "euphonics_matches_for_name",
        lambda _name: [
            {
                "id": "A",
                "title": "A title",
                "summary": "A summary",
                "matched_token": "A",
                "occurrences": 3,
                "first_index": 1,
                "color": "#ff8fa3",
            }
        ],
    )

    rendered = euphonics.render_euphonics_html("banana")

    assert "(found: A x 3)" in rendered
    assert "color:#ff8fa3" in rendered
    assert "color:#9bd3ff" in rendered
