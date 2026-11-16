"""Run actual Qt checks outside the source tests' optional-dependency stubs."""
import os
from pathlib import Path
import subprocess
import sys


def test_static_prediction_runtime_gui_contracts(tmp_path):
    result = subprocess.run([sys.executable, '-m', 'pytest', '--noconftest', '-q', 'tests/gui_checks/static_prediction_runtime.py'], cwd=Path(__file__).resolve().parents[1], env={**os.environ, 'QT_QPA_PLATFORM':'offscreen', 'XDG_CACHE_HOME':str(tmp_path)}, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
