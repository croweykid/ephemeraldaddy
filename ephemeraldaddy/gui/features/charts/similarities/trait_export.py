"""Final builder for reusable Similarities Analysis trait exports."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable, Mapping
from typing import Any

from ephemeraldaddy.gui.features.charts.similarities_export import (
    build_similarities_json_export_payload,
)

from .cohort_metadata import inject_trait_cohort_metadata


def build_similarities_trait_export_payload(
    selection_name: str,
    export_sections: Any,
    *,
    sample_uids: Iterable[object] = (),
    gender_distribution: Mapping[str, Any] | None = None,
) -> OrderedDict:
    """Build a profile-shaped export with explicit source-sample metadata.

    The lower-level Similarities payload builder remains responsible for factor
    normalization.  This final builder owns reusable Trait metadata so the file
    export path does not depend on replacing builder globals at runtime.
    Two-chart Dissimilarity bundles remain unchanged because the metadata
    injector deliberately ignores non-Trait bundles.
    """
    payload = build_similarities_json_export_payload(selection_name, export_sections)
    inject_trait_cohort_metadata(
        payload,
        selection_name,
        sample_uids=sample_uids,
        gender_distribution=gender_distribution,
    )
    return payload
