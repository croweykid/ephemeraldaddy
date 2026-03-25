# EphemeralDaddy
private astrological research app with dark mode

## FAQs:
### Q. What is EphemeralDaddy?
### A. EphemeralDaddy (ED) is part astrology lab, part database notebook, part user-defined memoir, part weird toy box.

### Q. Why would someone use ED?
### A. Some reasons:
#### 1) Debunking/Bunking
You wonder if there's any merit to astrology at all. Does it work? Probably not, right? But what the hell, it's been around awhile. So have a lot of idiotic things. If only there were a way to confirm or discredit it once and for all! (Yes, there were those bad faith "studies" done based solely on sun signs being used to predict things astrology can't claim to predict, but they were obviously whack; the 'twin study' was the only piece of legitimate science in the mainstream skeptic camp, and I disagree with how it was interpreted, albeit not with the methods of execution) - WELL here. Have a DIY kit for evaluating the people in your life as an experiment. lol Then decide for yourself.

#### 2) Dark mode
You need dark mode and wanted a free astrology app.

#### 3) Privacy / Data Control
You wanted a secure, private offline astro chart database that's easy to access. 

#### 4) Nakshatras
You wanted an app that calculated tropical zodiac signs but also included nakshatras in a way that is readable for those more familiar with Western (Tropical/Grecoroman) astrological tradition.

#### 5) Anti-Cloud
You wanted an good offline astrology app that wouldn't force automated updates on you or start locking features behind a paywall as the universal quality declines, and features get dumbed down.

#### 6) Sociological/Psychological Intrigue
You wondered how many people you've met in life & could remember & wanted to see if there were any patterns in your relationships. While ED is essentially an astrological app at its core, I am increasingly rolling out mundane sociological metrics as well, for those who just want to analyze patterns in their relationships in a purely science-driven manner, independent of birth date shiz.

If you treat it like a research workspace (not an omniscient oracle), you’ll have a good time.

### Q. Why does ED exist?
### A. Several factors motivated the creation of this app:
#### 1) Nothing Similar Existed
I couldn't find a robust astrological research tool that could handle bulk chart comparisons. The work of Suzel Fuzeau-Braesch, Michel Gauquelin, John Addey, Robert Currey, Lois Rodden, David Cochrane & Claire Nakti, as well as my own independent research, pointed to some interested statistical outliers beyond what standard deviation would predict in control population estimates, but documenting and evaluating those experiements via spreadsheet was getting unwieldy, and I wanted a stable base of operations.
#### 2) Accessibility Features
Dark mode is a much-needed accessibility feature in modern apps. I couldn't find a good open source astrology app with built-in dark mode. I'm planning to roll out additional accessibility features in due course to make the app more democratized per the needs of different users.
#### 3) GOOD Open Source Astro Apps are Scarce
I was annoyed by the proprietary nature by which the popular astrology apps make their databases noncommunicable with one another. So I made a very simple, demystified database that can be parsed for integration into existing softwares with relative ease (at least in the era of LLMs), even by basic users with very little tech savvy.
#### 4) Offline-Only Is Hard To Find for Mobile
Mobile app astrology apps are sus in their handling of user data. I wanted an offline, secure solution. The app is not currently COMPLETELY offline, but is trending that way. The user's *Database*, however, is stored COMPLETELY locally, never touches the internet. Granted, this app hasn't yet been ported to mobile, but it's headed that way.
#### 5) Hedge Against Enshittification
Certain Apps That Shan't Be Mentioned for iOS & Android used to be excellent, but have become subject to enshittification, and so now there just wasn't a good app available for people that didn't have a hideous interface, saccharine voice-overs, generic/Barnum descriptions, annoying paywall or a significant learning curve. Eventually, I intend to port a slightly simplified version of EphemeralDaddy to mobile.

### Q. Why is it called EphemeralDaddy? Now I can't recommend it to friends without them thinking I'm some kind of kinkster.
### A. I thought it was pretty funny.
The haters might say, "That makes it harder for anyone to take seriously as a research tool."
But honestly, the haters were never going to take us seriously, anyway.

## How to Run
Even though I'm working on EXE & DMG builds for Windows & MacOS, right now. You can run the Python version of this app from Terminal, in the mean time: 
1. Download the repository, unzip to a folder. 
2. Open CMD/Terminal from newly unzipped ephemeraldaddy folder, or navigate to the ephemeraldaddy folder with the command line using 'cd'.
3. Launch the app by typing:

ephemeraldaddy % python -m ephemeraldaddy.gui.app

...and hitting Enter.

## Troubleshooting: 

EphemeralDaddy no longer auto-installs Python packages at runtime. In locked-down environments, install dependencies ahead of time (for example `pip install -r requirements.txt`) or distribute the bundled desktop EXE generated by `python tools/build_desktop_app.py --onefile`.

For first-time Windows EXE build steps (clean venv, build, smoke-test, signing notes) plus a turnkey Windows installer workflow (Inno Setup), see `desktop_app.md`.

### Offline location search (optional)
By default, ephemeraldaddy will build the database from the bundled `tools/cities15000.txt` file when available, or automatically download a small GeoNames dataset if the bundled file is missing. 

(Optional) Disable online fallback entirely:

```bash
export EPHEMERALDADDY_GAZETTEER_ONLY=1
```

If the gazetteer database exists, ephemeraldaddy will prefer it for search and geocoding.

Notes:
- The message about your default shell switching to `zsh` is informational and not an error.
- You still need to run the build command (step 2) in your shell; `export` just sets the path for ephemeraldaddy to read.
- If you placed `cities1500.txt` inside the repo’s `tools/` folder, the build command would look like:

```bash
cd /path/to/ephemeraldaddy
python3 tools/build_gazetteer.py --input tools/cities15000.txt
```

If your system doesn’t have a `python` command, `python3` is usually the right one on macOS/Linux.
and make sure the input path is correct for your current working directory.
If you want to disable the automatic download/build step, set `EPHEMERALDADDY_GAZETTEER_AUTO=0`.

### Swiss Ephemeris minor bodies (Ceres/Pallas/Juno/Vesta/Chiron/Lilith)

If these come back as `Unknown`, the Swiss ephemeris asteroid data files are usually missing from your configured ephemeris directory.

- Required files: `seas_18.se1` (Ceres/Pallas/Juno/Vesta) and `seorbel.txt` (Chiron).
- `Lilith` uses Swiss Black Moon apogee data (true/osculating when available, else mean) and is not an asteroid.
- Set `SWEPH_PATH` (or `EPHEMERALDADDY_SWEPH_PATH`) to a directory containing these files.

`ephemeraldaddy` will try to download missing files automatically, but in restricted/corporate networks this can fail silently at the network layer. Working on resolving this by bundling all dependencies for future users, but it's a major change to the app, so will take a bit to work the kinks out.

### Permanent offline setup (recommended for every install)

1. On a machine with internet access, download these Swiss files and copy them to a USB/shared folder:
   - `seas_18.se1`
   - `seorbel.txt`
2. On the target machine, run:

```bash
python3 tools/setup_swiss_ephemeris_offline.py --source /path/to/your/local/swiss-files
```

3. Add one of these to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) so every launch uses your local offline ephemeris directory:

```bash
export SWEPH_PATH="$HOME/.local/share/ephemeraldaddy/sweph"
# or
export EPHEMERALDADDY_SWEPH_PATH="$HOME/.local/share/ephemeraldaddy/sweph"
```

This gives you a permanent local/offline setup for Ceres, Pallas, Juno, Vesta, and Chiron in each installation.

## Database Privacy
Q. Where is the app’s DB stored? Is it stored locally within the app directory, or locally somewhere on the user’s hard drive? Is it accessible if they share the program directory? How can users protect their database data? Obviously, we have the DB export that allows them to back it up or import it (within the Database View window, under "Manage Charts"), but without using that tool within the app, where is that data actually stored?

A. Where the DB is stored
The application stores its main SQLite database at ~/.ephemeraldaddy/charts.db (i.e., inside the user’s home directory under a hidden .ephemeraldaddy folder), not inside the app’s install directory.

The code also exposes a get_db_path() helper that returns this same path, reinforcing that the database lives in the user’s home directory.

Is it stored inside the app directory?
No. The DB directory is explicitly set to the user’s home directory (Path.home() / ".ephemeraldaddy"), so it is separate from the program folder (e.g., wherever the app binary or source is installed).

If someone shares the program directory, is the DB included?
Not by default. Because the DB lives in the user’s home directory, copying or sharing the program directory alone will not include the database file unless the user manually includes ~/.ephemeraldaddy/charts.db (or exports it via the app).

How can users protect their database data?
Rely on OS-level permissions on the user’s home directory and the ~/.ephemeraldaddy folder; this is where the database lives.

Avoid sharing the home directory (or the hidden .ephemeraldaddy folder) if they don’t want their DB copied along with user files. The DB file is separate from the program directory, so keeping the home directory private is the key protection measure.

Use the app’s export/backup feature when they want to share or migrate data, since the database file is otherwise located in the hidden home folder and is not automatically included in app folder copies. The code’s backup flow creates copies from the same DB_DIR, reinforcing that ~/.ephemeraldaddy is the storage location.

## Importing Public Astrology Databases

You can import a CSV-based public database from **Manage Charts → Import DB from CSV**.

- Imported rows are tagged with `chart_type=public_db`.
- Charts created directly in the app are tagged with `chart_type=personal`.
- The Manage Charts search panel includes a **Chart Type** filter so you can query by this field.
- Exports include a `chart_type` CSV column (and legacy `source`) for round-tripping datasets.
# Composite charts (transit overlays + synastry)
See `docs/composite_charts_deployment.md` for deployment steps and new shared composition helpers.
