import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ephemeraldaddy.gui.features.charts.render_queue import ChartRenderQueueState


def test_discard_if_unqueued_removes_popped_stale_pending_section():
    queue = ChartRenderQueueState()
    queue.enqueue(sections={"summary", "signs"}, render_order=("summary", "signs"), priority="interactive")

    popped = queue.pop_next()
    assert popped == "summary"

    # A newer schedule filtered down to a different subset, so the popped section
    # should not remain pending without any queue entry to render it.
    queue.enqueue(sections={"signs"}, render_order=("summary", "signs"), priority="interactive")
    queue.discard_if_unqueued("summary")

    assert "summary" not in queue.pending_sections
    assert queue.has_queued_work()
    assert queue.pop_next() == "signs"


def test_discard_if_unqueued_keeps_requeued_stale_section_pending():
    queue = ChartRenderQueueState()
    queue.enqueue(sections={"summary", "signs"}, render_order=("summary", "signs"), priority="interactive")

    popped = queue.pop_next()
    assert popped == "summary"

    # A newer schedule asked for the same section again, so the fresh queue entry
    # must still render and must not be marked complete by the stale flush.
    queue.enqueue(sections={"summary"}, render_order=("summary", "signs"), priority="interactive")
    queue.discard_if_unqueued("summary")

    assert "summary" in queue.pending_sections
    assert "summary" in queue.interactive_queue
