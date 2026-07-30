from pathlib import Path


DEV_TOOLS_SOURCE = Path("ephemeraldaddy/gui/dev_tools.py").read_text()


def test_only_tags_manager_keeps_the_uncategorized_third_column() -> None:
    dialog_source = DEV_TOOLS_SOURCE.split("class ManageMetadataLabelsDialog", 1)[1]
    setup = dialog_source.split("self._column_splitter = QSplitter", 1)[1].split(
        "layout.addWidget(self._column_splitter, 1)", 1
    )[0]
    refresh = dialog_source.split("def _refresh_list(self)", 1)[1].split(
        "def _selected_label(self)", 1
    )[0]

    assert "self._unsorted_panel_widget = QWidget(self)" in setup
    assert "self._column_splitter.addWidget(self._unsorted_panel_widget)" in setup
    assert "self._column_splitter.addWidget(middle_panel_widget)" in setup
    assert "self._column_splitter.addWidget(self._right_panel_widget)" in setup
    assert "tags_mode = self._active_field() == self.FIELD_TAGS" in refresh
    assert "self._unsorted_panel_widget.setVisible(tags_mode)" in refresh


def test_property_manager_column_widths_are_adjustable_and_persisted() -> None:
    dialog_source = DEV_TOOLS_SOURCE.split("class ManageMetadataLabelsDialog", 1)[1]

    assert "QSplitter(Qt.Horizontal, self)" in dialog_source
    assert "splitterMoved.connect(self._save_column_widths)" in dialog_source
    assert "settings.setValue(self._column_widths_key(), splitter.sizes())" in dialog_source
    assert "self._column_splitter.setSizes(sizes)" in dialog_source
    assert "setSectionResizeMode(QHeaderView.Interactive)" in dialog_source
    assert "sectionResized.connect(" in dialog_source
    assert "self._restore_preset_column_widths()" in dialog_source
    assert "setSectionResizeMode(0, QHeaderView.Stretch)" in dialog_source
    assert "setTextElideMode(Qt.ElideNone)" in DEV_TOOLS_SOURCE
    assert "def _fit_preset_columns_to_viewport(self)" in dialog_source
    assert "setSectionResizeMode(2, QHeaderView.Stretch)" in dialog_source
