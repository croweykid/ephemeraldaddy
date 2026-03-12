import argparse
from pathlib import Path

from ephemeraldaddy.io.gazetteer_builder import build_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local gazetteer database from GeoNames data.")
    parser.add_argument("--input", required=True, help="Path to GeoNames .txt file (e.g., cities500.txt)")
    parser.add_argument(
        "--output",
        default=str(Path.home() / ".local" / "share" / "ephemeraldaddy" / "gazetteer.sqlite"),
        help="Where to write the gazetteer SQLite database",
    )
    parser.add_argument("--min-pop", type=int, default=0, help="Minimum population to keep")
    args = parser.parse_args()

    rows = build_db(Path(args.input), Path(args.output), args.min_pop)
    print(f"Wrote {rows} locations to {args.output}")


if __name__ == "__main__":
    main()