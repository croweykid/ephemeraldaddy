"""Queue helpers for Chart View analytics rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal


RenderQueuePriority = Literal["interactive", "background"]


@dataclass
class ChartRenderQueueState:
    """Tracks pending Chart View section renders with interactive-first semantics."""

    pending_sections: set[str] = field(default_factory=set)
    interactive_queue: list[str] = field(default_factory=list)
    background_queue: list[str] = field(default_factory=list)

    def clear(self) -> None:
        self.pending_sections.clear()
        self.interactive_queue.clear()
        self.background_queue.clear()

    def enqueue(
        self,
        *,
        sections: Iterable[str],
        render_order: tuple[str, ...],
        priority: RenderQueuePriority,
    ) -> None:
        section_set = set(sections)
        if not section_set:
            return
        self.pending_sections.update(section_set)
        target_queue = (
            self.interactive_queue
            if priority == "interactive"
            else self.background_queue
        )
        source_queue = (
            self.background_queue
            if priority == "interactive"
            else self.interactive_queue
        )

        for section_name in render_order:
            if section_name not in section_set:
                continue
            if section_name in source_queue:
                source_queue.remove(section_name)
            if section_name in target_queue:
                target_queue.remove(section_name)
            target_queue.append(section_name)

    def pop_next(self) -> str | None:
        if self.interactive_queue:
            return self.interactive_queue.pop(0)
        if self.background_queue:
            return self.background_queue.pop(0)
        return None

    def mark_complete(self, section_name: str) -> None:
        self.pending_sections.discard(section_name)

    def discard_if_unqueued(self, section_name: str) -> None:
        """Discard a pending section only when no queue will render it.

        A stale render flush may have popped ``section_name`` from a queue before
        a newer schedule changes the queue contents.  If the newer schedule did
        not requeue that same section, leaving it in ``pending_sections`` wedges
        the queue because there is pending work but no queued entry to pop.
        When the newer schedule *did* requeue the section, keep it pending so
        the fresh render still runs.
        """
        if section_name in self.interactive_queue or section_name in self.background_queue:
            return
        self.pending_sections.discard(section_name)

    def has_pending_work(self) -> bool:
        return bool(self.pending_sections)

    def has_queued_work(self) -> bool:
        return bool(self.interactive_queue or self.background_queue)
