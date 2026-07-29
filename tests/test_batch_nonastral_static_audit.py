"""Static architecture guard; this file has no application runtime cost."""

import ast
from pathlib import Path


APP_PATH = Path("ephemeraldaddy/gui/app.py")
ALLOWED_RECALCULATING_BATCH_HANDLERS = {
    "_on_batch_birthtime_unknown_toggled",
}


def _calls_name(node: ast.AST, called_name: str) -> bool:
    return any(
        isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id == called_name
        for child in ast.walk(node)
    )


def test_batch_handlers_cannot_gain_unapproved_full_chart_updates():
    tree = ast.parse(APP_PATH.read_text())
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if "batch" not in node.name or node.name in ALLOWED_RECALCULATING_BATCH_HANDLERS:
            continue
        if _calls_name(node, "update_chart"):
            offenders.append(node.name)
    assert offenders == [], (
        "Nonastral Batch Editor handlers must use the UID patch writer; "
        f"unexpected update_chart callers: {sorted(offenders)}"
    )


def test_only_allowlisted_batch_handler_recalculates_dominance():
    tree = ast.parse(APP_PATH.read_text())
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if "batch" not in node.name or node.name in ALLOWED_RECALCULATING_BATCH_HANDLERS:
            continue
        if any(
            _calls_name(node, calculation)
            for calculation in (
                "_calculate_dominant_sign_weights",
                "_calculate_dominant_planet_weights",
                "_calculate_dominant_nakshatra_weights",
            )
        ):
            offenders.append(node.name)
    assert offenders == []
