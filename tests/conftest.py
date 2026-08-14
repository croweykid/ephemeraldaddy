"""Collection safeguards for tests which install optional-dependency stubs.

Several focused unit tests replace Qt or application modules at import time so
they can run in minimal environments.  Pytest imports every test module during
collection, however, so those process-global replacements must not leak into
the next test module.
"""

from __future__ import annotations

import sys
from collections.abc import Generator
from types import ModuleType

import pytest


_ISOLATED_MODULE_PREFIXES = ("PySide6", "ephemeraldaddy")


def _is_isolated_module(name: str) -> bool:
    return any(
        name == prefix or name.startswith(f"{prefix}.")
        for prefix in _ISOLATED_MODULE_PREFIXES
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(collector: pytest.Collector) -> Generator[None, None, None]:
    """Restore Qt and application modules after collecting each test file."""

    if not isinstance(collector, pytest.Module):
        yield
        return

    original_modules: dict[str, ModuleType] = {
        name: module
        for name, module in sys.modules.items()
        if _is_isolated_module(name) and module is not None
    }

    yield

    introduced_stub = any(
        _is_isolated_module(name)
        and name not in original_modules
        and getattr(module, "__spec__", None) is None
        for name, module in sys.modules.items()
    )
    if not introduced_stub:
        return

    for name in tuple(sys.modules):
        module = sys.modules.get(name)
        is_new_application_module = (
            name.startswith("ephemeraldaddy") and name not in original_modules
        )
        is_new_stub = (
            name.startswith("PySide6")
            and name not in original_modules
            and getattr(module, "__spec__", None) is None
        )
        if is_new_application_module or is_new_stub:
            sys.modules.pop(name, None)
    sys.modules.update(original_modules)
