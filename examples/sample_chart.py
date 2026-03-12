import datetime
from zoneinfo import ZoneInfo

from ephemeraldaddy.core.deps import ensure_all_deps
from ephemeraldaddy.io.geocode import geocode_location, LocationLookupError
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.graphics.wheel_plot import plot_chart_wheel

# Make sure all deps are installed in this venv before doing anything else
ensure_all_deps(verbose=True)

# --- Input data (you can later make this interactive) ---
birth_place = "Chicago, IL, USA"
dt_local = datetime.datetime(2024, 6, 1, 14, 30)  # local civil time

# --- Geocode: place -> lat/lon, with UTC fallback and user-visible message ---
try:
    lat, lon, label = geocode_location(birth_place)
    print(f"Using birth location: {label} ({lat:.4f}, {lon:.4f})")
    tz_override = None  # let Chart infer timezone from lat/lon
except LocationLookupError:
    print("Birth location not found, defaulting to UTC.")
    # Fallback coordinates + explicit UTC timezone
    lat, lon = 0.0, 0.0
    tz_override = ZoneInfo("UTC")

# --- Build the chart ---
chart = Chart(
    "Sample",
    dt_local,
    lat,
    lon,
    tz=tz_override,  # either None (inferred from lat/lon) or explicit UTC fallback
)

# If timezone inference inside Chart had to fall back to UTC, surface that:
if chart.used_utc_fallback:
    print("Warning: Timezone inference failed; UTC was used.")

# --- Plot the wheel ---
plot_chart_wheel(chart)
