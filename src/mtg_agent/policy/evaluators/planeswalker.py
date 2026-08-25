"""Planeswalker ability, loyalty, and survival heuristic."""

from ..models import GameState, StructuredAction
from ..scoring import ComponentScores, Evaluation


def evaluate(state: GameState, action: StructuredAction) -> Evaluation:
    del state
    planeswalker = action.projection.planeswalker
    board = (
        0.5 * planeswalker.loyalty_delta
        + planeswalker.board_value * planeswalker.survival
    )
    risk = planeswalker.exposed_value * (1.0 - planeswalker.survival)
    return Evaluation(
        "planeswalker",
        ComponentScores(
            immediate_value=planeswalker.ability_value,
            board_value=board,
            risk=risk,
        ),
        {
            "loyalty_delta": planeswalker.loyalty_delta,
            "survival": planeswalker.survival,
            "exposed_value": planeswalker.exposed_value,
        },
    )
