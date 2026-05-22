"""Chart View chart analytics panel rendering helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Iterable

from PySide6.QtWidgets import QSizePolicy

from ephemeraldaddy.core.interpretations import PLANET_ORDER
from ephemeraldaddy.gui.features.charts.metrics import calculate_planet_dynamics_scores

if TYPE_CHECKING:
    from ephemeraldaddy.core.chart import Chart

BODY_DYNAMICS_AXIS_LABEL_COLORS: dict[str, str] = {
    "enabler": "#6be39d",
    "antagonist": "#ff6b6b",
    "escalator": "#ffbd59",
}


def normalize_body_dynamics_role_label(value: object) -> str | None:
    """Normalize stored/UI Body Dynamics labels into chart-axis role keys."""
    text = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
    if not text:
        return None
    if text in {"enabler", "enabling", "enabling influence"}:
        return "enabler"
    if text in {"antagonist", "antagonizer", "antagonizing", "antagonizing influence"}:
        return "antagonist"
    if text.startswith("escalat") or " escalating" in f" {text}":
        return "escalator"
    return None


def _body_dynamics_role_from_scores(body_scores: dict[str, Any] | None) -> str:
    """Classify one body's dynamics scores into an axis-label role."""
    scores = body_scores or {}
    enabling = float(scores.get("enabling", 0.0))
    antagonizing = float(scores.get("antagonizing", 0.0))
    escalating = float(scores.get("escalating", 0.0))
    if escalating > enabling and escalating > antagonizing:
        return "escalator"
    if antagonizing > enabling:
        return "antagonist"
    return "enabler"


def body_dynamics_roles_for_chart(chart: Chart) -> dict[str, str]:
    """Resolve per-body roles for Chart View's analytics-panel body labels."""
    raw_roles = getattr(chart, "body_dynamics_roles", None)
    if isinstance(raw_roles, dict):
        role_items = raw_roles.items()
    else:
        role_items = ()
        role_text = str(raw_roles or "").strip()
        if role_text:
            try:
                parsed_roles = json.loads(role_text)
            except (TypeError, json.JSONDecodeError):
                parsed_roles = {}
            if isinstance(parsed_roles, dict):
                role_items = parsed_roles.items()

    canonical_bodies = {body.casefold(): body for body in PLANET_ORDER}
    roles: dict[str, str] = {}
    for raw_body, raw_role in role_items:
        body = canonical_bodies.get(str(raw_body or "").strip().casefold())
        role = normalize_body_dynamics_role_label(raw_role)
        if body and role:
            roles[body] = role

    if roles:
        return roles

    scores = getattr(chart, "planet_dynamics_scores", None) or calculate_planet_dynamics_scores(chart)
    if not isinstance(scores, dict):
        return {}
    for body, body_scores in scores.items():
        canonical_body = canonical_bodies.get(str(body or "").strip().casefold())
        if not canonical_body or not isinstance(body_scores, dict):
            continue
        roles[canonical_body] = _body_dynamics_role_from_scores(body_scores)
    return roles


def dominant_body_axis_label_color(role: str | None) -> str | None:
    """Return the Chart View Dominant Bodies axis-label color for a role."""
    return BODY_DYNAMICS_AXIS_LABEL_COLORS.get(role or "")


def style_dominant_body_axis_labels(ax: Any, chart: Chart, bodies: Iterable[str]) -> None:
    """Color and preserve pick metadata for Dominant Bodies X-axis labels."""
    body_dynamics_roles = body_dynamics_roles_for_chart(chart)
    for tick_label, body in zip(ax.get_xticklabels(), bodies, strict=True):
        tick_label.set_gid(f"body:{body}")
        tick_label.set_picker(5)
        role_color = dominant_body_axis_label_color(body_dynamics_roles.get(body))
        if role_color:
            tick_label.set_color(role_color)


def apply_metric_canvas_display_sizing(canvas: Any) -> None:
    """Apply stable metric-canvas sizing to avoid tab-switch resize jitter."""
    figure = canvas.figure
    figure_width, figure_height = figure.get_size_inches()
    display_height = canvas.property("metric_display_height")
    if not isinstance(display_height, int) or display_height <= 0:
        display_height = int(round(figure_height * figure.get_dpi()))
    if display_height <= 0 and figure_width > 0:
        display_height = int(round(figure_width * figure.get_dpi()))
    if display_height > 0:
        canvas.setMinimumHeight(display_height)
        canvas.setMaximumHeight(display_height)
    canvas.setSizePolicy(canvas.sizePolicy().horizontalPolicy(), QSizePolicy.Fixed)
    canvas.updateGeometry()
