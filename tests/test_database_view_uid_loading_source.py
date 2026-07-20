from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()


def _indented_method_source(source: str, name: str) -> str:
    start = source.index(f"    def {name}")
    next_method = source.find("\n    def ", start + 1)
    end = next_method if next_method != -1 else len(source)
    return source[start:end]


def test_database_view_loads_selected_chart_by_uid_without_metadata_role_collision():
    populate_source = APP_SOURCE.split("item = QListWidgetItem(label)", 1)[1].split(
        "is_hypothetical = _chart_row_is_hypothetical", 1
    )[0]
    assert "item.setData(Qt.UserRole + 2" in populate_source
    metadata_source = APP_SOURCE.split("item.setData(\n                    Qt.UserRole + 1", 1)[1].split(
        "\n                self.list_widget.addItem", 1
    )[0]
    assert '"raw_name"' in metadata_source
    load_source = _indented_method_source(APP_SOURCE, "_load_chart_from_item")
    assert "chart_uid = str(item.data(Qt.UserRole + 2)" in load_source
    assert "parent.load_chart_by_uid(chart_uid)" in load_source
