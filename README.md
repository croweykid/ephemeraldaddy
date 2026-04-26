# EphemeralDaddy
private astrological research app with dark mode

## FAQs:
### Q. What is EphemeralDaddy?
### A. EphemeralDaddy (ED) is part astrology lab, part database notebook, part user-defined memoir, part weird toy box.

### Q. Why would someone use ED?
### A. Some reasons:
#### 1) Debunking/Bunking
You wonder if there's any merit to astrology at all. Does it work? Probably not, right? But what the hell, it's been around awhile. So have a lot of idiotic things. WELL here. Have a DIY kit for evaluating the people in your life as an experiment, and decide for yourself. (we could talk about the sun-sign based 'studies', what they proved/disproved, the good/bad faith of their conduct & methodology, but that's a significant digression outside the scope of this Readme probably)

#### 2) Dark mode
You desire/need dark mode and wanted a free desktop astrology app.

#### 3) Privacy / Data Control
You wanted a secure, private offline astro chart database that's easy to access. 

#### 4) Nakshatras
You wanted an app that calculated tropical zodiac signs but also included nakshatras in a way that is readable for those more familiar with Western (Tropical/Grecoroman) astrological tradition. Vic DiCara fired up this heresy of combining sidereal nakshatras with the Tropical zodiac, and it was a pretty interesting take.

#### 5) Anti-Cloud
You wanted an good offline astrology app that wouldn't force automated updates on you or start locking features behind a paywall as the universal quality declines, with all features getting 'Fisher Priced' along the way.

#### 6) Sociological/Psychological Intrigue
You wondered how many people you've met in life & could remember & wanted to see if there were any patterns in your relationships. While ED is essentially an astrological app at its core, I am increasingly rolling out mundane sociological metrics as well, for those who just want to analyze patterns in their relationships in a purely science-driven manner, independent of birth date shiz.

If you treat the app like a research workspace (not an omniscient oracle), you’ll have a good time and maybe change your perspective on the world. Whether you wind up believing in astrology or not (confirmation isn't my goal - data is), I think there's value in thought experiments and challenging psychological/sociological constructs. Who knows?

### Q. Why does ED exist?
### A. Several factors motivated the creation of this app:
#### 1) Nothing Similar Existed
I couldn't find a robust astrological research tool that could handle bulk chart comparisons. The work of Suzel Fuzeau-Braesch, Michel Gauquelin, John Addey, Robert Currey, Lois Rodden, David Cochrane & Claire Nakti, as well as my own independent research, pointed to some interested statistical outliers beyond what standard deviation would predict in control population estimates, but documenting and evaluating those experiements via spreadsheet was getting unwieldy, and I personally wanted a stable base of operations. Sharing it has admittedly been secondary, so there may still be some blind spots in terms of UI/Ux, but I also do want to make this software available to people and widely useful to fellow nerds/weirdos, so I'm trying to bridge those gaps and make a tool for other people to enjoy as well, at this point.
#### 2) Accessibility Features
Dark mode is a much-needed accessibility feature in modern apps. I'm planning to roll out additional accessibility features in due course to make the app more democratized per the needs of different users; the more feedback I get from anyone based on their specific individual needs, the more I'll know to incorporate to try to make this equal access for all enquiring minds.
#### 3) GOOD Open Source Astro Apps are Scarce
I was annoyed by the proprietary nature by which the popular astrology apps make their databases noncommunicable with one another. So I made a very simple, demystified database that can be parsed for integration into existing softwares with relative ease (at least in the era of LLMs), even by basic users with very little tech savvy.
#### 4) Privacy Should be Prioritized
Mobile app astrology apps are sus in their handling of user data. I wanted an offline, secure solution - even if that meant building for desktop rather than mobile. The desktop app is not yet currently COMPLETELY offline, but is trending that way. The user's *Database*, however, is stored COMPLETELY locally, never touches the internet. (Which all savvy computer users understand doesn't mean the internet never touches your hard drive: Be mindful that anything on a computer with internet access is never completely private & you should always be wary; I'm looking into developing at-rest database encryption & (optional) password-protected login for additional user security, but my background knowledge in that field is limited, and I'd rather not give users the false assurance of a flimsy veneer of protection; that said, even a Schlage lock can keep casual robbers from breaking into a house; leaving a door unlocked is still a reduction in friction for hackers, so I will probably implement something simple as a measure of enhanced privacy as soon as I learn how to do so.)
#### 5) Hedge Against Enshittification
Certain Apps That Shan't Be Mentioned for iOS & Android used to be excellent, but have become subject to enshittification, and so now there just wasn't a good app available for people that didn't have a hideous interface, saccharine voice-overs, generic/Barnum descriptions, annoying paywall or a significant learning curve. Eventually, I intend to port a slightly simplified version of EphemeralDaddy to mobile, while keeping quality high and data privacy prioritized.

### Q. Why is it called EphemeralDaddy? Now I can't recommend it to friends without them thinking I'm some kind of kinkster.
### A. I thought it was pretty funny.
The haters might say, "That makes it harder for anyone to take seriously as a research tool."
But honestly, the haters were prolly never going to take us seriously, anyway. And if they do, the name will still be hilarious in its stupidity.

##How to Set Up & Run
If you're a Windows user, you're in luck (at least in this regard)...
Click the newest "Release" in the righthand Release panel on Ephemeral Daddy's Github page, and download that bad boy. Extract. Click the Setup EXE. You'll go through a proper installer. It'll be installed, visible in your Add/Remove programs, and you can uninstall it if you hate it. That's the easiest way.
If you're on Mac or Linux, I'm sorry, I haven't finsihed that build yet. 1) I've just been shamefully lazy about the Linux build. Will try to knock that out sometime in 5/2026. 2) Mac requires an annual Developer account subscription at this time to sign the app so the avg Mac user will know how to install it without it getting shot down as an untrusted 'probable virus' app, and I haven't yet forked over the ransom money to Apple to get the app properly signed. Would rather do it all at once, for a bunch of apps, in the same year, and so far this is the only one that's at the official release stage. Hoping to complete an official signed .DMG Mac build sometime in 2026, but it's my first time trying, and my knowledge of the process remains theoretical at this juncture...

## How to Run Repository Download in Terminal (rather than using an official Windows .EXE release with Installer)
Even though I'm working on EXE & DMG builds for Windows & MacOS, right now. You can run the Python version of this app from Terminal, in the mean time: 
1. Download the repository, unzip to a folder. 
2. Open CMD/Terminal from newly unzipped ephemeraldaddy folder, or navigate to the ephemeraldaddy folder with the command line using 'cd'. Activate/set up a virtual environment.
3. Then launch the app by typing:

ephemeraldaddy % python -m ephemeraldaddy.gui.app

...and hitting Enter.

_(See "ONBOARDING.MD" for more granular instructions)_

## Database Privacy
Q. Where is the app’s DB stored? Is it stored locally within the app directory, or locally somewhere on the user’s hard drive? Is it accessible if they share the program directory? How can users protect their database data? Obviously, we have the DB export that allows them to back it up or import it (within the Database View window, under "Manage Charts"), but without using that tool within the app, where is that data actually stored?

A. Where the DB is stored
The application stores its main SQLite database at ~/.ephemeraldaddy/charts.db (i.e., inside the user’s home directory under a hidden .ephemeraldaddy folder), not inside the app’s install directory. 
The DB directory is explicitly set to the user’s home directory (Path.home() / ".ephemeraldaddy"), so it is separate from the program folder (e.g., wherever the app binary or source is installed, rather than existing inside the app's installation directory.

You can always look up the exact location using the get_db_path() helper in Terminal. Buuut...I'm realizing if you are running this in Terminal, you probably aren't the kind of person who needs that hand-holding, so I should really make this more turnkey for the average user. 

Q. If someone shares the program directory, is the DB included?
A. Not by default. Because the DB lives in the user’s home directory, copying or sharing the program directory alone will not include the database file unless the user manually includes ~/.ephemeraldaddy/charts.db (or exports it via the app).

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

### CSV format: **Import DB from CSV** (generic importer)

This importer accepts either:

1. **Simple 3-column rows** (no header required):
   - `name`
   - `datetime`
   - `birth_place`
2. **Round-trip export rows** (the same schema produced by **Export selected charts**), with this header:
   - `id,name,birth_place,datetime_iso,tz_name,latitude,longitude,used_utc_fallback,sentiments,relationship_types,positive_sentiment_intensity,negative_sentiment_intensity,familiarity,dominant_planet_weights,dominant_sign_weights,chart_type,source`

Notes:
- A header row that includes both `datetime_iso` and `latitude` is auto-detected and skipped.
- Comma-delimited and tab-delimited rows are both accepted.
- Datetime parsing accepts ISO values plus common variants (for example: `YYYY-MM-DD HH:MM`, `MM/DD/YYYY`, `Month DD YYYY`).
- If required data cannot be resolved (bad datetime, missing/un-geocodable place, etc.), the importer falls back to:
  - date at **12:00 UTC**
  - `lat=0.0`, `lon=0.0`
  - `used_utc_fallback=1` (warning)
- Date-only values are treated as unknown-time records and normalized to noon.

#### Minimal generic example

```csv
Ada Lovelace,1815-12-10 08:00,London UK
Alan Turing,1912-06-23,Cambridge UK
```

#### Round-trip/export-compatible example

```csv
id,name,birth_place,datetime_iso,tz_name,latitude,longitude,used_utc_fallback,sentiments,relationship_types,positive_sentiment_intensity,negative_sentiment_intensity,familiarity,dominant_planet_weights,dominant_sign_weights,chart_type,source
1,Grace Hopper,New York USA,1906-12-09T09:00:00,America/New_York,40.712800,-74.006000,0,"mentor, pioneer","friend",8,1,7,"{""Mercury"": 0.2}","{""Sagittarius"": 0.3}",public_db,public_db
```

### CSV format: **Import CSV from The Pattern**

The Pattern importer requires a header row that includes **all** of the following columns (case-insensitive):

- `full name`
- `birthday`
- `birth time`
- `gender`
- `birthtimezone`

Notes:
- `birthtimezone` should be a valid IANA timezone (for example `America/New_York`).
- Birth place is inferred from timezone (last segment, e.g. `America/Los_Angeles` → `Los Angeles`) and then geocoded.
- If `birth time` is `unknown`, or timezone/place/date cannot be resolved, importer falls back to **12:00 UTC** and `lat/lon=0.0`.
- `gender` normalization:
  - `f` → `F`
  - `m` → `M`
  - `unknown`/blank → unset

#### Pattern example

```csv
full name,birthday,birth time,gender,birthtimezone
Jane Doe,1992-04-03,14:20,f,America/Los_Angeles
John Doe,1988-11-30,unknown,m,Europe/London
```
# Composite charts (transit overlays + synastry)
See `docs/composite_charts_deployment.md` for deployment steps and new shared composition helpers.


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
- `Lilith` uses Swiss **Black Moon Lilith** (`SE_MEAN_APOG`, lunar apogee / empty focus of the Moon's ellipse) and is not asteroid 1181 Lilith.
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
