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


def test_batch_typology_patch_preserves_lowercase_and_x_mbti_slots():
    chart = SimpleNamespace(
        enneagram_type=None,
        tritype=None,
        mbti=["i", "x", "t", "p"],
    )

    patch = typology_patch_for_chart(
        chart,
        enneagram_values=(None, None),
        tritype_values=(None, None, None),
        mbti_values=(None, None, None, "J"),
    )

    assert patch == {"mbti": ["i", "x", "t", "J"]}


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


def test_typology_selection_summarizes_blank_and_populated_mbti_slots():
    charts = [
        SimpleNamespace(mbti=["?", "?", "F", "J"]),
        SimpleNamespace(mbti=["?", "S", "F", "J"]),
    ]

    summary = summarize_typology_selection(charts)

    assert summary is not None
    assert summary.mbti == (None, MIXED, "F", "J")


def test_typology_selection_summarizes_all_requested_mbti_combinations():
    charts = [
        SimpleNamespace(mbti=list("ISTJ")),
        SimpleNamespace(mbti=list("ESTJ")),
        SimpleNamespace(mbti=["?", "?", "F", "J"]),
        SimpleNamespace(mbti=["?", "S", "F", "J"]),
    ]

    two_populated = summarize_typology_selection(charts[:2])
    all_four = summarize_typology_selection(charts)

    assert two_populated is not None
    assert two_populated.mbti == (MIXED, "S", "T", "J")
    assert all_four is not None
    assert all_four.mbti == (MIXED, MIXED, MIXED, "J")


def test_batch_typology_hydrates_only_when_selection_changes():
    source = Path("ephemeraldaddy/gui/app.py").read_text()
    start = source.index("    def _update_batch_edit_state")
    end = source.index("    def _update_batch_tag_state", start)
    method = source[start:end]

    assert '"_batch_last_typology_selection_uids"' in method
    assert (
        'if typology_selection_changed and hasattr(self, "batch_typology_editor"):'
        in method
    )
    assert "self._batch_last_typology_selection_uids = set(chart_uid_set)" in method


def test_batch_typology_selection_cache_is_independent_from_other_batch_fields():
    source = Path("ephemeraldaddy/gui/app.py").read_text()
    start = source.index("    def _update_batch_edit_state")
    end = source.index("    def _update_batch_tag_state", start)
    method = source[start:end]

    comparison_start = method.index("typology_selection_changed =")
    comparison_end = method.index("preserve_lucygoosey_metrics", comparison_start)
    comparison = method[comparison_start:comparison_end]

    assert "_batch_last_typology_selection_uids" in comparison
    assert "_batch_last_selection_uids" not in comparison


def test_chart_editor_lightweight_save_reads_typology_controls_before_persisting():
    source = Path("ephemeraldaddy/gui/app.py").read_text()
    start = source.index("    def on_update_chart")
    lightweight_start = source.index("        if not recalculate_chart", start)
    lightweight_end = source.index(
        "        if chart is None and is_placeholder",
        lightweight_start,
    )
    lightweight_path = source[lightweight_start:lightweight_end]

    assert (
        "chart.enneagram_type,\n"
        "                    chart.tritype,\n"
        "                    chart.mbti,\n"
        "                ) = get_chart_view_typology(self)"
    ) in lightweight_path
