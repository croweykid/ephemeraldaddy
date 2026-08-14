from pathlib import Path

from tools.build_desktop_app import REPO_ROOT, _build_datas


def test_desktop_build_bundles_synastry_explainer_assets() -> None:
    expected_source = Path(
        "ephemeraldaddy/gui/features/popouts/assets"
    ).as_posix()
    expected_destination = "ephemeraldaddy/gui/features/popouts/assets"

    assert (expected_source, expected_destination) in _build_datas()
    assert (REPO_ROOT / expected_source / "what_is_synastry.html").is_file()
