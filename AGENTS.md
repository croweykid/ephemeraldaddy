# AGENTS.md

## Repo map
- app.py is the central GUI file.
- The app has 2 core modes: Database View (default) and Chart View (former default, legacy named 'Main', but actually secondary)
- Database View has 5 lefthand panels: Transit, Database Analytics, Genpop Analytics, Similarities Analysis and (when visible) Predictor Feedback. There are 3 lefthand panels: Search, Batch Editor (formerly combined with "Database Manager", but now separate), and Collections (aka "Collections Manager").
- Chart View has 
- Database Analytics live in 
- Additional popup menus: Settings, Properties Manager, Database Manager, Create Gemstone Chart
- Additional popup windows: Astro Twin (previously "Similar Charts"/"Similarities Calculator"), Human Design, BaZi, Synastry Chart, Chart Predictor Quiz, Guide to the Galaxy, Sign Degrees Reference Circle, Rectifier Engine (formerly "Retcon Engine"), and "Interpret Astro Age". Additionally, each graph (in most cases) has its own popout window.
- And a 'splash screen x loading bar' into, as well as a number of various dialogue boxes & loading bars.

## Protocol
- As much as possible of any task should be handled OUTSIDE of app.py, in the appropriate .py file in the interest of keeping app.py lightweight & lean.
- always reference charts by "UID" rather than the legacy "ID". IDs are not being phased out in favor of permanent UIDs.
- Anatomy of Graphs' popout windows: The default for every graph, appwide, is - when clicked - to spawn a popout window, with clickable bars and labels in the top (graph) panel that display associated info in their bottom 'Chart Info' panel. 
- Chart Info panels always display the names of signs, bodies/planets/positions, nakshatras, houses, aspect names, Human Design (HD) gates, centers, types, profiles, channels and authorities as color coded.
- Information Availability: Many charts lack a known birth time. For most of these, the metadata states birthtime merely as "unknown", but for some "rectified time" is assigned and treated as a provisional birth time for calculation purposes. Rectified times are hypothetical and not reliable. When data needs to be based on facts, not hunches, 'rectified time's shouldn't be applied. This is largely established in rules surrounding the binary "chart_uses_houses" property, which should always be baked into every major algorithmic change for the sake of continued accuracy and integrity.
- Key data for most charts (the dependencies for most calculations app wide) is recalculated based on only a few pieces of metadata: birth data, birth place, birth time, rectified time (if "use rectified time == TRUE"), and "chart_uses_houses". In some cases (like the Search panel or Tags section of Database Analytics), associated user-submitted tags for each chart are relevant, but most app features don't care about tag updates. Most other aspects of chart metadata are flavor text/subjective impressions by the user, and have no bearing on actual analytics, except where they are specifically referenced (i.e. the Database Analytics, Batch Editor and Search panels' Subjective Notes sections)

## Time Calculation