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
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.core.interpretations import NATAL_WEIGHT


@dataclass(frozen=True)
class QuizOption:
    label: str
    body_scores: dict[str, float]
    house_scores: dict[int, float]
    madlib_fragment: str


@dataclass(frozen=True)
class QuizQuestion:
    prompt: str
    options: tuple[QuizOption, ...]


QUIZ_QUESTIONS: tuple[QuizQuestion, ...] = (
    QuizQuestion(
        prompt="When plans change last-minute, your reflex is:",
        options=(
            QuizOption(
                label="take charge and improvise",
                body_scores={"Mars": 4, "Sun": 2, "AS": 2},
                house_scores={1: 3, 10: 2},
                madlib_fragment="kicks the door open and writes a new script",
            ),
            QuizOption(
                label="talk it out and gather data",
                body_scores={"Mercury": 4, "Moon": 1, "Jupiter": 1},
                house_scores={3: 3, 6: 2},
                madlib_fragment="builds a map made of conversations and clues",
            ),
            QuizOption(
                label="feel the vibe before moving",
                body_scores={"Moon": 4, "Venus": 2, "Neptune": 1},
                house_scores={4: 3, 12: 2},
                madlib_fragment="reads the room like weather before taking a step",
            ),
        ),
    ),
    QuizQuestion(
        prompt="What kind of recognition feels most satisfying?",
        options=(
            QuizOption(
                label="public impact and achievement",
                body_scores={"Sun": 4, "Saturn": 2, "MC": 2},
                house_scores={10: 4, 1: 1},
                madlib_fragment="wants the mountain peak and the skyline view",
            ),
            QuizOption(
                label="trusted one-on-one bonds",
                body_scores={"Venus": 4, "Moon": 2, "DS": 2},
                house_scores={7: 4, 4: 1},
                madlib_fragment="finds power in mirrors, promises, and partnerships",
            ),
            QuizOption(
                label="freedom to reinvent everything",
                body_scores={"Uranus": 4, "Pluto": 2, "Rahu": 1},
                house_scores={11: 3, 8: 2},
                madlib_fragment="rewires the game and calls it growth",
            ),
        ),
    ),
    QuizQuestion(
        prompt="Your ideal weekend usually includes:",
        options=(
            QuizOption(
                label="adventure, action, movement",
                body_scores={"Mars": 3, "Jupiter": 3, "Sun": 1},
                house_scores={9: 3, 5: 2},
                madlib_fragment="chases horizons until the map runs out",
            ),
            QuizOption(
                label="beauty, art, delicious comfort",
                body_scores={"Venus": 4, "Moon": 2, "Ceres": 1},
                house_scores={2: 3, 5: 2},
                madlib_fragment="collects textures, tastes, and tiny luxuries",
            ),
            QuizOption(
                label="deep dive into mysteries",
                body_scores={"Pluto": 4, "Ketu": 2, "Saturn": 1},
                house_scores={8: 4, 12: 1},
                madlib_fragment="goes spelunking in secrets and shadow archives",
            ),
        ),
    ),
    QuizQuestion(
        prompt="In conflicts, you tend to:",
        options=(
            QuizOption(
                label="set boundaries and structure quickly",
                body_scores={"Saturn": 4, "Mars": 2, "MC": 1},
                house_scores={6: 2, 10: 2, 1: 1},
                madlib_fragment="draws the line in ink and means it",
            ),
            QuizOption(
                label="seek fairness and mutual understanding",
                body_scores={"Venus": 3, "Mercury": 2, "Juno": 2},
                house_scores={7: 3, 3: 2},
                madlib_fragment="turns tension into negotiation and accord",
            ),
            QuizOption(
                label="withdraw, reflect, then return transformed",
                body_scores={"Neptune": 3, "Pluto": 2, "Moon": 2},
                house_scores={12: 3, 8: 2},
                madlib_fragment="vanishes into the fog and returns with revelations",
            ),
        ),
    ),
    QuizQuestion(
        prompt="Your growth edge right now feels like:",
        options=(
            QuizOption(
                label="speaking up and being seen",
                body_scores={"Sun": 3, "Rahu": 2, "Mercury": 1},
                house_scores={1: 3, 3: 1},
                madlib_fragment="steps into the spotlight even with shaking knees",
            ),
            QuizOption(
                label="stability, resources, grounded routines",
                body_scores={"Saturn": 3, "Ceres": 2, "Jupiter": 1},
                house_scores={2: 3, 6: 2},
                madlib_fragment="builds a sturdy temple from daily rituals",
            ),
            QuizOption(
                label="surrendering old identity layers",
                body_scores={"Ketu": 3, "Pluto": 2, "Neptune": 1},
                house_scores={8: 2, 12: 3},
                madlib_fragment="lets old skins fall off without ceremony",
            ),
        ),
    ),
)


class ChartPredictorQuizDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Chart Predictor Quiz")
        self.resize(700, 620)

        self._button_groups: list[QButtonGroup] = []
        self._question_buttons: list[list[QRadioButton]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        intro = QLabel(
            "Answer the prompts and this quiz will estimate your dominant bodies and houses\n"
            "using Ephemeral Daddy's natal weighting constants and your answers."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        for index, question in enumerate(QUIZ_QUESTIONS, start=1):
            question_block = self._build_question_block(index, question)
            layout.addWidget(question_block)

        self._results = QPlainTextEdit()
        self._results.setReadOnly(True)
        self._results.setPlaceholderText("Select one answer per question, then click Predict Chart.")
        layout.addWidget(self._results, 1)

        run_button = QPushButton("Predict Chart")
        run_button.clicked.connect(self._run_quiz)
        layout.addWidget(run_button, 0, Qt.AlignRight)

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
            checked_id = button_group.checkedId()
            if checked_id < 0:
                QMessageBox.information(
                    self,
                    "Incomplete quiz",
                    f"Please answer question {group_index + 1} before running the prediction.",
                )
                return
            checked_button = button_group.checkedButton()
            option_index = self._question_buttons[group_index].index(checked_button)
            selections.append(QUIZ_QUESTIONS[group_index].options[option_index])

        body_scores: dict[str, float] = {body: float(weight) for body, weight in NATAL_WEIGHT.items()}
        house_scores: dict[int, float] = {house: 0.0 for house in range(1, 13)}

        for selection in selections:
            for body, score in selection.body_scores.items():
                body_scores[body] = body_scores.get(body, 0.0) + float(score)
            for house, score in selection.house_scores.items():
                house_scores[house] = house_scores.get(house, 0.0) + float(score)

        top_bodies = sorted(body_scores.items(), key=lambda item: item[1], reverse=True)[:5]
        top_houses = sorted(house_scores.items(), key=lambda item: item[1], reverse=True)[:3]
        madlib = "Then your archetype " + ", ".join(selection.madlib_fragment for selection in selections[:3]) + "."

        lines = [
            "CHART PREDICTOR QUIZ RESULT",
            "",
            "Dominant bodies (weighted):",
        ]
        lines.extend(f"  • {body}: {score:.1f}" for body, score in top_bodies)
        lines.append("")
        lines.append("Likely active houses:")
        lines.extend(f"  • House {house}: {score:.1f}" for house, score in top_houses)
        lines.append("")
        lines.append("Narrative mode:")
        lines.append(f"  • {madlib}")
        lines.append("")
        lines.append(
            "Note: This is a playful predictor and not an ephemeris-derived natal calculation."
        )

        self._results.setPlainText("\n".join(lines))


def create_chart_predictor_quiz_dialog(parent: QWidget | None = None) -> ChartPredictorQuizDialog:
    return ChartPredictorQuizDialog(parent)
