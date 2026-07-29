import ast
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text(
    encoding="utf-8"
)


def _class_methods(class_name: str) -> set[str]:
    module = ast.parse(SOURCE)
    class_node = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    return {
        node.name
        for node in class_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_cached_settings_dialog_refreshes_algorithm_accuracy_ranking():
    assert "_ensure_settings_dialog" in _class_methods("ManageChartsDialog")
    assert "_refresh_similarity_algorithm_accuracy_label" in _class_methods(
        "ManageChartsDialog"
    )
    ensure_method = SOURCE.split("def _ensure_settings_dialog", 1)[1].split(
        "def _refresh_plugins_status_labels", 1
    )[0]
    cached_branch = ensure_method.split("if self._settings_dialog is not None:", 1)[1]
    assert "self._refresh_similarity_algorithm_accuracy_label()" in cached_branch


def test_saved_observation_refreshes_open_accuracy_ranking():
    save_method = SOURCE.split(
        "def _on_similar_chart_popout_perceived_accuracy_changed", 1
    )[1].split("def _on_similar_chart_popout_make_collection_clicked", 1)[0]
    assert "append_similarity_accuracy_observation(" in save_method
    assert "self._refresh_similarity_algorithm_accuracy_label()" in save_method


def test_accuracy_ranking_label_is_retained_by_settings_owner():
    assert (
        'self._similarity_algorithm_accuracy_label = similarity_controls[\n'
        '            "algorithm_accuracy_label"\n'
        "        ]"
    ) in SOURCE
