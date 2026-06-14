import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ephemeraldaddy.core.loading_messages import LoadingMessageRotator, LoadingSequence


def test_sequences_are_shuffled_without_repeating_until_all_have_run(monkeypatch):
    sequences = (
        LoadingSequence("one", ("one-a", "one-b")),
        LoadingSequence("two", ("two-a",)),
        LoadingSequence("three", ("three-a",)),
    )
    rotations = [list(reversed(sequences)), list(sequences)]

    def fake_shuffle(values):
        values[:] = rotations.pop(0)

    monkeypatch.setattr("ephemeraldaddy.core.loading_messages.random.shuffle", fake_shuffle)
    rotator = LoadingMessageRotator(
        sequences=sequences,
        standalone_messages=(),
        initial_message="start",
        sequence_probability=1.0,
    )

    assert rotator.next() == "start"
    assert rotator.next() == "three-a"
    assert rotator.next() == "two-a"
    assert rotator.next() == "one-a"
    assert rotator.next() == "one-b"
    assert rotator.next() == "one-a"


def test_standalone_messages_can_be_interspersed_between_sequence_starts(monkeypatch):
    sequence = LoadingSequence("seq", ("seq-a",))
    random_values = iter((0.9, 0.1))
    monkeypatch.setattr("ephemeraldaddy.core.loading_messages.random.random", lambda: next(random_values))
    monkeypatch.setattr("ephemeraldaddy.core.loading_messages.random.choice", lambda values: values[0])

    rotator = LoadingMessageRotator(
        sequences=(sequence,),
        standalone_messages=("solo",),
        initial_message="start",
        sequence_probability=0.5,
    )

    assert rotator.next() == "start"
    assert rotator.next() == "solo"
    assert rotator.next() == "seq-a"


def test_display_interval_scales_proportionately_after_twenty_characters():
    rotator = LoadingMessageRotator()

    assert rotator.display_interval_ms("x" * 20, default_ms=3200) == 3200
    assert rotator.display_interval_ms("x" * 40, default_ms=3200) == 6400
    assert rotator.display_interval_ms("x" * 30, default_ms=3200) == 4800
