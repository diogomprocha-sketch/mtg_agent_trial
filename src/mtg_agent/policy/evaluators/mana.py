"""Mana efficiency and resource-preservation heuristic."""

from ..models import GameState, StructuredAction
from ..scoring import ComponentScores, Evaluation


def evaluate(state: GameState, action: StructuredAction) -> Evaluation:
    del state
    mana = action.projection.mana
    efficiency = mana.value_generated - mana.mana_spent
    opportunity_cost = mana.explicit_opportunity_cost + (
        mana.mana_spent * (1.0 - mana.flexibility_preserved) * 0.25
    )
    return Evaluation(
        "mana",
        ComponentScores(
            mana_efficiency=efficiency,
            future_opportunity_cost=opportunity_cost,
        ),
        {
            "mana_spent": mana.mana_spent,
            "value_generated": mana.value_generated,
            "flexibility_preserved": mana.flexibility_preserved,
        },
    )
