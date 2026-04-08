from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.core.interpretations import NATAL_WEIGHT


SIGN_NAMES: tuple[str, ...] = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)


@dataclass(frozen=True)
class QuizOption:
    label: str
    body_scores: dict[str, float]
    house_scores: dict[int, float]
    sign_scores: dict[str, float]
    madlib_fragment: str


@dataclass(frozen=True)
class QuizQuestion:
    prompt: str
    options: tuple[QuizOption, ...]


def _option(
    label: str,
    *,
    body_scores: dict[str, float] | None = None,
    house_scores: dict[int, float] | None = None,
    sign_scores: dict[str, float] | None = None,
    madlib_fragment: str,
) -> QuizOption:
    return QuizOption(
        label=label,
        body_scores=body_scores or {},
        house_scores=house_scores or {},
        sign_scores=sign_scores or {},
        madlib_fragment=madlib_fragment,
    )


QUIZ_QUESTIONS: tuple[QuizQuestion, ...] = (
    QuizQuestion(
        prompt="When plans change last-minute, your reflex is:",
        options=(
            _option(
                "take charge and improvise",
                body_scores={"Mars": 4, "Sun": 2, "AS": 2},
                house_scores={1: 3, 10: 2},
                sign_scores={"Aries": 2, "Leo": 1},
                madlib_fragment="kicks the door open and writes a new script",
            ),
            _option(
                "talk it out and gather data",
                body_scores={"Mercury": 4, "Moon": 1, "Jupiter": 1},
                house_scores={3: 3, 6: 2},
                sign_scores={"Gemini": 2, "Virgo": 1},
                madlib_fragment="builds a map made of conversations and clues",
            ),
            _option(
                "feel it out before moving",
                body_scores={"Moon": 4, "Venus": 2, "Neptune": 1},
                house_scores={4: 3, 12: 2},
                sign_scores={"Cancer": 2, "Pisces": 1},
                madlib_fragment="reads the room like weather before taking a step",
            ),
        ),
    ),
    QuizQuestion(
        prompt="What kind of recognition feels most satisfying?",
        options=(
            _option(
                "public impact and achievement",
                body_scores={"Sun": 4, "Saturn": 2, "MC": 2},
                house_scores={10: 4, 1: 1},
                sign_scores={"Capricorn": 2, "Leo": 1},
                madlib_fragment="wants the mountain peak and skyline view",
            ),
            _option(
                "trusted one-on-one bonds",
                body_scores={"Venus": 4, "Moon": 2, "DS": 2},
                house_scores={7: 4, 4: 1},
                sign_scores={"Libra": 2, "Cancer": 1},
                madlib_fragment="finds power in mirrors and promises",
            ),
            _option(
                "freedom to reinvent everything",
                body_scores={"Uranus": 4, "Pluto": 2, "Rahu": 1},
                house_scores={11: 3, 8: 2},
                sign_scores={"Aquarius": 2, "Scorpio": 1},
                madlib_fragment="rewires the game and calls it growth",
            ),
        ),
    ),
    QuizQuestion(
        prompt="Your ideal weekend usually includes:",
        options=(
            _option(
                "adventure, action, movement",
                body_scores={"Mars": 3, "Jupiter": 3, "Sun": 1},
                house_scores={9: 3, 5: 2},
                sign_scores={"Sagittarius": 2, "Aries": 1},
                madlib_fragment="chases horizons until the map runs out",
            ),
            _option(
                "beauty, art, delicious comfort",
                body_scores={"Venus": 4, "Moon": 2, "Ceres": 1},
                house_scores={2: 3, 5: 2},
                sign_scores={"Taurus": 2, "Libra": 1},
                madlib_fragment="collects textures, tastes, and tiny luxuries",
            ),
            _option(
                "deep dive into mysteries",
                body_scores={"Pluto": 4, "Ketu": 2, "Saturn": 1},
                house_scores={8: 4, 12: 1},
                sign_scores={"Scorpio": 2, "Pisces": 1},
                madlib_fragment="goes spelunking in shadow archives",
            ),
        ),
    ),
    QuizQuestion(
        prompt="In conflicts, you tend to:",
        options=(
            _option(
                "set boundaries and structure quickly",
                body_scores={"Saturn": 4, "Mars": 2, "MC": 1},
                house_scores={6: 2, 10: 2, 1: 1},
                sign_scores={"Capricorn": 2, "Virgo": 1},
                madlib_fragment="draws the line in ink and means it",
            ),
            _option(
                "seek fairness and mutual understanding",
                body_scores={"Venus": 3, "Mercury": 2, "Juno": 2},
                house_scores={7: 3, 3: 2},
                sign_scores={"Libra": 2, "Gemini": 1},
                madlib_fragment="turns tension into negotiation and accord",
            ),
            _option(
                "withdraw, reflect, then return transformed",
                body_scores={"Neptune": 3, "Pluto": 2, "Moon": 2},
                house_scores={12: 3, 8: 2},
                sign_scores={"Pisces": 2, "Scorpio": 1},
                madlib_fragment="vanishes into fog and returns with revelations",
            ),
        ),
    ),
    QuizQuestion(
        prompt="Your growth edge right now feels like:",
        options=(
            _option(
                "speaking up and being seen",
                body_scores={"Sun": 3, "Rahu": 2, "Mercury": 1},
                house_scores={1: 3, 3: 1},
                sign_scores={"Leo": 2, "Aries": 1},
                madlib_fragment="steps into the spotlight with shaking knees",
            ),
            _option(
                "stability, resources, grounded routines",
                body_scores={"Saturn": 3, "Ceres": 2, "Jupiter": 1},
                house_scores={2: 3, 6: 2},
                sign_scores={"Taurus": 2, "Virgo": 1},
                madlib_fragment="builds a temple out of daily rituals",
            ),
            _option(
                "surrendering old identity layers",
                body_scores={"Ketu": 3, "Pluto": 2, "Neptune": 1},
                house_scores={8: 2, 12: 3},
                sign_scores={"Scorpio": 2, "Pisces": 1},
                madlib_fragment="lets old skins fall off without ceremony",
            ),
        ),
    ),
    # Signs-focused questions (5)
    QuizQuestion(
        prompt="[Signs] Your social style is most like:",
        options=(
            _option("bold and direct", sign_scores={"Aries": 3, "Leo": 1}, madlib_fragment="speaks first and polishes later"),
            _option("witty and curious", sign_scores={"Gemini": 3, "Aquarius": 1}, madlib_fragment="collects ideas like shiny coins"),
            _option("steady and soothing", sign_scores={"Taurus": 3, "Cancer": 1}, madlib_fragment="grounds chaos with warm steadiness"),
        ),
    ),
    QuizQuestion(
        prompt="[Signs] What drives your ambition most?",
        options=(
            _option("winning and leading", sign_scores={"Aries": 2, "Capricorn": 2}, madlib_fragment="turns pressure into momentum"),
            _option("mastering a craft", sign_scores={"Virgo": 3, "Capricorn": 1}, madlib_fragment="sharpens skill until it sings"),
            _option("meaning and vision", sign_scores={"Sagittarius": 3, "Pisces": 1}, madlib_fragment="follows purpose over certainty"),
        ),
    ),
    QuizQuestion(
        prompt="[Signs] Your love language is closest to:",
        options=(
            _option("romantic and dramatic", sign_scores={"Leo": 3, "Libra": 1}, madlib_fragment="loves in technicolor"),
            _option("loyal and practical", sign_scores={"Taurus": 2, "Virgo": 2}, madlib_fragment="shows care with consistency"),
            _option("soul-deep and private", sign_scores={"Scorpio": 3, "Cancer": 1}, madlib_fragment="protects intimacy like treasure"),
        ),
    ),
    QuizQuestion(
        prompt="[Signs] In uncertainty you become:",
        options=(
            _option("inventive and experimental", sign_scores={"Aquarius": 3, "Gemini": 1}, madlib_fragment="treats uncertainty like a lab"),
            _option("faithful and optimistic", sign_scores={"Sagittarius": 3, "Leo": 1}, madlib_fragment="bets on possibility"),
            _option("intuitive and adaptive", sign_scores={"Pisces": 3, "Cancer": 1}, madlib_fragment="moves with tides not clocks"),
        ),
    ),
    QuizQuestion(
        prompt="[Signs] Your default creative process is:",
        options=(
            _option("draft, revise, perfect", sign_scores={"Virgo": 3, "Capricorn": 1}, madlib_fragment="chisels brilliance from rough stone"),
            _option("collaborate and remix", sign_scores={"Libra": 2, "Gemini": 2}, madlib_fragment="builds masterpieces in dialogue"),
            _option("obsess and transform", sign_scores={"Scorpio": 2, "Aquarius": 2}, madlib_fragment="reinvents from the ashes"),
        ),
    ),
    # Houses-focused questions (5)
    QuizQuestion(
        prompt="[Houses] Where is your attention most often pulled?",
        options=(
            _option("self-definition and body", house_scores={1: 3, 6: 1}, madlib_fragment="keeps returning to the mirror and mission"),
            _option("money and material security", house_scores={2: 4}, madlib_fragment="counts what can be built and banked"),
            _option("siblings, neighbors, daily info", house_scores={3: 4}, madlib_fragment="lives inside conversations and corridors"),
        ),
    ),
    QuizQuestion(
        prompt="[Houses] Which stage of life feels loudest right now?",
        options=(
            _option("home, roots, family history", house_scores={4: 4}, madlib_fragment="is renovating the inner home"),
            _option("romance, pleasure, creativity", house_scores={5: 4}, madlib_fragment="lets play become a compass"),
            _option("workflows, health, service", house_scores={6: 4}, madlib_fragment="organizes life into useful rituals"),
        ),
    ),
    QuizQuestion(
        prompt="[Houses] Relationship dynamics are mostly about:",
        options=(
            _option("partnership and contracts", house_scores={7: 4}, madlib_fragment="learns through mirrors and agreements"),
            _option("merging, debt, taboo, healing", house_scores={8: 4}, madlib_fragment="walks the underworld for alchemy"),
            _option("travel, belief, higher learning", house_scores={9: 4}, madlib_fragment="stretches meaning across horizons"),
        ),
    ),
    QuizQuestion(
        prompt="[Houses] Career/public life currently feels:",
        options=(
            _option("high-stakes and visible", house_scores={10: 4}, madlib_fragment="is climbing toward visible mastery"),
            _option("networked and future-facing", house_scores={11: 4}, madlib_fragment="builds power through community webs"),
            _option("quiet, spiritual, behind-the-scenes", house_scores={12: 4}, madlib_fragment="finds strength in retreat and dreams"),
        ),
    ),
    QuizQuestion(
        prompt="[Houses] If you had one year of focus, you'd prioritize:",
        options=(
            _option("a personal rebrand", house_scores={1: 2, 10: 2}, madlib_fragment="rewrites identity as a public chapter"),
            _option("building long-term assets", house_scores={2: 2, 8: 2}, madlib_fragment="turns value into shared legacy"),
            _option("healing and integration", house_scores={4: 2, 12: 2}, madlib_fragment="mends roots and rests the nervous system"),
        ),
    ),
)


class ChartPredictorQuizDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Chart Predictor Quiz")
        self.resize(760, 700)

        self._button_groups: list[QButtonGroup] = []
        self._question_buttons: list[list[QRadioButton]] = []

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        root_layout.addWidget(scroll_area, 1)

        scroll_content = QWidget(self)
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)

        intro = QLabel(
            "Answer the prompts and this quiz will estimate your dominant bodies, signs, and houses\n"
            "using Ephemeral Daddy's natal weighting constants and your answers."
        )
        intro.setWordWrap(True)
        content_layout.addWidget(intro)

        for index, question in enumerate(QUIZ_QUESTIONS, start=1):
            question_block = self._build_question_block(index, question)
            content_layout.addWidget(question_block)

        self._results = QPlainTextEdit()
        self._results.setReadOnly(True)
        self._results.setMinimumHeight(220)
        self._results.setPlaceholderText("Select one answer per question, then click Predict Chart.")
        content_layout.addWidget(self._results)

        run_button = QPushButton("Predict Chart")
        run_button.clicked.connect(self._run_quiz)
        content_layout.addWidget(run_button, 0, Qt.AlignRight)

        scroll_area.setWidget(scroll_content)

    def _build_question_block(self, index: int, question: QuizQuestion) -> QWidget:
        container = QWidget(self)
        question_layout = QVBoxLayout(container)
        question_layout.setContentsMargins(0, 0, 0, 0)
        question_layout.setSpacing(4)

        prompt = QLabel(f"{index}. {question.prompt}")
        prompt.setWordWrap(True)
        question_layout.addWidget(prompt)

        group = QButtonGroup(container)
        option_buttons: list[QRadioButton] = []
        for option in question.options:
            button = QRadioButton(option.label)
            question_layout.addWidget(button)
            group.addButton(button)
            option_buttons.append(button)

        if option_buttons:
            option_buttons[0].setChecked(True)

        self._button_groups.append(group)
        self._question_buttons.append(option_buttons)
        return container

    def _run_quiz(self) -> None:
        selections: list[QuizOption] = []
        for group_index, button_group in enumerate(self._button_groups):
            checked_button = button_group.checkedButton()
            if checked_button is None:
                QMessageBox.information(
                    self,
                    "Incomplete quiz",
                    f"Please answer question {group_index + 1} before running the prediction.",
                )
                return
            option_index = self._question_buttons[group_index].index(checked_button)
            selections.append(QUIZ_QUESTIONS[group_index].options[option_index])

        body_scores: dict[str, float] = {body: float(weight) for body, weight in NATAL_WEIGHT.items()}
        house_scores: dict[int, float] = {house: 0.0 for house in range(1, 13)}
        sign_scores: dict[str, float] = {sign: 0.0 for sign in SIGN_NAMES}

        for selection in selections:
            for body, score in selection.body_scores.items():
                body_scores[body] = body_scores.get(body, 0.0) + float(score)
            for house, score in selection.house_scores.items():
                house_scores[house] = house_scores.get(house, 0.0) + float(score)
            for sign, score in selection.sign_scores.items():
                sign_scores[sign] = sign_scores.get(sign, 0.0) + float(score)

        top_bodies = sorted(body_scores.items(), key=lambda item: item[1], reverse=True)[:5]
        top_houses = sorted(house_scores.items(), key=lambda item: item[1], reverse=True)[:5]
        top_signs = sorted(sign_scores.items(), key=lambda item: item[1], reverse=True)[:5]
        madlib = "Then your archetype " + ", ".join(selection.madlib_fragment for selection in selections[:4]) + "."

        lines = [
            "CHART PREDICTOR QUIZ RESULT",
            "",
            f"Questions answered: {len(selections)}",
            "",
            "Dominant bodies (weighted):",
        ]
        lines.extend(f"  • {body}: {score:.1f}" for body, score in top_bodies)
        lines.append("")
        lines.append("Dominant signs (quiz-derived):")
        lines.extend(f"  • {sign}: {score:.1f}" for sign, score in top_signs)
        lines.append("")
        lines.append("Likely active houses:")
        lines.extend(f"  • House {house}: {score:.1f}" for house, score in top_houses)
        lines.append("")
        lines.append("Narrative mode:")
        lines.append(f"  • {madlib}")
        lines.append("")
        lines.append("Note: This is a playful predictor and not an ephemeris-derived natal calculation.")

        self._results.setPlainText("\n".join(lines))


def create_chart_predictor_quiz_dialog(parent: QWidget | None = None) -> ChartPredictorQuizDialog:
    return ChartPredictorQuizDialog(parent)
