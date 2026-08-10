from types import MappingProxyType
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication

from ephemeraldaddy.gui.features.chart_editor.time_sensitivity.controller import (
    FineTuneHourlyScanController,
)
from ephemeraldaddy.gui.features.chart_editor.time_sensitivity.formatting import (
    format_fine_tune_hourly_scan_html,
)
from ephemeraldaddy.gui.features.chart_editor.time_sensitivity.hourly_scan import (
    FineTuneHourlyScanRequest,
    FineTuneHourlyScanResult,
    FineTuneSnapshot,
    FineTuneTransition,
    TransitionSection,
    fine_tune_hour_sample_minutes,
    transitions_between,
)


EMPTY = MappingProxyType({})


def snapshot(offset=0, **changes):
    values = {
        "minute_offset": offset,
        "time_label": f"01:{offset:02d}",
        "body_signs": EMPTY,
        "angle_signs": EMPTY,
        "cusp_signs": EMPTY,
        "body_houses": EMPTY,
        "relevant_aspects": EMPTY,
        "nakshatras": EMPTY,
        "hd_gate_lines": EMPTY,
    }
    values.update(changes)
    return FineTuneSnapshot(**values)


def test_hour_samples_are_half_open_and_have_truthful_counts():
    assert fine_tune_hour_sample_minutes(5) == tuple(range(0, 60, 5))
    assert len(fine_tune_hour_sample_minutes(5)) == 12
    assert fine_tune_hour_sample_minutes(1) == tuple(range(60))
    assert len(fine_tune_hour_sample_minutes(1)) == 60


def test_request_is_uid_first_and_rejects_unsupported_resolution():
    with pytest.raises(ValueError, match="chart UID"):
        FineTuneHourlyScanRequest("", 1, 1)
    with pytest.raises(ValueError, match="resolution"):
        FineTuneHourlyScanRequest("chart-uid", 1, 2)  # type: ignore[arg-type]


def test_transitions_are_grouped_into_requested_sections():
    before = snapshot(
        body_signs={"Moon": "Aries"},
        angle_signs={"AS": "Aries"},
        cusp_signs={1: "Aries"},
        body_houses={"Moon": 1},
        relevant_aspects={(('Moon', 'Sun'), 'trine'): 0.1},
        nakshatras={"Moon": "Ashwini"},
        hd_gate_lines={("personality", "Moon"): (1, 2)},
    )
    after = snapshot(
        3,
        body_signs={"Moon": "Taurus"},
        angle_signs={"AS": "Taurus"},
        cusp_signs={1: "Taurus"},
        body_houses={"Moon": 2},
        relevant_aspects={},
        nakshatras={"Moon": "Bharani"},
        hd_gate_lines={("personality", "Moon"): (2, 1)},
    )

    transitions = transitions_between(before, after)

    assert {item.section for item in transitions} == set(TransitionSection)
    aspect = next(item for item in transitions if item.section is TransitionSection.ASPECT_CHANGES)
    assert aspect.current_value == "moved out of relevance"
    hd = next(item for item in transitions if item.section is TransitionSection.HD_GATE_LINE_CHANGES)
    assert (hd.previous_value, hd.current_value) == ("Gate 1.2", "Gate 2.1")


def test_formatter_renders_every_section_and_relevance_language():
    result = FineTuneHourlyScanResult(
        chart_uid="chart-uid",
        start_hour=1,
        resolution_minutes=1,
        displayed_sample_count=60,
        refined_sample_count=0,
        uses_houses=False,
        transitions=(
            FineTuneTransition(
                3,
                "01:03",
                TransitionSection.ASPECT_CHANGES,
                "Moon trine Sun",
                "relevant",
                "moved out of relevance",
            ),
        ),
    )

    html = format_fine_tune_hourly_scan_html(result)

    for section in TransitionSection:
        assert section.value in html
    assert "01:03" in html
    assert "moved out of relevance" in html
    assert "does not use houses" in html


class HoldingThreadPool:
    def __init__(self):
        self.workers = []

    def start(self, worker):
        self.workers.append(worker)


def test_controller_discards_result_from_superseded_request():
    QCoreApplication.instance() or QCoreApplication([])
    pool = HoldingThreadPool()

    def compute(_chart, request):
        return FineTuneHourlyScanResult(
            chart_uid=request.chart_uid,
            start_hour=request.start_hour,
            resolution_minutes=request.resolution_minutes,
            displayed_sample_count=60,
            refined_sample_count=0,
            uses_houses=True,
            transitions=(),
        )

    controller = FineTuneHourlyScanController(thread_pool=pool, compute=compute)
    received = []
    controller.result_ready.connect(received.append)
    chart = SimpleNamespace(chart_uid="chart-uid")
    controller.start(chart, FineTuneHourlyScanRequest("chart-uid", 1, 1))
    controller.start(chart, FineTuneHourlyScanRequest("chart-uid", 2, 1))

    pool.workers[1].run()
    pool.workers[0].run()

    assert [result.start_hour for result in received] == [2]
