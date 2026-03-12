#!/usr/bin/env python3
import os

# ----------- PROJECT STRUCTURE -----------

PROJECT_DIRS = [
    "ephemeraldaddy",
    "ephemeraldaddy/core",
    "ephemeraldaddy/io",
    "ephemeraldaddy/analysis",
    "ephemeraldaddy/graphics",
    "ephemeraldaddy/ui",
    "examples"
]

PROJECT_FILES = {
    "pyproject.toml": '''[project]
name = "ephemeraldaddy"
version = "0.1.0"
description = "A modular, research-ready astrology toolkit."
authors = [{name="Your Name"}]
dependencies = [
  "skyfield>=1.49",
  "pandas>=2.2",
  "matplotlib>=3.9",
  "numpy>=1.26",
  "rich>=13.7",
]

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
''',

    "README.md": "# EphemeralDaddy\nA modular Python astrology engine.\n",
    ".gitignore": "venv/\n__pycache__/\n*.pyc\n",

    "ephemeraldaddy/__init__.py": "",

    # ---- core ----
    "ephemeraldaddy/core/__init__.py": "",
    "ephemeraldaddy/core/ephemeris.py": '''from skyfield.api import load, wgs84, N, E

ts = load.timescale()
eph = load('de421.bsp')

PLANETS = {
    "Sun": eph['sun'],
    "Moon": eph['moon'],
    "Mercury": eph['mercury'],
    "Venus": eph['venus'],
    "Mars": eph['mars'],
    "Jupiter": eph['jupiter barycenter'],
    "Saturn": eph['saturn barycenter'],
    "Uranus": eph['uranus barycenter'],
    "Neptune": eph['neptune barycenter'],
    "Pluto": eph['pluto barycenter'],
}

def planetary_positions(dt, lat, lon):
    t = ts.from_datetime(dt)
    observer = wgs84.latlon(lat * N, lon * E)
    results = {}
    for name, body in PLANETS.items():
        astro = observer.at(t).observe(body).apparent()
        lon = astro.ecliptic_position().longitude.degrees % 360
        results[name] = lon
    return results
''',

    "ephemeraldaddy/core/houses.py": '''def placidus_houses(sidereal_time_deg, latitude_deg):
    # Placeholder house system
    return [(sidereal_time_deg + i*30) % 360 for i in range(12)]
''',

    "ephemeraldaddy/core/aspects.py": '''ASPECTS = {
    "Conjunction": 0,
    "Opposition": 180,
    "Trine": 120,
    "Square": 90,
    "Sextile": 60,
}

ORB = 6

def find_aspects(positions):
    aspects = []
    planets = list(positions.keys())
    for i in range(len(planets)):
        for j in range(i+1, len(planets)):
            p1, p2 = planets[i], planets[j]
            diff = abs(positions[p1] - positions[p2])
            diff = min(diff, 360 - diff)
            for asp, angle in ASPECTS.items():
                if abs(diff - angle) <= ORB:
                    aspects.append((p1, p2, asp, diff))
    return aspects
''',

    "ephemeraldaddy/core/chart.py": '''from .ephemeris import planetary_positions
from .houses import placidus_houses
from .aspects import find_aspects

class Chart:
    def __init__(self, name, dt, lat, lon):
        self.name = name
        self.dt = dt
        self.lat = lat
        self.lon = lon

        self.positions = planetary_positions(dt, lat, lon)
        self.houses = placidus_houses(0, lat)
        self.aspects = find_aspects(self.positions)

    def as_dict(self):
        return {
            "name": self.name,
            "datetime": str(self.dt),
            "lat": self.lat,
            "lon": self.lon,
            "positions": self.positions,
            "houses": self.houses,
            "aspects": self.aspects,
        }
''',

    # ---- io ----
    "ephemeraldaddy/io/__init__.py": "",
    "ephemeraldaddy/io/import_csv.py": "import pandas as pd\n",
    "ephemeraldaddy/io/export_json.py": "import json\n",

    # ---- analysis ----
    "ephemeraldaddy/analysis/__init__.py": "",
    "ephemeraldaddy/analysis/stats.py": "# statistical tools placeholder\n",
    "ephemeraldaddy/analysis/cycles.py": "# transit/cycle analysis placeholder\n",

    # ---- graphics ----
    "ephemeraldaddy/graphics/__init__.py": "",
    "ephemeraldaddy/graphics/theme.py": '''DARK_THEME = {
    "background": "#111111",
    "foreground": "#EEEEEE",
    "planet": "#FFDD88",
    "aspect_major": "#88BBFF",
    "aspect_minor": "#5577AA",
    "house_line": "#444444",
    "wheel_circle": "#333333",
}
''',

    "ephemeraldaddy/graphics/wheel_plot.py": '''import matplotlib.pyplot as plt
import numpy as np
from .theme import DARK_THEME

def plot_chart_wheel(chart):
    plt.figure(figsize=(8,8))
    ax = plt.subplot(111, polar=True)
    ax.set_facecolor(DARK_THEME["background"])
    ax.set_theta_zero_location("E")
    ax.set_theta_direction(-1)
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])

    ax.plot(
        np.linspace(0, 2*np.pi, 360),
        [1]*360,
        color=DARK_THEME["wheel_circle"],
        linewidth=2
    )

    for name, lon in chart.positions.items():
        theta = np.radians(lon)
        ax.scatter(theta, 0.85, color=DARK_THEME["planet"], s=120)
        ax.text(theta, 0.92, name, color=DARK_THEME["foreground"],
                ha='center', va='center', fontsize=9)

    plt.title(chart.name, color=DARK_THEME["foreground"])
    plt.show()
''',

    # ---- UI ----
    "ephemeraldaddy/ui/__init__.py": "",
    "ephemeraldaddy/ui/cli.py": '''from rich.console import Console
from ..core.chart import Chart
import datetime

console = Console()

def run():
    console.print("[bold cyan]EphemeralDaddy[/bold cyan]")

    name = input("Name: ")
    year = int(input("Year: "))
    month = int(input("Month: "))
    day = int(input("Day: "))
    hour = int(input("Hour: "))
    minute = int(input("Minute: "))
    lat = float(input("Latitude: "))
    lon = float(input("Longitude: "))

    dt = datetime.datetime(year, month, day, hour, minute)
    chart = Chart(name, dt, lat, lon)

    console.print(chart.as_dict())
''',

    # ---- examples ----
    "examples/sample_chart.py": '''from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.graphics.wheel_plot import plot_chart_wheel
import datetime

chart = Chart(
    "Sample",
    datetime.datetime(2024, 6, 1, 14, 30),
    41.8781,
    -87.6298
)

plot_chart_wheel(chart)
'''
}

# ----------- EXECUTION -----------

def main():
    print("Creating EphemeralDaddy scaffold...")

    for d in PROJECT_DIRS:
        os.makedirs(d, exist_ok=True)
        print(f"✓ Directory: {d}")

    for path, content in PROJECT_FILES.items():
        if os.path.exists(path):
            print(f"• Skipped (exists): {path}")
            continue
        with open(path, "w") as f:
            f.write(content)
        print(f"✓ File: {path}")

    print("\nDone. EphemeralDaddy is ready.")

if __name__ == "__main__":
    main()
