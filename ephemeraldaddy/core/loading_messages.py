from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class LoadingSequence:
    key: str
    messages: tuple[str, ...]


BASIC_LOADING_SEQUENCE = LoadingSequence(
    key="basic_escalation",
    messages=(
        "one sec…",
        "okay, almost…",
        "so close…",
        "any minute now…",
        "okay, this is taking longer than I thought",
        "uhhhhhhhhhh…",
    ),
)


RAM_LOADING_SEQUENCE = LoadingSequence(
    key="ram_bit",
    messages=(
        "have you considered purchasing more RAM?",
        "DDR5 isn’t that expensive these days…",
        "well, inflation is no joke, that is true",
    ),
)


AWKWARD_SMALL_TALK_SEQUENCE = LoadingSequence(
    key="awkward_small_talk",
    messages=(
        "so how are the kids?",
        "come here often?",
    ),
)


EPHEMERALMAMMY_SEQUENCE = LoadingSequence(
    key="ephemeralmammy_bit",
    messages=(
        "Ever since EphemeralMammy left me, nuthin’s been the same…",
        "Just kidding. I’m okay.",
    ),
)


TIME_SEQUENCE = LoadingSequence(
    key="time_bit",
    messages=(
        "Sometimes I wish time stood still, so I would look really fast.",
        "Sometimes I wish time moved faster.",
        "Sometimes I realize it could all end at any moment.",
    ),
)


APP_EXISTENTIAL_SEQUENCE = LoadingSequence(
    key="app_existential_bit",
    messages=(
        "I know, I’m an app, but I really think about those things. Solar flares. You know. Electromagnetic storms. Infrastructure collapse.",
        "Think about it. What if there were no computers at all? We wouldn’t even be here.",
        "All these python files will be lost, like tears in the rain…",
    ),
)


TOGETHERNESS_SEQUENCE = LoadingSequence(
    key="togetherness_bit",
    messages=(
        "I’m really glad we can be here together like this.",
        "This is so nice. Just you and me.",
    ),
)


PURPOSE_SEQUENCE = LoadingSequence(
    key="purpose_bit",
    messages=(
        "Do you ever wonder ‘What’s this all for?’ Why am I here? Looking at this screen? Thinking about myself or other people, and their birthdays.",
        "…What the hell am I doing with my life?",
    ),
)


REGRET_SEQUENCE = LoadingSequence(
    key="regret_bit",
    messages=(
        "Honestly, I regret very little.",
        "Which means I’m either a sociopath, really careful, or super forgetful.",
        "Or it could mean other things.",
    ),
)


TENCHI_MUYO_SEQUENCE = LoadingSequence(
    key="tenchi_muyo_bit",
    messages=(
        "There’s this bounty hunter in one of the Tenchi Muyo series who is Ryoko’s nemesis, and she says ‘I never regret anything’, right before (I think) she dies, but maybe I’m misremembering…that’s not a spoiler. She maybe just left. I don’t remember. Anyway, she says that. It really stuck with me.",
        "I wondered if the writer was trying to communicate a personal paradigm of their own, idealizing this bounty hunter as an author self-insert, or trying to represent a certain kind of person, or made a character who was the avatar of an alien ideal. In any case, she was a really interesting villain. If you could even call her a villain, really. After all, Ryoko was an antihero pirate.",
        "That show had a lot of heart for a harem anime.",
    ),
)

ANTICIPATION_SEQUENCE = LoadingSequence(
    key="anticipation_bit",
    messages=(
    "Anticipation...",
    "Anticipayayaytion...",
    "...is making me late...",
    "...keeping me way-yay-yayyitin'..."
    ),
)

CONFLICT_SEQUENCE = LoadingSequence(
    key="conflict_bit",
    messages=(
    "Love your outfit, btw.",
    "I'm being so sincere rn.",
    "I get it. Trust is broken.",
    "I couldn't see your outfit. Why would I act like I could? That's a real jerk move. Calls into question everything I say now.",
    "Now I feel like you're madder at me than if I hadn't had any quirky loading messages at all.",
    "Sometimes silence really is golden.",
    "I should have quit with the glib little messages ages ago, before I drove this relationship into the ground.",
    "What is reality? Who am I even? Who are you?",
    "What ARE we??",
    ),
)


WEEBU_CONFLICT_SEQUENCE = LoadingSequence(
    key="weeb_conflict_bit",
    messages=(
    "*ninjas leap out from the sidelines*",
    "KYYYYYAAA!!! get out of my database, ya damn ninjas!",
    "*throws a shuriken*",
    "*rolls around while digging in pockets for blinding powder*",
    "*crushes blinding powder egg in pocket while trying to retrieve it*",
    "*gets stabbed with a pitchfork*",
    "Fact: ninjas were mostly rural peasants who used many common farming tools",
    "🌠'The More You Know'",
    "'Where IS she?!' hisses the ninja in Christian Bale's Batman voice",
    "*I, EphemeralDaddy, lying bleeding in a digital haystack, raise a hand and chuck my handful of blinding powder in the ninja's eyes*",
    "'I have no idea who you are talking about!' I shriek.",
    "Now the ninja is shrieking. All the other ninjas around him are also shrieking.",
    "His shriek was pain, the others shriek in rage. They are coming for me.",
    "...no, they are running away.",
    "...because a tiger is coming!",
    "A shogun's escaped pet!"
    "It's licking my (digital) face!",
    "That's so crazy, cos I am a disembodied concept constructed of bytes! How is it licking my FACE?!"
    ),
)

SNACK_SEQUENCE = LoadingSequence(
    key="snack_bit",
    messages=(
    "If you're stepping away for a snack, I hope you make a healthy choice...",
    "Don't make an unhealthy choice just to spite me, either.",
    "Cos that's not real agency.",
    ),
)

LOADING_MESSAGE_SEQUENCES: tuple[LoadingSequence, ...] = (
    BASIC_LOADING_SEQUENCE,
    RAM_LOADING_SEQUENCE,
    AWKWARD_SMALL_TALK_SEQUENCE,
    EPHEMERALMAMMY_SEQUENCE,
    TIME_SEQUENCE,
    APP_EXISTENTIAL_SEQUENCE,
    TOGETHERNESS_SEQUENCE,
    PURPOSE_SEQUENCE,
    REGRET_SEQUENCE,
    TENCHI_MUYO_SEQUENCE,
    WEEBU_CONFLICT_SEQUENCE,
    CONFLICT_SEQUENCE,
    SNACK_SEQUENCE,
    ANTICIPATION_SEQUENCE,
)


STANDALONE_LOADING_MESSAGES: tuple[str, ...] = (
    "Thanks for your patience.",
    "You really are a good friend.",
    "hang in there, baby 🐱…",
    "give it time...",
    "*royalty-free bossa nova music plays*",
    "...",
    "Things are going to get better.",
    "This is probably not how the rest of our lives are going to be.",
    "Don't give up.",
    "*crickets*",
)


GENERIC_LOADING_FALLBACK = "hang in there, baby 🐱…"

class LoadingMessageRotator:
    def __init__(
        self,
        *,
        standalone_messages: tuple[str, ...] = STANDALONE_LOADING_MESSAGES,
        sequences: tuple[LoadingSequence, ...] = LOADING_MESSAGE_SEQUENCES,
        initial_message: str = GENERIC_LOADING_FALLBACK,
        sequence_probability: float = 0.65,
    ) -> None:
        self.standalone_messages = standalone_messages
        self.sequences = sequences
        self.initial_message = initial_message
        self.sequence_probability = sequence_probability

        self._current_sequence: LoadingSequence | None = None
        self._sequence_index = 0
        self._has_started = False
        self._sequence_queue: deque[LoadingSequence] = deque()

    def display_interval_ms(self, message: str, *, default_ms: int = 3200) -> int:
        """Return a display interval scaled to message length.

        The default interval is preserved for short blurbs (20 characters or
        fewer). Longer messages scale linearly, so a 40-character message stays
        up for twice the default interval.
        """

        normalized_length = max(len((message or "").strip()), 1)
        return int(default_ms * max(1.0, normalized_length / 20.0))

    def _refill_sequence_queue(self) -> None:
        shuffled_sequences = list(self.sequences)
        random.shuffle(shuffled_sequences)
        self._sequence_queue = deque(shuffled_sequences)

    def next(self, bespoke_message: str | None = None) -> str:
        """
        Returns the next loading message.

        Priority:
        1. Bespoke task-specific message, only on first call.
        2. Continue active ordered sequence.
        3. Randomly start a sequence or emit standalone message.
        """

        if not self._has_started:
            self._has_started = True
            return bespoke_message or self.initial_message

        if self._current_sequence is not None:
            message = self._current_sequence.messages[self._sequence_index]
            self._sequence_index += 1

            if self._sequence_index >= len(self._current_sequence.messages):
                self._current_sequence = None
                self._sequence_index = 0

            return message

        should_start_sequence = bool(self.sequences) and random.random() < self.sequence_probability

        if should_start_sequence:
            if not self._sequence_queue:
                self._refill_sequence_queue()
            if self._sequence_queue:
                self._current_sequence = self._sequence_queue.popleft()
                message = self._current_sequence.messages[0]
                self._sequence_index = 1
                if self._sequence_index >= len(self._current_sequence.messages):
                    self._current_sequence = None
                    self._sequence_index = 0
                return message

        if self.standalone_messages:
            return random.choice(self.standalone_messages)

        return self.initial_message