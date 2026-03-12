# ephemeraldaddy/ui/cli.py

import datetime
from zoneinfo import ZoneInfo

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from ephemeraldaddy.core.deps import ensure_all_deps
from ephemeraldaddy.io.geocode import geocode_location, LocationLookupError
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.graphics.wheel_plot import plot_chart_wheel

console = Console()


def _parse_date(date_str: str) -> datetime.date:
    return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()


def _parse_time(time_str: str) -> datetime.time:
    return datetime.datetime.strptime(time_str, "%H:%M").time()


def run():
    """Interactive CLI for EphemeralDaddy."""
    # Make sure dependencies are present
    ensure_all_deps(verbose=False)

    console.print("[bold cyan]EphemeralDaddy[/bold cyan]  —  natal chart generator\n")

    name = Prompt.ask("Name", default="Sample Person")
    birth_place = Prompt.ask(
        "Birth place (city, region, country)",
        default="Chicago, IL, USA",
    )

    date_str = Prompt.ask("Birth date [YYYY-MM-DD]", default="1990-01-01")
    time_str = Prompt.ask("Birth time [HH:MM 24hr]", default="12:00")

    try:
        birth_date = _parse_date(date_str)
        birth_time = _parse_time(time_str)
    except ValueError:
        console.print("[red]Invalid date or time format. Use YYYY-MM-DD and HH:MM (24hr).[/red]")
        return

    dt_local = datetime.datetime.combine(birth_date, birth_time)

    # --- Geocode location ---
    try:
        lat, lon, label = geocode_location(birth_place)
        console.print(f"[green]Using birth location:[/green] {label} "
                      f"([bold]{lat:.4f}[/bold], [bold]{lon:.4f}[/bold])")
        tz_override = None  # Chart will infer timezone from lat/lon
    except LocationLookupError:
        console.print("[yellow]Birth location not found, defaulting to UTC @ (0.0, 0.0).[/yellow]")
        lat, lon = 0.0, 0.0
        tz_override = ZoneInfo("UTC")

    # --- Build chart ---
    chart = Chart(name, dt_local, lat, lon, tz=tz_override)

    if chart.used_utc_fallback and tz_override is None:
        console.print("[yellow]Warning: Timezone inference failed; UTC was used.[/yellow]")

    console.print()

    # --- Summary table ---
    table = Table(
        title=f"{name} — {chart.dt.isoformat()}  "
              f"@ lat {lat:.4f}, lon {lon:.4f}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Body")
    table.add_column("Ecl. Lon (°)", justify="right")

    for body, lon_deg in sorted(chart.positions.items()):
        table.add_row(body, f"{lon_deg:7.2f}")

    console.print(table)

    # --- Optional wheel plot ---
    choice = Prompt.ask("Plot wheel?", choices=["y", "n"], default="y")
    if choice.lower() == "y":
        plot_chart_wheel(chart)
