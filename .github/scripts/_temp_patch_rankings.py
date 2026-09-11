from pathlib import Path

path = Path("ephemeraldaddy/gui/ranking_panel.py")
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"Expected exactly one match, found {count}: {old[:120]!r}"
        )
    text = text.replace(old, new, 1)


replace_once(
    "import html\nfrom typing import Any\n\nfrom PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot\nfrom PySide6.QtWidgets import (\n    QComboBox,",
    "import html\nfrom pathlib import Path\nfrom typing import Any\n\nfrom PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot\nfrom PySide6.QtGui import QColor, QIcon, QPainter, QPixmap\nfrom PySide6.QtWidgets import (\n    QComboBox,\n    QFileDialog,",
)

replace_once(
    "        self._rankings_trait_visible_limits: dict[str, int] = {}\n        self._rankings_traits_sorted_order_cache:",
    "        self._rankings_trait_visible_limits: dict[str, int] = {}\n        self._rankings_sign_visible_limits: dict[tuple[bool, str], int] = {}\n        self._rankings_traits_sorted_order_cache:",
)

replace_once(
    "        trait_row_layout.addWidget(self.rankings_trait_combo, 1)\n        traits_layout.addWidget(trait_row)",
    "        trait_row_layout.addWidget(self.rankings_trait_combo, 1)\n        self.rankings_traits_export_button = QPushButton()\n        self._configure_rankings_export_button(\n            self.rankings_traits_export_button, \"traits\"\n        )\n        trait_row_layout.addWidget(self.rankings_traits_export_button)\n        traits_layout.addWidget(trait_row)",
)

replace_once(
    "        sign_row_layout.addWidget(self.rankings_sign_combo, 1)\n        most_sign_layout.addWidget(sign_row)",
    "        sign_row_layout.addWidget(self.rankings_sign_combo, 1)\n        self.rankings_signs_export_button = QPushButton()\n        self._configure_rankings_export_button(\n            self.rankings_signs_export_button, \"most_sign\"\n        )\n        sign_row_layout.addWidget(self.rankings_signs_export_button)\n        most_sign_layout.addWidget(sign_row)",
)

replace_once(
    "        most_sign_layout.addWidget(self.rankings_signs_label)\n\n        least_sign_layout = self._add_left_panel_collapsible_section(",
    "        most_sign_layout.addWidget(self.rankings_signs_label)\n        most_sign_more_row = QWidget()\n        most_sign_more_row_layout = QHBoxLayout(most_sign_more_row)\n        most_sign_more_row_layout.setContentsMargins(0, 0, 0, 0)\n        most_sign_more_row_layout.setSpacing(6)\n        most_sign_more_row_layout.addStretch(1)\n        self.rankings_signs_more_button = QPushButton(\"show next 10\")\n        self.rankings_signs_more_button.setToolTip(\n            \"Append the next 10 charts to this sign ranking.\"\n        )\n        self.rankings_signs_more_button.clicked.connect(\n            lambda: self._on_rankings_sign_show_next_clicked(least=False)\n        )\n        self.rankings_signs_more_button.setVisible(False)\n        most_sign_more_row_layout.addWidget(self.rankings_signs_more_button)\n        most_sign_layout.addWidget(most_sign_more_row)\n\n        least_sign_layout = self._add_left_panel_collapsible_section(",
)

replace_once(
    "        least_sign_row_layout.addWidget(self.rankings_least_sign_combo, 1)\n        least_sign_layout.addWidget(least_sign_row)",
    "        least_sign_row_layout.addWidget(self.rankings_least_sign_combo, 1)\n        self.rankings_least_signs_export_button = QPushButton()\n        self._configure_rankings_export_button(\n            self.rankings_least_signs_export_button, \"least_sign\"\n        )\n        least_sign_row_layout.addWidget(self.rankings_least_signs_export_button)\n        least_sign_layout.addWidget(least_sign_row)",
)

replace_once(
    "        least_sign_layout.addWidget(self.rankings_least_signs_label)\n        layout.addStretch(1)",
    "        least_sign_layout.addWidget(self.rankings_least_signs_label)\n        least_sign_more_row = QWidget()\n        least_sign_more_row_layout = QHBoxLayout(least_sign_more_row)\n        least_sign_more_row_layout.setContentsMargins(0, 0, 0, 0)\n        least_sign_more_row_layout.setSpacing(6)\n        least_sign_more_row_layout.addStretch(1)\n        self.rankings_least_signs_more_button = QPushButton(\"show next 10\")\n        self.rankings_least_signs_more_button.setToolTip(\n            \"Append the next 10 charts to this sign ranking.\"\n        )\n        self.rankings_least_signs_more_button.clicked.connect(\n            lambda: self._on_rankings_sign_show_next_clicked(least=True)\n        )\n        self.rankings_least_signs_more_button.setVisible(False)\n        least_sign_more_row_layout.addWidget(self.rankings_least_signs_more_button)\n        least_sign_layout.addWidget(least_sign_more_row)\n        layout.addStretch(1)",
)

marker = "    def _on_rankings_section_toggled(self, section: str, expanded: bool) -> None:\n"
helpers = '''    @staticmethod
    def _rankings_export_icon_path() -> str:
        return str(
            Path(__file__).resolve().parents[2] / "graphics" / "share_icon2.png"
        )

    def _configure_rankings_export_button(
        self, button: QPushButton, section: str
    ) -> None:
        button.setIcon(QIcon(self._rankings_export_icon_path()))
        button.setFlat(True)
        button.setFixedSize(26, 26)
        button.setToolTip("Export the currently revealed ranking as PNG.")
        button.clicked.connect(
            lambda _checked=False, section=section: self._export_rankings_section_png(
                section
            )
        )

    def _export_rankings_section_png(self, section: str) -> None:
        targets = {
            "traits": (
                "rankings_traits_label",
                "rankings_trait_combo",
                "trait-ranking",
            ),
            "most_sign": (
                "rankings_signs_label",
                "rankings_sign_combo",
                "most-dominant-sign",
            ),
            "least_sign": (
                "rankings_least_signs_label",
                "rankings_least_sign_combo",
                "least-dominant-sign",
            ),
        }
        target_spec = targets.get(section)
        if target_spec is None:
            return
        label_name, combo_name, filename_prefix = target_spec
        label = getattr(self, label_name, None)
        combo = getattr(self, combo_name, None)
        if not isinstance(label, QLabel):
            return

        context_name = "ranking"
        if isinstance(combo, QComboBox):
            context_name = str(combo.currentData() or combo.currentText() or "ranking")
        filename_token = "-".join(
            part
            for part in "".join(
                char if char.isalnum() else " " for char in context_name
            ).lower().split()
            if part
        ) or "ranking"
        default_name = f"{filename_prefix}-{filename_token}.png"
        save_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export ranking as PNG",
            default_name,
            "PNG images (*.png)",
        )
        if not save_path:
            return
        if not save_path.lower().endswith(".png"):
            save_path += ".png"

        label.ensurePolished()
        export_width = max(1, int(label.width()), int(label.sizeHint().width()))
        try:
            content_height = int(label.heightForWidth(export_width))
        except (TypeError, ValueError):
            content_height = int(label.sizeHint().height())
        export_height = max(
            1,
            int(label.height()),
            int(label.minimumHeight()),
            int(label.sizeHint().height()),
            content_height,
        )
        original_size = label.size()
        painter = None
        try:
            label.resize(export_width, export_height)
            pixmap = QPixmap(export_width, export_height)
            pixmap.fill(QColor("#17191d"))
            painter = QPainter(pixmap)
            label.render(painter)
            painter.end()
            painter = None
            pixmap.save(save_path, "PNG")
        finally:
            if painter is not None and painter.isActive():
                painter.end()
            label.resize(original_size)

'''
if marker not in text:
    raise SystemExit("Could not locate rankings helper insertion point")
text = text.replace(marker, helpers + marker, 1)

marker = "    def _sync_rankings_traits_scroll_height(self) -> None:\n"
sign_limit_helpers = '''    def _rankings_sign_visible_limit(self, selected_sign: str, *, least: bool) -> int:
        key = (bool(least), str(selected_sign or "").strip())
        if not key[1]:
            return 10
        limits = getattr(self, "_rankings_sign_visible_limits", None)
        if not isinstance(limits, dict):
            limits = {}
            self._rankings_sign_visible_limits = limits
        try:
            current_limit = int(limits.get(key, 10))
        except (TypeError, ValueError):
            current_limit = 10
        current_limit = max(10, current_limit)
        limits[key] = current_limit
        return current_limit

    def _on_rankings_sign_show_next_clicked(self, *, least: bool) -> None:
        combo_name = "rankings_least_sign_combo" if least else "rankings_sign_combo"
        combo = getattr(self, combo_name, None)
        if not isinstance(combo, QComboBox):
            return
        selected_sign = str(combo.currentText() or "").strip()
        if selected_sign not in ZODIAC_NAMES:
            return
        limits = getattr(self, "_rankings_sign_visible_limits", None)
        if not isinstance(limits, dict):
            limits = {}
            self._rankings_sign_visible_limits = limits
        key = (bool(least), selected_sign)
        limits[key] = self._rankings_sign_visible_limit(
            selected_sign, least=least
        ) + 10
        self._refresh_rankings_panel({"sign_dominance"})

'''
if marker not in text:
    raise SystemExit("Could not locate sign limit helper insertion point")
text = text.replace(marker, sign_limit_helpers + marker, 1)

replace_once(
    "        combo = getattr(self, combo_name, None)\n        label = getattr(self, label_name, None)\n        if not isinstance(combo, QComboBox) or not isinstance(label, QLabel):\n            return\n        selected_sign = str(combo.currentText() or \"\").strip()\n        if selected_sign not in ZODIAC_NAMES:\n            label.setText(\n                \"<span style='color:#9a9a9a;'>Select a sign to rank chart dominance.</span>\"\n            )\n            return",
    "        combo = getattr(self, combo_name, None)\n        label = getattr(self, label_name, None)\n        more_button_name = (\n            \"rankings_least_signs_more_button\"\n            if least\n            else \"rankings_signs_more_button\"\n        )\n        more_button = getattr(self, more_button_name, None)\n        if not isinstance(combo, QComboBox) or not isinstance(label, QLabel):\n            return\n        selected_sign = str(combo.currentText() or \"\").strip()\n        if selected_sign not in ZODIAC_NAMES:\n            if isinstance(more_button, QPushButton):\n                more_button.setVisible(False)\n            label.setText(\n                \"<span style='color:#9a9a9a;'>Select a sign to rank chart dominance.</span>\"\n            )\n            return",
)

replace_once(
    "        selected_top_20_keys = [\n            str(row.get(\"chart_uid\") or row.get(\"name\") or \"\").strip()\n            for row in rows[:20]\n        ]\n        shared_top_20_ranks = [\n            rank\n            for rank, chart_key in enumerate(selected_top_20_keys, start=1)\n            if len(sign_top_20_memberships.get(chart_key, ())) >= 2\n        ]\n        shared_top_20_count = len(shared_top_20_ranks)\n        deepest_shared_rank = max(shared_top_20_ranks, default=0)\n        display_limit = min(20, max(10 + shared_top_20_count, deepest_shared_rank))\n        if least:\n            display_limit = min(20, len(rows))",
    "        display_limit = min(\n            len(rows),\n            self._rankings_sign_visible_limit(selected_sign, least=least),\n        )\n        if isinstance(more_button, QPushButton):\n            more_button.setVisible(len(rows) > display_limit)",
)

replace_once(
    "        if not table_rows:\n            label.setText(\n                f\"<span style='color:#9a9a9a;'>No charts are available to rank for <b>{safe_sign}</b>.</span>\"\n            )\n            return",
    "        if not table_rows:\n            if isinstance(more_button, QPushButton):\n                more_button.setVisible(False)\n            label.setText(\n                f\"<span style='color:#9a9a9a;'>No charts are available to rank for <b>{safe_sign}</b>.</span>\"\n            )\n            return",
)

path.write_text(text, encoding="utf-8")
