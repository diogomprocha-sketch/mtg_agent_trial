"""Counterspell impact and exchange heuristic."""

from ..models import GameState, StructuredAction
from ..scoring import ComponentScores, Evaluation


def evaluate(state: GameState, action: StructuredAction) -> Evaluation:
    del state
    counter = action.projection.counterspell
    return Evaluation(
        "counterspell",
        ComponentScores(
            immediate_value=counter.target_value,
            tempo=max(0.0, counter.target_mana_value - counter.action_mana_cost),
            interaction_value=counter.target_value * (0.5 + 0.5 * counter.flexibility),
            risk=counter.counterplay_risk,
        ),
        {
            "target_value": counter.target_value,
            "mana_exchange": counter.target_mana_value - counter.action_mana_cost,
            "flexibility": counter.flexibility,
        },
    )
