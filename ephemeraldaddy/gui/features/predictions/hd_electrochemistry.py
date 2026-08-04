"""Chart Editor presentation for Human Design electrochemistry predictions."""

from __future__ import annotations

import html
import urllib.parse

from PySide6.QtCore import QSettings, QSignalBlocker, QTimer, Qt
from PySide6.QtWidgets import QComboBox, QLabel

from ephemeraldaddy.analysis.human_design import derive_human_design_profile
from ephemeraldaddy.analysis.human_design_synastry import (
    HD_ELECTROCHEMISTRY_MAX_SCORE,
    HD_SYNASTRY_GENDER_METHOD_IDENTITY as HD_ELECTROCHEMISTRY_GENDER_METHOD_IDENTITY,
    HD_SYNASTRY_GENDER_METHOD_SEX as HD_ELECTROCHEMISTRY_GENDER_METHOD_SEX,
    filter_hd_synastry_candidates as filter_hd_electrochemistry_candidates,
    normalize_gates,
    normalize_hd_synastry_gender_filter as normalize_hd_electrochemistry_gender_filter,
    rank_human_design_synastry as rank_human_design_electrochemistry,
)
from ephemeraldaddy.core.db import (
    list_human_design_synastry_candidates as list_human_design_electrochemistry_candidates,
)
from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.gui.features.charts.collections import (
    DEFAULT_COLLECTION_ALL,
    DEFAULT_COLLECTION_OPTIONS,
    CustomCollection,
    chart_belongs_to_collection,
    collection_scope_cache_signature,
    normalize_collection_id,
)
from ephemeraldaddy.gui.style import (
    SETTINGS_APP,
    SETTINGS_ORG,
    apply_chart_info_link_cursor,
    houses_unknown_note_html,
)
from ephemeraldaddy.gui.features.predictions.hd_electrochemistry_norms import (
    current_human_design_electrochemistry_norms,
    human_design_electrochemistry_norms_are_building,
    request_human_design_electrochemistry_norms,
)


HD_ELECTROCHEMISTRY_SUBHEADER = (
    "Top 10 charts ranked as 'theoretically most compatible' by Human Design "
    "channel/center synastry alone. This says nothing of shared values, means "
    "or other lifestyle factors."
)

SETTINGS_KEY_GENDERED_RESULTS_METHOD = "chart_calculation/gendered_results_method"


def reload_hd_electrochemistry_custom_collections(
    owner: object,
) -> dict[str, CustomCollection]:
    """Reload the Chart Editor's collection snapshot from shared settings."""
    loader = getattr(owner, "_load_custom_collections_from_settings", None)
    if callable(loader):
        custom_collections = loader()
        setattr(owner, "_custom_collections", custom_collections)
    else:
        custom_collections = getattr(owner, "_custom_collections", {}) or {}
    return custom_collections


def hd_electrochemistry_collection_options(owner: object) -> list[tuple[str, str]]:
    """Return built-in and current custom collection choices, with All first."""
    custom_collections = reload_hd_electrochemistry_custom_collections(owner)
    return list(DEFAULT_COLLECTION_OPTIONS) + [
        (collection.name, collection.collection_id)
        for collection in sorted(custom_collections.values(), key=lambda item: item.name.casefold())
    ]


def populate_hd_electrochemistry_collection_combo(owner: object, combo: QComboBox) -> None:
    """Populate the collection selector while preserving its UID-first scope."""
    selected = normalize_collection_id(
        getattr(owner, "hd_electrochemistry_collection_filter", DEFAULT_COLLECTION_ALL)
    )
    blocker = QSignalBlocker(combo)
    try:
        combo.clear()
        for label, collection_id in hd_electrochemistry_collection_options(owner):
            combo.addItem(label, collection_id)
        index = combo.findData(selected)
        combo.setCurrentIndex(index if index >= 0 else 0)
    finally:
        del blocker
    setattr(
        owner,
        "hd_electrochemistry_collection_filter",
        combo.currentData() or DEFAULT_COLLECTION_ALL,
    )


def refresh_hd_electrochemistry_collections(owner: object) -> None:
    """Refresh collection choices/membership and invalidate the visible ranking."""
    combo = getattr(owner, "hd_electrochemistry_collection_combo", None)
    if isinstance(combo, QComboBox):
        populate_hd_electrochemistry_collection_combo(owner, combo)
    else:
        reload_hd_electrochemistry_custom_collections(owner)
    setattr(owner, "_hd_electrochemistry_last_render_token", None)
    chart = getattr(owner, "_latest_chart", None) or getattr(owner, "current_chart", None)
    if chart is not None and isinstance(
        getattr(owner, "hd_electrochemistry_prediction_label", None), QLabel
    ):
        render_hd_electrochemistry_predictions(owner, chart)


def normalize_gendered_results_method(value: object) -> str:
    """Normalize the appwide gender grouping preference."""
    return (
        HD_ELECTROCHEMISTRY_GENDER_METHOD_IDENTITY
        if str(value or "").strip().casefold() == HD_ELECTROCHEMISTRY_GENDER_METHOD_IDENTITY
        else HD_ELECTROCHEMISTRY_GENDER_METHOD_SEX
    )


def load_gendered_results_method() -> str:
    """Load the appwide gender grouping preference, defaulting to assigned sex."""
    settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
    return normalize_gendered_results_method(
        settings.value(SETTINGS_KEY_GENDERED_RESULTS_METHOD, HD_ELECTROCHEMISTRY_GENDER_METHOD_SEX)
    )


def save_gendered_results_method(value: object) -> str:
    """Persist and return the normalized appwide gender grouping preference."""
    normalized = normalize_gendered_results_method(value)
    QSettings(SETTINGS_ORG, SETTINGS_APP).setValue(SETTINGS_KEY_GENDERED_RESULTS_METHOD, normalized)
    return normalized

def resolve_hd_electrochemistry_gates(chart: object | None) -> frozenset[int]:
    """Return cached gates, deriving them when an older chart has no HD cache."""
    if chart is None:
        return frozenset()
    gates = normalize_gates(getattr(chart, "human_design_gates", None))
    if gates:
        return gates
    try:
        derived_gates, _lines, _channels, _hd_type = derive_human_design_profile(chart)
    except Exception:
        return frozenset()
    gates = normalize_gates(derived_gates)
    if gates:
        setattr(chart, "human_design_gates", sorted(gates))
    return gates


def hd_electrochemistry_subheader(chart: object | None) -> str:
    """Add the required reliability warning for unknown or rectified times."""
    if chart is None or not bool(getattr(chart, "birthtime_unknown", False)):
        return HD_ELECTROCHEMISTRY_SUBHEADER
    name = html.escape(str(getattr(chart, "name", "This chart") or "This chart"))
    return (
        HD_ELECTROCHEMISTRY_SUBHEADER
        + f"<br><br>Since {name}'s birth time is hypothetical, results may be dodgier than usual."
    )


def hd_electrochemistry_render_token(owner: object, chart: object | None) -> tuple[object, ...]:
    """Return the chart/database revision tuple that invalidates this ranking."""
    collection_id = normalize_collection_id(
        getattr(owner, "hd_electrochemistry_collection_filter", DEFAULT_COLLECTION_ALL)
    )
    custom_collections = reload_hd_electrochemistry_custom_collections(owner)
    selected_custom_collection = custom_collections.get(collection_id)
    collection_signature = collection_scope_cache_signature(
        collection_id,
        getattr(selected_custom_collection, "chart_uids", ()),
    )
    return (
        str(getattr(chart, "chart_uid", "") or "").strip().upper(),
        tuple(sorted(resolve_hd_electrochemistry_gates(chart))),
        bool(chart is not None and chart_uses_houses(chart)),
        normalize_hd_electrochemistry_gender_filter(getattr(owner, "hd_electrochemistry_gender_filter", "all")),
        load_gendered_results_method(),
        collection_signature,
        int(getattr(owner, "_database_metrics_cache_revision", 0) or 0),
    )


def hd_electrochemistry_predictions_are_current(owner: object, chart: object | None) -> bool:
    return getattr(owner, "_hd_electrochemistry_last_render_token", None) == hd_electrochemistry_render_token(owner, chart)


def _format_hd_electrochemistry_matches(matches: tuple, warning_lines: tuple[str, ...]) -> str:
    """Format source-relative rankings alongside persistent database-wide norms."""
    norms = current_human_design_electrochemistry_norms()
    lines = list(warning_lines)
    if norms is None:
        lines.append("Database-wide norms are being calculated in the background.")
    else:
        lines.append(
            f"Database-wide norms: {norms.sample_size:,} unique chart pairs; "
            f"median score {norms.median:g}/{HD_ELECTROCHEMISTRY_MAX_SCORE}."
        )
    for index, match in enumerate(matches, 1):
        display_name = match.name
        if match.alias and match.alias.casefold() != match.name.casefold():
            display_name += f" ({match.alias})"
        href = "chart-uid:" + urllib.parse.quote(match.chart_uid, safe="")
        uncertainty_html = " " + houses_unknown_note_html() if not match.uses_houses else ""
        chart_top_decile = " · top 10% for this chart" if match.percentile >= 90.0 else ""
        database_norms = ""
        if norms is not None and norms.sample_size:
            database_norms = (
                f"; database-wide {norms.percentile_for_score(match.score):.0f}th percentile"
            )
        lines.append(
            f'{index}. <a href="{href}" style="color: #cdb7ff;">'
            f"{html.escape(display_name)}</a>{uncertainty_html} "
            f'<span style="color: #aaa;">(score {match.score}/{HD_ELECTROCHEMISTRY_MAX_SCORE}: '
            f"{match.completed_channels} cross-chart channels + "
            f"{match.defined_centers} combined defined centers; "
            f"candidate median {match.population_median:g}, "
            f"{match.percentile:.0f}th percentile for this chart"
            f"{chart_top_decile}{database_norms})</span>"
        )
    return "<br>".join(lines)


def _poll_hd_electrochemistry_norms(
    label: QLabel,
    matches: tuple,
    warning_lines: tuple[str, ...],
    poll_token: str,
) -> None:
    """Refresh only the originating label after its background norms build."""
    if str(label.property("hdNormsPollToken") or "") != poll_token:
        return
    if human_design_electrochemistry_norms_are_building():
        QTimer.singleShot(
            250,
            lambda: _poll_hd_electrochemistry_norms(label, matches, warning_lines, poll_token),
        )
        return
    label.setText(_format_hd_electrochemistry_matches(matches, warning_lines))


def render_hd_electrochemistry_predictions(owner: object, chart: object | None) -> None:
    label = getattr(owner, "hd_electrochemistry_prediction_label", None)
    if not isinstance(label, QLabel) or chart is None:
        return
    render_token = hd_electrochemistry_render_token(owner, chart)
    if getattr(owner, "_hd_electrochemistry_last_render_token", None) == render_token:
        return
    chart_uid = str(getattr(chart, "chart_uid", "") or "").strip().upper()
    gates = resolve_hd_electrochemistry_gates(chart)
    subheader = getattr(owner, "hd_electrochemistry_prediction_subheader", None)
    if isinstance(subheader, QLabel):
        subheader.setText(hd_electrochemistry_subheader(chart))
    if not chart_uid or not gates:
        label.setText("Human Design gate data is unavailable for this chart.")
        setattr(owner, "_hd_electrochemistry_last_render_token", render_token)
        return
    gender_filter = normalize_hd_electrochemistry_gender_filter(
        getattr(owner, "hd_electrochemistry_gender_filter", "all")
    )
    available_candidates = list_human_design_electrochemistry_candidates()
    collection_id = normalize_collection_id(
        getattr(owner, "hd_electrochemistry_collection_filter", DEFAULT_COLLECTION_ALL)
    )
    custom_collections = getattr(owner, "_custom_collections", {}) or {}
    if collection_id != DEFAULT_COLLECTION_ALL:
        available_candidates = [
            candidate
            for candidate in available_candidates
            if chart_belongs_to_collection(
                collection_id,
                chart=candidate,
                source=candidate.source,
                custom_collections=custom_collections,
                chart_uid=candidate.chart_uid,
            )
        ]
    candidates = filter_hd_electrochemistry_candidates(
        available_candidates,
        gender_filter,
        load_gendered_results_method(),
    )
    database_revision = int(getattr(owner, "_database_metrics_cache_revision", 0) or 0)
    request_human_design_electrochemistry_norms(database_revision)
    matches = rank_human_design_electrochemistry(
        chart_uid,
        gates,
        candidates,
    )
    if not matches:
        other_candidates_are_available = any(
            str(candidate.chart_uid or "").strip().upper() != chart_uid
            for candidate in available_candidates
        )
        if gender_filter != "all" and other_candidates_are_available:
            label.setText(
                f"No charts matching the {html.escape(gender_filter.title())} filter "
                "have Human Design gate data."
            )
        else:
            label.setText("No other charts with Human Design gate data are available.")
        setattr(owner, "_hd_electrochemistry_last_render_token", render_token)
        return
    warning_lines = []
    if not chart_uses_houses(chart):
        warning_lines.append(
            "Ranked using this chart's default hypothetical time "
            + houses_unknown_note_html()
        )
    matches_tuple = tuple(matches)
    warning_lines_tuple = tuple(warning_lines)
    poll_token = repr(render_token)
    label.setProperty("hdNormsPollToken", poll_token)
    label.setText(_format_hd_electrochemistry_matches(matches_tuple, warning_lines_tuple))
    if human_design_electrochemistry_norms_are_building():
        QTimer.singleShot(
            250,
            lambda: _poll_hd_electrochemistry_norms(
                label,
                matches_tuple,
                warning_lines_tuple,
                poll_token,
            ),
        )
    setattr(owner, "_hd_electrochemistry_last_render_token", render_token)


def on_hd_electrochemistry_gender_filter_changed(owner: object, gender_filter: str, checked: bool) -> None:
    """Refresh the current top-ten ranking when a gender radio is selected."""
    if not checked:
        return
    setattr(owner, "hd_electrochemistry_gender_filter", normalize_hd_electrochemistry_gender_filter(gender_filter))
    setattr(owner, "_hd_electrochemistry_last_render_token", None)
    chart = getattr(owner, "_latest_chart", None) or getattr(owner, "current_chart", None)
    if chart is not None:
        render_hd_electrochemistry_predictions(owner, chart)


def on_hd_electrochemistry_collection_changed(owner: object, collection_id: object) -> None:
    """Rerank the open chart against the selected collection."""
    setattr(
        owner,
        "hd_electrochemistry_collection_filter",
        normalize_collection_id(collection_id),
    )
    setattr(owner, "_hd_electrochemistry_last_render_token", None)
    chart = getattr(owner, "_latest_chart", None) or getattr(owner, "current_chart", None)
    if chart is not None:
        render_hd_electrochemistry_predictions(owner, chart)


def on_gendered_results_method_changed(owner: object, gender_method: str, checked: bool) -> None:
    """Persist the calculation preference and refresh visible Synastry Predictions."""
    if not checked:
        return
    save_gendered_results_method(gender_method)
    setattr(owner, "_hd_electrochemistry_last_render_token", None)
    chart = getattr(owner, "_latest_chart", None) or getattr(owner, "current_chart", None)
    if chart is not None:
        render_hd_electrochemistry_predictions(owner, chart)


def on_hd_electrochemistry_link_activated(owner: object, href: str) -> None:
    prefix = "chart-uid:"
    if not str(href).startswith(prefix):
        return
    chart_uid = urllib.parse.unquote(str(href)[len(prefix):]).strip().upper()
    load_chart = getattr(owner, "load_chart_by_uid", None)
    if chart_uid and callable(load_chart):
        load_chart(chart_uid, from_chart_link=True)


def configure_hd_electrochemistry_label(owner: object, label: QLabel) -> None:
    label.setTextFormat(Qt.RichText)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.TextSelectableByMouse)
    label.setOpenExternalLinks(False)
    label.linkActivated.connect(lambda href: on_hd_electrochemistry_link_activated(owner, href))
    apply_chart_info_link_cursor(label)
