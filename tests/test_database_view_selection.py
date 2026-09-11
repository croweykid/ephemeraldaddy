from ephemeraldaddy.gui.features.database_view.selection import (
    DatabaseSelectionController,
    DatabaseSelectionModel,
)


def test_model_normalizes_and_deduplicates_uid_selection_in_order():
    model = DatabaseSelectionModel()
    model.replace([" uid-b ", "UID-A", "uid-b", None])

    assert model.selected_uids == ["UID-B", "UID-A"]
    assert model.selected_uid_set == {"UID-A", "UID-B"}


def test_model_normalizes_constructor_identity_state():
    model = DatabaseSelectionModel(
        selected_uids=[" uid-a ", "UID-A"],
        anchor_uid=" uid-a ",
        prior_single_selection=" uid-b ",
    )

    assert model.selected_uids == ["UID-A"]
    assert model.anchor_uid == "UID-A"
    assert model.prior_single_selection == "UID-B"


def test_filtered_merge_preserves_logical_selection_hidden_from_view():
    model = DatabaseSelectionModel(selected_uids=["HIDDEN", "VISIBLE-A"])
    controller = DatabaseSelectionController(model)

    result = controller.merge_visible_selection(
        visible_uids=["VISIBLE-A", "VISIBLE-B"],
        selected_visible_uids=["VISIBLE-B"],
        replace=False,
    )

    assert result == ["HIDDEN", "VISIBLE-B"]


def test_replace_discards_hidden_selection_for_explicit_selection_action():
    model = DatabaseSelectionModel(selected_uids=["HIDDEN", "VISIBLE-A"])
    controller = DatabaseSelectionController(model)

    result = controller.merge_visible_selection(
        visible_uids=["VISIBLE-A", "VISIBLE-B"],
        selected_visible_uids=["VISIBLE-B"],
        replace=True,
    )

    assert result == ["VISIBLE-B"]


def test_reconcile_removes_deleted_uids_without_reordering_survivors():
    model = DatabaseSelectionModel(selected_uids=["UID-C", "UID-A", "UID-B"])

    assert model.reconcile(["UID-B", "UID-C"]) is True
    assert model.selected_uids == ["UID-C", "UID-B"]
    assert model.reconcile(["UID-C", "UID-B"]) is False


def test_reconcile_does_not_make_deleted_single_selection_undoable():
    model = DatabaseSelectionModel(selected_uids=["DELETED"])

    assert model.reconcile(["OTHER"]) is True
    assert model.restore_prior_single_selection() is None


def test_single_selection_can_be_restored_once_after_clear():
    model = DatabaseSelectionModel(selected_uids=["UID-A"])
    model.replace([], remember_deselection=True)

    assert model.restore_prior_single_selection() == ["UID-A"]
    assert model.selected_uids == ["UID-A"]
    assert model.restore_prior_single_selection() is None
