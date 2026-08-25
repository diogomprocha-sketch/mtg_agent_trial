"""Removal value, permanence, and tempo heuristic."""

from ..models import GameState, StructuredAction
from ..scoring import ComponentScores, Evaluation


def evaluate(state: GameState, action: StructuredAction) -> Evaluation:
    del state
    removal = action.projection.removal
    removed_value = removal.target_value * removal.removed_fraction
    return Evaluation(
        "removal",
        ComponentScores(
            immediate_value=removed_value,
            tempo=max(0.0, removal.target_mana_value - removal.action_mana_cost),
            interaction_value=removed_value * (0.5 + 0.5 * removal.permanence),
            risk=removal.own_collateral_value,
        ),
        {
            "removed_value": removed_value,
            "permanence": removal.permanence,
            "own_collateral_value": removal.own_collateral_value,
        },
    )
