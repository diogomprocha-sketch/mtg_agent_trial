"""Card quantity and selection heuristic."""

from ..models import GameState, StructuredAction
from ..scoring import ComponentScores, Evaluation


def evaluate(state: GameState, action: StructuredAction) -> Evaluation:
    del state
    cards = action.projection.card_advantage
    net_cards = cards.cards_gained + cards.opponent_cards_lost - cards.cards_spent
    return Evaluation(
        "card_advantage",
        ComponentScores(card_advantage=net_cards + 0.25 * cards.selection_value),
        {
            "net_cards": net_cards,
            "selection_value": cards.selection_value,
        },
    )
