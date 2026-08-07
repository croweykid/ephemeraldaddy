from pathlib import Path
from types import SimpleNamespace

from ephemeraldaddy.gui.features.database_view.batch_editor.typology import typology_patch_for_chart
from ephemeraldaddy.gui.features.database_view.typology_selection import (
    MIXED,
    summarize_typology_selection,
)


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


def test_typology_selection_summarizes_shared_and_mixed_slots():
    charts = [
        SimpleNamespace(enneagram_type=[2, 1], tritype=[2, 5, 8], mbti=list("ESTJ")),
        SimpleNamespace(enneagram_type=[2, 1], tritype=[2, 6, 8], mbti=list("ISTJ")),
        SimpleNamespace(enneagram_type=[2, 3], tritype=[2, 6, 9], mbti=list("ISFP")),
    ]

    summary = summarize_typology_selection(charts)

    assert summary is not None
    assert summary.enneagram == (2, MIXED)
    assert summary.tritype == (2, MIXED, MIXED)
    assert summary.mbti == (MIXED, "S", MIXED, MIXED)


def test_batch_typology_hydrates_only_when_selection_changes():
    source = Path("ephemeraldaddy/gui/app.py").read_text()
    start = source.index("    def _update_batch_edit_state")
    end = source.index("    def _update_batch_tag_state", start)
    method = source[start:end]

    assert "typology_selection_changed = chart_uid_set != self._batch_last_selection_uids" in method
    assert (
        'if typology_selection_changed and hasattr(self, "batch_typology_editor"):'
        in method
    )
