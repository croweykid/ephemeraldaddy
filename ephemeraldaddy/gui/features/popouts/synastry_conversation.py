"""Parser and renderer for the bundled Twine synastry conversation."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from importlib import resources
from pathlib import Path
from urllib.parse import quote


_LINK_PATTERN = re.compile(r"\[\[([^\]]+?)(?:->|-&gt;)([^\]]+)\]\]|\[\[([^\]]+)\]\]")


class _TwinePassageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.passages: dict[str, str] = {}
        self.start_name = ""
        self._active_name: str | None = None
        self._chunks: list[str] = []
        self._start_pid = ""
        self._pid_names: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "tw-storydata":
            self._start_pid = attributes.get("startnode") or ""
        elif tag == "tw-passagedata":
            self._active_name = attributes.get("name") or ""
            self._pid_names[attributes.get("pid") or ""] = self._active_name
            self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._active_name is not None:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "tw-passagedata" and self._active_name is not None:
            self.passages[self._active_name] = "".join(self._chunks).strip()
            self._active_name = None
            self._chunks = []

    def close(self) -> None:
        super().close()
        self.start_name = self._pid_names.get(self._start_pid, "")


def load_synastry_conversation(source_path: Path | None = None) -> tuple[str, dict[str, str]]:
    """Load passage text from the packaged Twine HTML export."""
    if source_path is None:
        story_text = (
            resources.files("ephemeraldaddy.gui.features.popouts")
            .joinpath("assets", "what_is_synastry.html")
            .read_text(encoding="utf-8")
        )
        source_description = "bundled what_is_synastry.html"
    else:
        story_text = source_path.read_text(encoding="utf-8")
        source_description = str(source_path)
    parser = _TwinePassageParser()
    parser.feed(story_text)
    parser.close()
    if not parser.passages or not parser.start_name:
        raise ValueError(f"No Twine passages found in {source_description}")
    return parser.start_name, parser.passages


def passage_html(source: str) -> str:
    """Convert the small subset of Harlowe markup used by this story."""
    rendered = html.escape(source, quote=False)
    rendered = re.sub(r"&lt;(/?h[1-3])&gt;", r"<\1>", rendered, flags=re.IGNORECASE)
    rendered = re.sub(r"''(.*?)''", r"<strong>\1</strong>", rendered, flags=re.DOTALL)
    rendered = re.sub(r"//(.*?)//", r"<em>\1</em>", rendered, flags=re.DOTALL)

    def _link(match: re.Match[str]) -> str:
        label = match.group(1) or match.group(3)
        target = html.unescape(match.group(2) or label)
        return f'<a href="twine:{quote(target, safe="")}">{label}</a>'

    rendered = _LINK_PATTERN.sub(_link, rendered)
    lines = rendered.splitlines()
    output: list[str] = []
    in_list = False
    for line in lines:
        if line.startswith("* "):
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{line[2:]}</li>")
        else:
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append(line if line.startswith("<h") else f"<p>{line}</p>" if line else "")
    if in_list:
        output.append("</ul>")
    return "\n".join(output)
