# Compatibility launcher for chartwheel generation.
#
# Supported commands:
# - python -m ephemeraldaddy.graphics.chartwheel_generator
# - python -m chartwheel_generator         (from ephemeraldaddy/graphics)
# - python -m chartwheel_generator.py      (from ephemeraldaddy/graphics)
# - python chartwheel_generator.py         (from ephemeraldaddy/graphics)

from pathlib import Path
import sys

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from ephemeraldaddy.graphics._chartwheel_generator_impl import draw_chartwheel, main

if __name__ == "__main__":
    main()
