from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT / "ephemeraldaddy/gui/features/charts/database_analytics.py"
).read_text(encoding="utf-8")


def _method_source(name: str) -> str:
    start = SOURCE.index(f"    def {name}(")
    next_method = SOURCE.find("\n    def ", start + 1)
    next_static = SOURCE.find("\n    @staticmethod", start + 1)
    boundaries = [value for value in (next_method, next_static) if value >= 0]
    end = min(boundaries) if boundaries else len(SOURCE)
    return SOURCE[start:end]


def test_similarity_display_name_adapter_does_not_require_removed_id_row_cache() -> None:
    method = _method_source("_display_name_for_chart_id")

    assert "_active_chart_rows_by_id" not in method
    assert "_get_chart_for_filter" in method


def test_similarity_display_name_adapter_does_not_expose_sqlite_primary_key() -> None:
    method = _method_source("_display_name_for_chart_id")

    assert 'f"Chart {int(chart_id)}"' not in method
    assert '"Unnamed Chart"' in method
