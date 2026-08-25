"""Terminal game-state and lethal-prevention heuristic."""

from ..models import GameState, StructuredAction
from ..scoring import ComponentScores, Evaluation

LETHAL_VALUE = 100.0
LETHAL_PREVENTION_VALUE = 25.0


def evaluate(state: GameState, action: StructuredAction) -> Evaluation:
    lethal = action.projection.lethal
    opponent_after = (
        state.opponent_life
        if lethal.opponent_life_after is None
        else lethal.opponent_life_after
    )
    controller_after = (
        state.controller_life
        if lethal.controller_life_after is None
        else lethal.controller_life_after
    )
    wins = opponent_after <= 0 and controller_after > 0
    loses = controller_after <= 0
    return Evaluation(
        "lethal",
        ComponentScores(
            immediate_value=(
                (LETHAL_VALUE if wins else 0.0)
                + (LETHAL_PREVENTION_VALUE if lethal.prevents_opponent_lethal else 0.0)
            ),
            risk=LETHAL_VALUE if loses else 0.0,
        ),
        {
            "opponent_life_after": float(opponent_after),
            "controller_life_after": float(controller_after),
            "wins_game": wins,
            "loses_game": loses,
            "prevents_opponent_lethal": lethal.prevents_opponent_lethal,
        },
    )
