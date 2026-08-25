"""Permanent-threat quality heuristic."""

from ..models import GameState, StructuredAction
from ..scoring import ComponentScores, Evaluation


def evaluate(state: GameState, action: StructuredAction) -> Evaluation:
    del state
    threat = action.projection.threat
    board = (
        threat.power_added
        + 0.5 * threat.toughness_added
        + 1.5 * threat.evasion
        + threat.resilience
    )
    return Evaluation(
        "threat",
        ComponentScores(
            immediate_value=0.5 * threat.immediate_pressure,
            board_value=board,
            risk=0.5 * threat.vulnerability,
        ),
        {
            "power_added": threat.power_added,
            "toughness_added": threat.toughness_added,
            "evasion": threat.evasion,
            "resilience": threat.resilience,
        },
    )
