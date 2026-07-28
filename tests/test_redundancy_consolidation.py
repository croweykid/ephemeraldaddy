from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

from ephemeraldaddy.core.astrology import sign_for_longitude


REPO_ROOT = Path(__file__).resolve().parents[1]


def _module(relative_path: str) -> ast.Module:
    return ast.parse((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def test_production_classes_do_not_shadow_plain_methods() -> None:
    """A later plain method must never silently replace an earlier method."""
    duplicates: list[str] = []
    for path in (REPO_ROOT / "ephemeraldaddy").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for class_node in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
            plain_methods = [
                node.name
                for node in class_node.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not any(
                    isinstance(decorator, ast.Name)
                    and decorator.id in {"property", "setter", "deleter"}
                    for decorator in node.decorator_list
                )
                and not any(
                    isinstance(decorator, ast.Attribute)
                    and decorator.attr in {"setter", "deleter"}
                    for decorator in node.decorator_list
                )
            ]
            for name, count in Counter(plain_methods).items():
                if count > 1:
                    duplicates.append(f"{path.relative_to(REPO_ROOT)}:{class_node.name}.{name}")
    assert duplicates == []


def test_style_tokens_have_one_authoritative_assignment() -> None:
    tree = _module("ephemeraldaddy/gui/style.py")
    assignments = Counter(
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    )
    assert assignments["CHART_DATA_HIGHLIGHT_COLOR"] == 1
    assert assignments["RELATIVE_YEAR_COLORS"] == 1


def test_search_options_are_imported_from_shared_controls() -> None:
    tree = _module("ephemeraldaddy/gui/app.py")
    shared_imports = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "ephemeraldaddy.gui.widgets.search_controls"
        for alias in node.names
    }
    assert "GENERATION_UNKNOWN_OPTION" in shared_imports
    locally_assigned = {
        target.id
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
        )
        if isinstance(target, ast.Name)
    }
    assert not locally_assigned.intersection(
        {
            "GENERATION_FILTER_OPTIONS",
            "SEARCH_SENTIMENT_OPTIONS",
            "SEARCH_RELATIONSHIP_TYPE_OPTIONS",
            "SEARCH_GENDER_OPTIONS",
            "SEARCH_GENDER_GUESSED_OPTIONS",
        }
    )


def test_sign_for_longitude_wraps_and_observes_cusps() -> None:
    assert sign_for_longitude(0) == "Aries"
    assert sign_for_longitude(29.999999) == "Aries"
    assert sign_for_longitude(30) == "Taurus"
    assert sign_for_longitude(359.999999) == "Pisces"
    assert sign_for_longitude(360) == "Aries"
    assert sign_for_longitude(-30) == "Pisces"


def test_human_design_circuit_compatibility_module_reexports_canonical_data() -> None:
    tree = _module("ephemeraldaddy/analysis/hd_circuits_reference.py")
    imports = {
        (node.module, alias.name)
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert (
        "ephemeraldaddy.analysis.human_design_reference",
        "HD_CIRCUIT_GROUPS",
    ) in imports
    assert not any(
        isinstance(node, (ast.Assign, ast.AnnAssign))
        and any(
            isinstance(target, ast.Name) and target.id == "HD_CIRCUIT_GROUPS"
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        )
        for node in tree.body
    )
    canonical_tree = _module("ephemeraldaddy/analysis/human_design_reference.py")
    canonical_assignments = {
        node.target.id
        for node in canonical_tree.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    assert {
        "HD_CIRCUIT_GROUPS",
        "HD_ALL_CHANNELS",
        "HD_ALL_GATES",
        "HD_SUBCIRCUIT_INDEX",
        "HD_CHANNEL_TO_CIRCUIT",
    } <= canonical_assignments
    assert not (REPO_ROOT / "ephemeraldaddy/analysis/human_design_circuits.py").exists()


def test_core_human_design_channel_topology_comes_from_reference() -> None:
    tree = _module("ephemeraldaddy/core/hd.py")
    imports = {
        (node.module, alias.name, alias.asname)
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert (
        "ephemeraldaddy.analysis.human_design_reference",
        "HD_CHANNELS",
        "HD_CHANNEL_REFERENCE",
    ) in imports


def test_human_design_circuit_reference_is_gui_independent() -> None:
    import sys

    sys.modules.pop("ephemeraldaddy.analysis.hd_circuits_reference", None)
    sys.modules.pop("ephemeraldaddy.analysis.human_design_reference", None)
    before = set(sys.modules)

    from ephemeraldaddy.analysis import hd_circuits_reference

    imported = set(sys.modules) - before
    assert hd_circuits_reference.HD_ALL_CHANNELS
    assert not any(name.startswith("ephemeraldaddy.gui") for name in imported)
    assert not any(name.startswith("PySide6") for name in imported)


def test_startup_entrypoints_share_one_animation_renderer() -> None:
    startup_source = (REPO_ROOT / "ephemeraldaddy/gui/startup.py").read_text(encoding="utf-8")
    process_source = (REPO_ROOT / "ephemeraldaddy/gui/startup_animation_process.py").read_text(
        encoding="utf-8"
    )
    assert "class StartupAnimationFrame" not in startup_source
    assert "class StartupAnimationFrame" not in process_source
    assert "from ephemeraldaddy.gui.startup_animation import StartupAnimationFrame" in startup_source
    assert "from ephemeraldaddy.gui.startup_animation import StartupAnimationFrame" in process_source
