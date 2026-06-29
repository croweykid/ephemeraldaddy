from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPORTERS_SOURCE = (ROOT / "ephemeraldaddy/gui/features/charts/exporters.py").read_text()
APP_SOURCE = (ROOT / "ephemeraldaddy/gui/app.py").read_text()


def test_similarities_exporters_add_sample_suffix_to_python_default_filename():
    assert "def similarities_export_sample_suffix" in EXPORTERS_SOURCE
    assert "_{sample_size}samples" in EXPORTERS_SOURCE
    assert "{timestamp}{sample_suffix}.py" in EXPORTERS_SOURCE


def test_similarities_csv_export_adds_sample_suffix_to_default_filename():
    assert "_similarities_export_sample_suffix(self._similarities_export_sections)" in APP_SOURCE
    assert "{timestamp}{sample_suffix}.csv" in APP_SOURCE


def test_similarities_exporters_reuse_and_remember_last_save_directory():
    assert "similarities_analysis/last_export_directory" in EXPORTERS_SOURCE
    assert "def similarities_export_default_path" in EXPORTERS_SOURCE
    assert "def remember_similarities_export_directory" in EXPORTERS_SOURCE
    assert "similarities_export_default_path(settings, default_filename)" in EXPORTERS_SOURCE
    assert "remember_similarities_export_directory(settings, file_path)" in EXPORTERS_SOURCE
    assert "_similarities_export_default_path(settings, default_filename)" in APP_SOURCE
    assert "_remember_similarities_export_directory(settings, file_path)" in APP_SOURCE
