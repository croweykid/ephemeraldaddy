from ephemeraldaddy.gui.features.database_view.collection_labels import (
    custom_collection_label,
)


def test_custom_collection_label_counts_only_live_uid_members():
    assert (
        custom_collection_label(
            "Test",
            {"UID-A", "uid-b", "ORPHAN-UID"},
            {"uid-a", "UID-B", "UID-C"},
        )
        == "Test (2)"
    )
