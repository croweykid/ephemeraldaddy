# ephemeraldaddy/__init__.py
from ephemeraldaddy.core.deps import ensure_all_deps

# Ensure dependencies are present as soon as the package is imported.
ensure_all_deps(verbose=True)
