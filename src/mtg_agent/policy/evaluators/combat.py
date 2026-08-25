"""Combat damage, trade, and exposure heuristic."""

from ..models import GameState, StructuredAction
from ..scoring import ComponentScores, Evaluation


def evaluate(state: GameState, action: StructuredAction) -> Evaluation:
    del state
    combat = action.projection.combat
    return Evaluation(
        "combat",
        ComponentScores(
            immediate_value=combat.opponent_damage,
            board_value=combat.favorable_trade_value,
            tempo=0.5 * combat.favorable_trade_value,
            risk=(
                combat.unfavorable_trade_value
                + combat.exposed_value
                + combat.controller_damage
            ),
        ),
        {
            "opponent_damage": combat.opponent_damage,
            "favorable_trade_value": combat.favorable_trade_value,
            "unfavorable_trade_value": combat.unfavorable_trade_value,
            "exposed_value": combat.exposed_value,
            "controller_damage": combat.controller_damage,
        },
    )
