from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


FILESYSTEM_INFOGRAPHIC_ITEMS: tuple[dict[str, object], ...] = (
    {
        "path": "ephemeraldaddy/",
        "plain": "The app itself. Think of this as the house where the application lives.",
        "dev": "Importable Python package root; code normally imports from ephemeraldaddy.*.",
        "children": (
            ("gui/", "Screens, windows, buttons, popups, and user-facing interactions.", "PySide6 GUI layer; app.py remains the shell while feature widgets should live in focused modules."),
            ("core/", "The astrology engine and shared rules: charts, aspects, houses, interpretations, databases, backups, photos, and time helpers.", "Domain logic used by GUI and analysis modules; keep calculations here when they are not view-specific."),
            ("analysis/", "Special calculators and reference libraries: Astro Twin matching, Human Design, BaZi, Enneagram, traits, cycles, D&D-flavored analysis, and time sensitivity.", "Higher-level derived analytics; many files consume core chart data and cached metadata."),
            ("graphics/", "Drawing tools and visual assets, including chart wheels and emoji rendering support.", "Matplotlib/graphics helpers plus packaged image assets."),
            ("data/", "Reference datasets and generated population data the app reads from.", "Static/generated data inputs; compiled/ contains preprocessed artifacts."),
            ("io/", "Import, export, and place lookup plumbing.", "CSV/JSON/gazetteer/geocode boundaries."),
            ("ui/", "Command-line entry points for running the project outside the full desktop app.", "CLI package surface."),
            ("help/", "Help/reference materials shown or used by the app.", "User assistance content."),
        ),
    },
    {"path": "ephemeraldaddy/gui/app.py", "plain": "The main control room: it assembles the big windows, switches between Database View and Chart View, and wires buttons to features.", "dev": "Central legacy GUI orchestrator; new work should be pushed into smaller gui modules when practical."},
    {"path": "ephemeraldaddy/gui/dev_tools.py", "plain": "Developer tools and maintenance popups, including this file-system infographic.", "dev": "Settings > Developer Tools helpers and dialogs."},
    {"path": "ephemeraldaddy/gui/style.py", "plain": "The app-wide visual wardrobe: colors, spacing, button styling, and reusable look-and-feel helpers.", "dev": "Shared stylesheet constants and widget styling helpers."},
    {"path": "ephemeraldaddy/gui/dbv_search_panel.py", "plain": "The Database View search panel: helps users find and filter charts.", "dev": "Right-side DBV search UI and query controls."},
    {"path": "ephemeraldaddy/gui/features/", "plain": "Feature-specific panels and popout windows that keep app.py from becoming even larger.", "dev": "Nested feature modules, especially chart panels and analytics widgets."},
    {"path": "ephemeraldaddy/core/chart.py", "plain": "Builds the actual astrology chart data from birth information.", "dev": "Core chart calculation model and helpers."},
    {"path": "ephemeraldaddy/core/interpretations.py", "plain": "The encyclopedia of astrology meanings, labels, color coding, and descriptions.", "dev": "Primary interpretation/reference text source used throughout UI explanations."},
    {"path": "ephemeraldaddy/core/db.py", "plain": "The database doorway: saving, loading, and updating chart records.", "dev": "Persistence layer; prefer UID-based references for chart identity."},
    {"path": "ephemeraldaddy/analysis/get_astro_twin.py", "plain": "Finds similar charts and explains why two charts are alike or different.", "dev": "Similarity scoring settings, algorithms, caching, and relationship logging."},
    {"path": "ephemeraldaddy/analysis/human_design.py", "plain": "Calculates Human Design details from chart data.", "dev": "HD computation pipeline plus reference lookups."},
    {"path": "tests/", "plain": "Automated checks that protect important behavior from accidental breakage.", "dev": "Pytest suite; many tests are source-level guards for GUI wiring."},
    {"path": "docs/ and *.md notes", "plain": "Project notes, dev logs, summaries, and planning documents.", "dev": "Documentation outside the importable package."},
)


class FileSystemInfographicDialog(QDialog):
    """Animated, interactive dark-theme map of the repository for non-developers."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ephemeral Daddy File-System Infographic")
        self.setModal(False)
        self.setMinimumSize(980, 680)
        self.resize(1180, 760)
        self._cards: list[QFrame] = []
        self._animations: list[QPropertyAnimation] = []
        self.setStyleSheet("""
            QDialog { background: #090b12; color: #f4f7ff; }
            QLabel { color: #f4f7ff; }
            QPushButton { background: #202a44; color: #f4f7ff; border: 1px solid #5268ff; border-radius: 8px; padding: 8px 12px; }
            QPushButton:hover { background: #2f3d64; border-color: #8ed8ff; }
            QTreeWidget, QTextBrowser { background: #101525; color: #edf4ff; border: 1px solid #26365f; border-radius: 12px; padding: 8px; }
            QTreeWidget::item:selected { background: #3146a8; color: #ffffff; }
            QLineEdit { background: #111827; color: #ffffff; border: 1px solid #3b4e83; border-radius: 8px; padding: 8px; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        self._title = QLabel("🗺️ Ephemeral Daddy: app file-system tour")
        self._title.setStyleSheet("font-size: 28px; font-weight: 800; color: #9ee8ff;")
        root.addWidget(self._title)
        subtitle = QLabel("Click a folder or file to see its plain-English job. Use the search box to highlight anything you are curious about. The pulsing cards below show how data flows through the app.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #c7d2fe; font-size: 13px;")
        root.addWidget(subtitle)

        body = QHBoxLayout()
        root.addLayout(body, 1)
        left = QVBoxLayout()
        body.addLayout(left, 2)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search folders, files, or concepts…")
        self._search.textChanged.connect(self._filter_tree)
        left.addWidget(self._search)
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["File / folder", "Plain-English purpose"])
        self._tree.itemSelectionChanged.connect(self._show_selected_item)
        left.addWidget(self._tree, 1)

        right = QVBoxLayout()
        body.addLayout(right, 3)
        flow = QHBoxLayout()
        right.addLayout(flow)
        for label, caption in (
            ("Input", "birth data, notes, photos, tags"),
            ("Core", "chart math + shared rules"),
            ("Analysis", "meaning, matching, predictions"),
            ("GUI", "what the user sees and clicks"),
        ):
            card = QFrame()
            card.setStyleSheet("QFrame { background: #131a2e; border: 1px solid #334475; border-radius: 14px; padding: 10px; }")
            lay = QVBoxLayout(card)
            top = QLabel(label)
            top.setStyleSheet("font-size: 17px; font-weight: 800; color: #ffd166;")
            bot = QLabel(caption)
            bot.setWordWrap(True)
            bot.setStyleSheet("color: #dbeafe;")
            lay.addWidget(top)
            lay.addWidget(bot)
            flow.addWidget(card)
            self._cards.append(card)
        self._details = QTextBrowser()
        self._details.setOpenExternalLinks(False)
        right.addWidget(self._details, 1)

        buttons = QHBoxLayout()
        root.addLayout(buttons)
        expand = QPushButton("Expand all")
        collapse = QPushButton("Collapse all")
        expand.clicked.connect(self._tree.expandAll)
        collapse.clicked.connect(self._tree.collapseAll)
        buttons.addWidget(expand)
        buttons.addWidget(collapse)
        buttons.addStretch(1)

        self._populate_tree()
        self._start_animation()

    def _populate_tree(self) -> None:
        self._tree.clear()
        for entry in FILESYSTEM_INFOGRAPHIC_ITEMS:
            item = QTreeWidgetItem([str(entry["path"]), str(entry["plain"])])
            item.setData(0, Qt.UserRole, entry)
            self._tree.addTopLevelItem(item)
            for child in entry.get("children", ()):
                path, plain, dev = child
                child_item = QTreeWidgetItem([path, plain])
                child_item.setData(0, Qt.UserRole, {"path": path, "plain": plain, "dev": dev})
                item.addChild(child_item)
        self._tree.expandToDepth(0)
        self._tree.resizeColumnToContents(0)
        if self._tree.topLevelItemCount():
            self._tree.setCurrentItem(self._tree.topLevelItem(0))

    def _show_selected_item(self) -> None:
        items = self._tree.selectedItems()
        if not items:
            return
        data = items[0].data(0, Qt.UserRole) or {}
        child_rows = "".join(
            f"<li><b>{path}</b>: {plain}<br><small>Dev footnote: {dev}</small></li>"
            for path, plain, dev in data.get("children", ())
        )
        if child_rows:
            child_rows = f"<h3>What lives inside</h3><ul>{child_rows}</ul>"
        self._details.setHtml(f"""
            <style>
              body {{ background: #101525; color: #edf4ff; font-family: Arial, sans-serif; line-height: 1.45; }}
              h2 {{ color: #9ee8ff; }} h3 {{ color: #ffd166; }} small {{ color: #b7c4e8; }}
              .note {{ border-left: 4px solid #8b5cf6; padding: 8px 12px; background: #151d33; border-radius: 8px; }}
              code {{ color: #a7f3d0; }}
            </style>
            <h2>{data.get('path', '')}</h2>
            <p class="note"><b>Plain English:</b> {data.get('plain', '')}</p>
            <p><b>Dev footnote:</b> <code>{data.get('dev', 'Top-level map node; expand it for implementation-specific notes.')}</code></p>
            {child_rows}
            <h3>How to read this map</h3>
            <p><b>Folders</b> are neighborhoods. <b>Files</b> are individual workbenches. The GUI asks for things, core calculates reliable chart facts, analysis turns those facts into higher-level insight, and data/io keep outside information organized.</p>
        """)

    def _filter_tree(self, text: str) -> None:
        needle = text.strip().lower()
        def visit(item: QTreeWidgetItem) -> bool:
            own = needle in " ".join(item.text(i).lower() for i in range(2))
            child_match = False
            for i in range(item.childCount()):
                child_match = visit(item.child(i)) or child_match
            item.setHidden(bool(needle) and not own and not child_match)
            if child_match:
                item.setExpanded(True)
            return own or child_match
        for row in range(self._tree.topLevelItemCount()):
            visit(self._tree.topLevelItem(row))

    def _start_animation(self) -> None:
        for index, card in enumerate(self._cards):
            animation = QPropertyAnimation(card, b"maximumHeight", self)
            animation.setStartValue(86)
            animation.setEndValue(116)
            animation.setDuration(1200 + index * 180)
            animation.setEasingCurve(QEasingCurve.InOutSine)
            animation.setLoopCount(-1)
            animation.start()
            self._animations.append(animation)
