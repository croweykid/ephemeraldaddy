from ephemeraldaddy.gui.features.charts import euphonics


def test_euphonics_matches_sort_by_frequency_then_first_appearance(monkeypatch):
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

    assert [match["id"] for match in matches] == ["A", "B", "C"]
    assert [match["occurrences"] for match in matches] == [3, 2, 1]
    assert all(str(match["color"]).startswith("#") for match in matches)


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
