from types import SimpleNamespace

from ephemeraldaddy.gui.features.database_view.batch_editor.typology import typology_patch_for_chart


def test_batch_typology_patch_preserves_unspecified_slots():
    chart = SimpleNamespace(
        enneagram_type=[5, 4],
        tritype=[5, 9, 2],
        mbti=["I", "N", "T", "P"],
    )

    patch = typology_patch_for_chart(
        chart,
        enneagram_values=(None, 6),
        tritype_values=(8, None, None),
        mbti_values=(None, None, "F", None),
    )

    assert patch == {
        "enneagram_type": [5, 6],
        "tritype": [8, 9, 2],
        "mbti": ["I", "N", "F", "P"],
    }


def test_batch_typology_patch_omits_wholly_unchanged_groups():
    chart = SimpleNamespace(
        enneagram_type=[5, 4],
        tritype=[5, 9, 2],
        mbti=["I", "N", "T", "P"],
    )

    patch = typology_patch_for_chart(
        chart,
        enneagram_values=(None, None),
        tritype_values=(None, None, None),
        mbti_values=(None, "S", None, None),
    )

    assert patch == {"mbti": ["I", "S", "T", "P"]}


def test_batch_typology_patch_normalizes_missing_existing_metadata():
    chart = SimpleNamespace(enneagram_type=None, tritype=[], mbti=None)

    patch = typology_patch_for_chart(
        chart,
        enneagram_values=(7, None),
        tritype_values=(None, 4, None),
        mbti_values=("E", None, None, None),
    )

    assert patch == {
        "enneagram_type": [7, 0],
        "tritype": [0, 4, 0],
        "mbti": ["E", "?", "?", "?"],
    }
