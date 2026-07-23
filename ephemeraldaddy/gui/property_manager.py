from __future__ import annotations

# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.

from typing import Any

from PySide6.QtCore import Qt, QTimer

from ephemeraldaddy.core.db import (
    apply_metadata_label_change,
    get_metadata_label_usage,
    parse_relationship_types,
    parse_sentiments,
    parse_tags,
)
from ephemeraldaddy.gui.dev_tools import ManageMetadataLabelsDialog
from ephemeraldaddy.gui.features.charts.tag_search import tag_matches_filter
from ephemeraldaddy.gui.features.charts.collections import (
    DEFAULT_COLLECTION_OPTIONS,
    chart_belongs_to_collection,
    normalize_collection_id,
)


class PropertyManagerCoordinator:
    """Lightweight coordinator that keeps property-manager specifics out of app.py."""

    def __init__(self, host: Any) -> None:
        self._host = host
        self._needs_refresh_after_close = False

    def _mark_needs_refresh_after_close(self) -> None:
        self._needs_refresh_after_close = True

    def _queue_embedded_refresh_after_reload(self) -> None:
        self._mark_needs_refresh_after_close()
        QTimer.singleShot(0, self.refresh_after_close)

    def create_widget(
        self,
        *,
        parent: Any | None = None,
        initial_field: str = ManageMetadataLabelsDialog.FIELD_TAGS,
        embedded: bool = False,
    ) -> ManageMetadataLabelsDialog:
        dialog = ManageMetadataLabelsDialog(
            parent=parent or self._host,
            load_usage=self.load_usage,
            apply_change=apply_metadata_label_change,
            label_limit=32767,
            load_chart_names=self.chart_names,
            # The Property Manager can rename/delete labels while Qt item views in
            # the dialog still hold selected/dragged items.  Do not refresh the
            # host chart model from inside the dialog's rename/reload cycle; on
            # some platforms that rebuilds views while Qt is still unwinding the
            # completed edit and can trigger a native crash.  Standalone dialogs
            # flush after close; the Settings-embedded manager has no normal
            # finished signal, so it queues the flush until after its reload
            # returns to the Qt event loop.
            refresh_chart_context=(
                self._queue_embedded_refresh_after_reload
                if embedded
                else self._mark_needs_refresh_after_close
            ),
            collection_actions={
                "create": self._host._on_create_custom_collection,
                "rename": self._host._on_rename_custom_collection_by_id,
                "delete": self._host._on_delete_custom_collection_by_id,
                "add_selected": self._host._on_add_selection_to_collection_by_id,
                "remove_selected": self._host._on_remove_selection_from_collection_by_id,
            },
            settings=getattr(self._host, "_settings", None),
            initial_field=initial_field,
            lock_field=False,
            window_title="Property Manager",
            show_close_button=not embedded,
            window_flags=Qt.Widget if embedded else Qt.Dialog,
        )
        if embedded:
            dialog.setWindowModality(Qt.NonModal)
            dialog.setSizeGripEnabled(False)
        return dialog

    def launch(
        self,
        initial_field: str = ManageMetadataLabelsDialog.FIELD_TAGS,
    ) -> None:
        dialog = self.create_widget(initial_field=initial_field)
        dialog.exec()
        self.refresh_after_close()

    def refresh_after_close(self) -> None:
        needs_refresh = self._needs_refresh_after_close
        self._needs_refresh_after_close = False
        self._host._update_tag_completers()
        self._host._refresh_charts(
            refresh_metrics=True,
            force_full_analysis_refresh=needs_refresh,
            refresh_tag_completers=False,
        )

    def load_usage(self) -> dict[str, list[dict[str, int | str]]]:
        usage = get_metadata_label_usage()
        # Relationship labels should disappear fully after rename/delete.
        usage[ManageMetadataLabelsDialog.FIELD_RELATIONSHIPS] = [
            row
            for row in usage.get(ManageMetadataLabelsDialog.FIELD_RELATIONSHIPS, [])
            if int(row.get("count", 0) or 0) > 0
        ]
        usage[ManageMetadataLabelsDialog.FIELD_COLLECTIONS] = self._collection_usage_rows()
        return usage

    def _collection_usage_rows(self) -> list[dict[str, int | str]]:
        rows = [
            normalized
            for row in self._host._chart_rows
            if (normalized := self._host._normalize_chart_row(row)) is not None
        ]
        collection_rows: list[dict[str, int | str]] = []
        for collection_label, collection_id in DEFAULT_COLLECTION_OPTIONS:
            count = 0
            for row in rows:
                chart = self._host._get_chart_for_filter(row[0])
                if chart_belongs_to_collection(
                    collection_id,
                    chart=chart,
                    source=row[14],
                    custom_collections=self._host._custom_collections,
                    chart_id=row[0],
                ):
                    count += 1
            collection_rows.append(
                {"label": collection_label, "key": collection_id, "count": count, "editable": False}
            )
        for custom_collection in sorted(
            self._host._custom_collections.values(),
            key=lambda collection: collection.name.casefold(),
        ):
            collection_rows.append(
                {
                    "label": custom_collection.name,
                    "key": custom_collection.collection_id,
                    "count": len(custom_collection.chart_ids),
                    "editable": True,
                }
            )
        return collection_rows

    def chart_names(self, field: str, label: str, key: str) -> list[str]:
        def _values_to_csv(values: object) -> str:
            if isinstance(values, str):
                return values
            if values is None:
                return ""
            try:
                return ",".join(str(value) for value in values if isinstance(value, str))
            except TypeError:
                return ""

        matches: list[str] = []
        rows = [
            normalized
            for row in self._host._chart_rows
            if (normalized := self._host._normalize_chart_row(row)) is not None
        ]
        for row in rows:
            chart_id = row[0]
            chart_name = str(row[1] or row[2] or f"Chart {chart_id}")
            chart = self._host._get_chart_for_filter(chart_id)
            if chart is None:
                continue
            if field == ManageMetadataLabelsDialog.FIELD_TAGS:
                tags = {
                    tag.casefold()
                    for tag in parse_tags(_values_to_csv(getattr(chart, "tags", [])))
                }
                if any(tag_matches_filter(tag, label) for tag in tags):
                    matches.append(chart_name)
            elif field == ManageMetadataLabelsDialog.FIELD_SENTIMENTS:
                sentiments = set(
                    parse_sentiments(_values_to_csv(getattr(chart, "sentiments", [])))
                )
                if label in sentiments:
                    matches.append(chart_name)
            elif field == ManageMetadataLabelsDialog.FIELD_RELATIONSHIPS:
                relationships = set(
                    parse_relationship_types(
                        _values_to_csv(getattr(chart, "relationship_types", []))
                    )
                )
                if label in relationships:
                    matches.append(chart_name)
            elif field == ManageMetadataLabelsDialog.FIELD_COLLECTIONS:
                collection_id = normalize_collection_id(key)
                if collection_id and chart_belongs_to_collection(
                    collection_id,
                    chart=chart,
                    source=row[14],
                    custom_collections=self._host._custom_collections,
                    chart_id=chart_id,
                ):
                    matches.append(chart_name)
        return sorted(matches, key=str.casefold)
