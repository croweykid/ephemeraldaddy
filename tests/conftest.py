"""Collection safeguards for tests which install optional-dependency stubs.

Several focused unit tests replace Qt or application modules at import time so
they can run in minimal environments.  Pytest imports every test module during
collection, however, so those process-global replacements must not leak into
the next test module.
"""

from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path

import pytest


_ISOLATED_MODULE_PREFIXES = ("PySide6", "ephemeraldaddy")
_COLLECTED_MODULE_STATES: dict[str, dict[str, object]] = {}


# Source-inspection tests should not depend on the host's legacy text encoding
# (notably cp1252 on Windows).  Production Python sources are UTF-8, so make
# the implicit encoding used by those tests deterministic as well.
_path_read_text = Path.read_text


def _read_utf8_text(
    self: Path, encoding: str | None = None, errors: str | None = None
) -> str:
    return _path_read_text(self, encoding=encoding or "utf-8", errors=errors)


Path.read_text = _read_utf8_text


def _is_isolated_module(name: str) -> bool:
    return any(
        name == prefix or name.startswith(f"{prefix}.")
        for prefix in _ISOLATED_MODULE_PREFIXES
    )


def _purge_isolated_modules() -> None:
    for name in tuple(sys.modules):
        if _is_isolated_module(name):
            sys.modules.pop(name, None)


def pytest_collectstart(collector: pytest.Collector) -> None:
    """Clear stubs immediately before pytest imports a test module."""

    if isinstance(collector, pytest.Module):
        _purge_isolated_modules()


@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(collector: pytest.Collector) -> Generator[None, None, None]:
    """Restore Qt and application modules after collecting each test file."""

    if not isinstance(collector, pytest.Module):
        yield
        return

    yield

    _COLLECTED_MODULE_STATES[str(collector.path)] = {
        name: module
        for name, module in sys.modules.items()
        if _is_isolated_module(name)
    }

    # Begin every test module with a clean import state.  Test modules are
    # imported recursively while collection reports are nested, so restoring
    # a snapshot can resurrect a stub installed by the outer module.  Purging
    # both namespaces avoids that ordering dependency entirely.
    _purge_isolated_modules()


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Reinstate the isolated imports captured for the item's own test file."""

    module_state = _COLLECTED_MODULE_STATES.get(str(item.path))
    if module_state is None:
        return
    _purge_isolated_modules()
    sys.modules.update(module_state)
