"""Graveyard setup, recovery, and disruption heuristic."""

from ..models import GameState, StructuredAction
from ..scoring import ComponentScores, Evaluation


def evaluate(state: GameState, action: StructuredAction) -> Evaluation:
    del state
    graveyard = action.projection.graveyard
    return Evaluation(
        "graveyard",
        ComponentScores(
            board_value=0.5 * graveyard.own_setup_value + graveyard.own_recovered_value,
            interaction_value=graveyard.opponent_value_removed,
            future_opportunity_cost=graveyard.own_value_lost,
        ),
        {
            "own_setup_value": graveyard.own_setup_value,
            "own_recovered_value": graveyard.own_recovered_value,
            "opponent_value_removed": graveyard.opponent_value_removed,
            "own_value_lost": graveyard.own_value_lost,
        },
    )
