"""Chart Editor presentation for Human Design electrochemistry predictions."""

from __future__ import annotations

import html
import urllib.parse

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QLabel

from ephemeraldaddy.analysis.human_design import derive_human_design_profile
from ephemeraldaddy.analysis.human_design_synastry import (
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
from ephemeraldaddy.gui.style import (
    SETTINGS_APP,
    SETTINGS_ORG,
    apply_chart_info_link_cursor,
    houses_unknown_note_html,
)


HD_ELECTROCHEMISTRY_SUBHEADER = (
    "Top 10 charts ranked by Human Design channel/center synastry alone. This says nothing of shared values, means "
    "or other lifestyle factors. Canonical HD lore even explicitly states that 'Authority' (gut hunch) is superior. lol"
)

SETTINGS_KEY_GENDERED_RESULTS_METHOD = "chart_calculation/gendered_results_method"


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
    return (
        str(getattr(chart, "chart_uid", "") or "").strip().upper(),
        tuple(sorted(resolve_hd_electrochemistry_gates(chart))),
        bool(chart is not None and chart_uses_houses(chart)),
        normalize_hd_electrochemistry_gender_filter(getattr(owner, "hd_electrochemistry_gender_filter", "all")),
        load_gendered_results_method(),
        int(getattr(owner, "_database_metrics_cache_revision", 0) or 0),
    )


def hd_electrochemistry_predictions_are_current(owner: object, chart: object | None) -> bool:
    return getattr(owner, "_hd_electrochemistry_last_render_token", None) == hd_electrochemistry_render_token(owner, chart)


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
    candidates = filter_hd_electrochemistry_candidates(
        available_candidates,
        gender_filter,
        load_gendered_results_method(),
    )
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
    lines = []
    if not chart_uses_houses(chart):
        lines.append(
            "Ranked using this chart's default hypothetical time "
            + houses_unknown_note_html()
        )
    for index, match in enumerate(matches, 1):
        display_name = match.name
        if match.alias and match.alias.casefold() != match.name.casefold():
            display_name += f" ({match.alias})"
        href = "chart-uid:" + urllib.parse.quote(match.chart_uid, safe="")
        uncertainty_html = " " + houses_unknown_note_html() if not match.uses_houses else ""
        lines.append(
            f'{index}. <a href="{href}" style="color: #cdb7ff;">'
            f"{html.escape(display_name)}</a>{uncertainty_html} "
            f'<span style="color: #aaa;">({match.completed_channels} completed channels, '
            f"{match.defined_centers} defined centers)</span>"
        )
    label.setText("<br>".join(lines))
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
