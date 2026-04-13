from __future__ import annotations

from typing import Any

from ephemeraldaddy.core.db import (
    apply_metadata_label_change,
    get_metadata_label_usage,
    parse_relationship_types,
    parse_sentiments,
    parse_tags,
)
from ephemeraldaddy.gui.dev_tools import ManageMetadataLabelsDialog
from ephemeraldaddy.gui.features.charts.collections import (
    DEFAULT_COLLECTION_OPTIONS,
    chart_belongs_to_collection,
    normalize_collection_id,
)


class PropertyManagerCoordinator:
    """Lightweight coordinator that keeps property-manager specifics out of app.py."""

    def __init__(self, host: Any) -> None:
        self._host = host

    def launch(
        self,
        initial_field: str = ManageMetadataLabelsDialog.FIELD_TAGS,
    ) -> None:
        dialog = ManageMetadataLabelsDialog(
            parent=self._host,
            load_usage=self.load_usage,
            apply_change=apply_metadata_label_change,
            label_limit=32767,
            load_chart_names=self.chart_names,
            collection_actions={
                "create": self._host._on_create_custom_collection,
                "rename": self._host._on_rename_custom_collection_by_id,
                "delete": self._host._on_delete_custom_collection_by_id,
                "add_selected": self._host._on_add_selection_to_collection_by_id,
                "remove_selected": self._host._on_remove_selection_from_collection_by_id,
            },
            initial_field=initial_field,
            lock_field=False,
            window_title="Property Manager",
        )
        dialog.exec()
        self._host._update_tag_completers()
        self._host._refresh_charts(refresh_metrics=True, force_full_analysis_refresh=True)

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
                if label.casefold() in tags:
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
