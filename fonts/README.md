# Bundled symbol fonts

Place symbol-capable static font files here for packaged builds.

Recommended:
- `NotoSansSymbols2-Regular.ttf` (or `.otf`)
- optionally `NotoSansSymbols-Regular.ttf`

Notes:
- Prefer **static** font files for cross-platform packaging reliability.
- Variable fonts may work but can render inconsistently in some older FreeType/fontconfig stacks.
- The app automatically registers `.ttf`, `.otf`, and `.ttc` files in this folder at startup.
- You can also point to an external folder for testing with `EPHEMERALDADDY_FONT_DIR`.
