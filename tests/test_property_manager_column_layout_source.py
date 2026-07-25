from pathlib import Path


DEV_TOOLS_SOURCE = Path("ephemeraldaddy/gui/dev_tools.py").read_text()


def test_only_tags_manager_keeps_the_uncategorized_third_column() -> None:
    dialog_source = DEV_TOOLS_SOURCE.split("class ManageMetadataLabelsDialog", 1)[1]
    setup = dialog_source.split("split_layout = QHBoxLayout()", 1)[1].split(
        "layout.addLayout(split_layout, 1)", 1
    )[0]
    refresh = dialog_source.split("def _refresh_list(self)", 1)[1].split(
        "def _selected_label(self)", 1
    )[0]

    assert "self._unsorted_panel_widget = QWidget(self)" in setup
    assert "split_layout.addWidget(self._unsorted_panel_widget, 1)" in setup
    assert "split_layout.addLayout(self._unsorted_panel, 1)" not in setup
    assert "tags_mode = self._active_field() == self.FIELD_TAGS" in refresh
    assert "self._unsorted_panel_widget.setVisible(tags_mode)" in refresh
