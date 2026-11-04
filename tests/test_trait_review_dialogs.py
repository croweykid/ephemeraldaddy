"""Run real Qt checks without the suite's process-wide Qt stub/reload hooks."""

import os
from pathlib import Path
import subprocess
import sys


def test_trait_review_dialog_contracts_in_subprocess(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--noconftest", "-q", "tests/gui_checks/trait_review_dialogs.py"],
        cwd=root,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "XDG_CACHE_HOME": str(tmp_path / "cache")},
        text=True, capture_output=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
