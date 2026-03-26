"""Bundled About dialog content for desktop builds."""

ABOUT_ONBOARDING_MARKDOWN = r"""# EphemeralDaddy Onboarding (New User Survival Guide)

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

## 1) Where things are in the app

### **A. Chart View (Chart Entry / Editor)**
This is where you create or edit one chart at a time.

Key features:
- **Name / Alias / Birth date / Birth place** inputs
- **Chart Type** dropdown
- **placeholder (check if birth date/year is unknown)** checkbox
- Save/update controls
- Right-side metrics and mini-analysis widgets

Use this window when you want to:
- Enter a new chart
- Edit an existing one
- Mark a chart as a placeholder
- Set chart classification manually

### **B. Database View (Manage Charts)**
This is mission control for your whole chart collection.

Key features:
- Chart list in the center
- Search/filter panel (includes **Chart Type**)
- Sorting options (including **Cursedness**)
- Data management actions (backup/import/export)
- Buttons for **Transit View** and **🧬 Composite**

Use this window when you want to:
- Browse and filter lots of charts
- Batch-manage records
- Open transit/composite tools
- Import or export CSV datasets

### **C. Transit View**
This is for current/dated transit overlays and “what’s active now” checks.

Use it when you want:
- Transit snapshots
- Daily vibe / life forecast style transit windows
- A practical, quick-look timing tool

### **D. Composite / Synastry tools**
This currently gives you a basic chart-over-chart aspect workflow.

Use it when you want:
- A rough compatibility lens
- Overlay-style chart comparison

⚠️ Synastry Tools are still early-stage (details below in the Synastry section).

---

## 2) Core features of Ephemeral Daddy (what they’re called + how they work)

## Chart calculation: methods & philosophy
- Planetary positions are computed with Swiss Ephemeris-backed logic (with offline setup supported).
- The app computes positions, houses, and aspects, then derives distributions and ranking-style metrics.
- Philosophy-wise: this is built as an exploratory tool. It favors inspectable intermediate outputs over pretending every interpretation is settled truth.
- Practical takeaway: treat calculations as structured inputs; treat textual interpretations as draft commentary.

## “Planet” / Sign / House weighting methods
- Weighting blends traditional astro ideas (dignity/rulership/exaltation/fall style ingredients) with project-specific observation-based tweaks.
- Aspect scoring is weighted by aspect type + body weights + orb influence.
- House weighting is conservative (with extra emphasis on key angles rather than pretending every house weight is equally robust).
- Non-standard bit: some scoring knobs (including quirky metrics) are deliberately experimental and intended for comparative use, not dogma.

## Chart Types
- **Chart Type** is a classifier/tag for what a chart record is (for example: personal, public database import, event, synastry-generated contexts).
- You set this manually in **Natal Chart View** (Chart Entry/Edit).
- The app also assigns defaults in some generation/import pathways.
- In **Manage Charts**, Chart Type is filterable, so you can separate personal notes from imported/public datasets.

## Sign/Position descriptions (important reality check)
Short version: useful as rough prompts, not gospel.

Longer version:
- The built-in interpretation text is still a work in progress and can read like procedural mad-libs.
- If you need polished narrative interpretation, you’ll often get better results by copying chart output into GPT/Claude (or doing your own independent research).
- The sign definitions in this project came from repeated observation work and cohort comparisons (including many public figures, which can bias toward “public persona” expression).
- Pattern-finding experiments (including blind/non-zodiac labeling during analysis) informed which recurring themes were kept, but this remains interpretive work, not hard science.

## Placeholder charts
What they are:
- A reminder/contact-style chart entry when exact birth data is missing.

What they’re good for:
- Relationship notes
- Sentiment/history tracking
- Non-astrological organization

What they’re **not** good for:
- Serious astrological inference

If you’re doing real astro research, placeholders are your polite sticky note saying:
> “Important person, incomplete data — come back later with actual birth info.”

## Nakshatras
- Zodiac sign framework in this app is tropical.
- Nakshatras are handled separately in the usual Vedic-style spirit.
- The author’s nakshatra notes are intentionally rough research notes, not a finished published doctrine.
- If you want to refine/replace them, `core/interpretations.py` is where contributions/forks can build cleaner definitions.

## Gates, Lines & Channels
For anyone familiar with the framework: in Chart View, G stands for gates, and L stands for lines, but I haven't done anything with channels yet, nor included any interpretations of I Ching hexagrams, nor calculated "Earth Signs", etc. Some of that stuff is proprietary IP - not public domain, and there are limits to how much can be included in an open source app. But certain enquiring minds wanted to know, and math is open source, so there you go.
As far as what's fair game, legally, the rest is in the works. Please stand by.

## Weird toy metrics (D&D Species, Cursedness, Gender Guesser)
These exist. They are fun. They are not commandments.

- **D&D Species**: vibe-based speculative classifier.
- **Cursedness**: weighted “chaos/strain flavor” score for entertainment + comparative curiosity.
- **Gender Guesser**: partially lore-inspired, partially experimental scoring, with a spectrum-oriented treatment rather than strict binary sign assignment.

Recommended posture:
- Use these as playful side channels and conversation starters.
- Do not build your worldview, hiring policy, or romantic destiny on them.

## Synastry/composite status
- Current synastry/composite support is functional but basic.
- Aspect math is there; relevance filtering and presentation polish are still maturing.
- Chart visualization for these workflows is still being refined.

Practical tip right now:
- Generate the data here.
- If you need sharp prose synthesis immediately, paste output into an LLM and ask it to rank the most relevant dynamics.

---

## 3) Data + privacy essentials
- Your database is local (stored in your home directory), not bundled inside the app folder.
- Sharing the app directory alone does not automatically share your chart database.
- Use built-in import/export/backup tools for intentional migration or sharing.

---

## 4) Suggested new-user workflow (fast start)
1. Create your own chart in **Natal Chart View**.
2. Add 5–20 known people in **Manage Charts**.
3. Use **Chart Type** tags early (future-you will be grateful).
4. Use placeholders for unknown birth-time/date cases.
5. Run transit/composite tools for pattern exploration.
6. Treat interpretation text as draft notes; verify externally when stakes are high.
7. Enjoy the weird toys, but keep one eyebrow raised.

---

## Final Takeaways
EphemeralDaddy is best used like a field notebook with a calculator attached.
If you expect a perfect oracle, you’ll be disappointed.
If you want a lively research cockpit with honest rough edges, you’re in exactly the right place.
"""
