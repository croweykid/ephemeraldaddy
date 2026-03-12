import datetime
from zoneinfo import ZoneInfo

from ephemeraldaddy.io.geocode import geocode_location, LocationLookupError
from ephemeraldaddy.core.chart import Chart

birth_place = "MadeUpCity, Nowhere"
dt_local = datetime.datetime(2024, 6, 1, 14, 30)

try:
    lat, lon, label = geocode_location(birth_place)
    print(f"Using birth location: {label} ({lat:.4f}, {lon:.4f})")
    tz_override = None
except LocationLookupError:
    print("Birth location not found, defaulting to UTC.")
    lat, lon = 0.0, 0.0
    tz_override = ZoneInfo("UTC")

chart = Chart("Sample", dt_local, lat, lon, tz=tz_override)
if chart.used_utc_fallback:
    print("Warning: Timezone inference failed; UTC was used.")

print(chart.as_dict())
