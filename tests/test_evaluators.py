import unittest

from mtg_agent.policy.evaluators import (
    card_advantage,
    combat,
    counterspell,
    graveyard,
    lethal,
    mana,
    planeswalker,
    removal,
    threat,
)
from mtg_agent.policy.models import (
    ActionProjection,
    ActionType,
    CardAdvantageProjection,
    CombatProjection,
    CounterspellProjection,
    GameState,
    GraveyardProjection,
    LethalProjection,
    ManaProjection,
    PlaneswalkerProjection,
    RemovalProjection,
    StructuredAction,
    ThreatProjection,
)


STATE = GameState("state-1", controller_life=10, opponent_life=8)


def action(**projections):
    return StructuredAction("a", ActionType.CHOOSE, ActionProjection(**projections))


class EvaluatorTests(unittest.TestCase):
    def test_mana(self):
        result = mana.evaluate(
            STATE,
            action(
                mana=ManaProjection(
                    mana_spent=2,
                    value_generated=4,
                    flexibility_preserved=0.5,
                    explicit_opportunity_cost=1,
                )
            ),
        )
        self.assertEqual(result.components.mana_efficiency, 2)
        self.assertEqual(result.components.future_opportunity_cost, 1.25)

    def test_threat(self):
        result = threat.evaluate(
            STATE,
            action(
                threat=ThreatProjection(
                    power_added=3,
                    toughness_added=4,
                    evasion=1,
                    resilience=0.5,
                    immediate_pressure=2,
                    vulnerability=2,
                )
            ),
        )
        self.assertEqual(result.components.board_value, 7)
        self.assertEqual(result.components.immediate_value, 1)
        self.assertEqual(result.components.risk, 1)

    def test_removal(self):
        result = removal.evaluate(
            STATE,
            action(
                removal=RemovalProjection(
                    target_value=6,
                    removed_fraction=0.5,
                    target_mana_value=5,
                    action_mana_cost=2,
                    permanence=1,
                    own_collateral_value=1,
                )
            ),
        )
        self.assertEqual(result.components.immediate_value, 3)
        self.assertEqual(result.components.tempo, 3)
        self.assertEqual(result.components.interaction_value, 3)
        self.assertEqual(result.components.risk, 1)

    def test_counterspell(self):
        result = counterspell.evaluate(
            STATE,
            action(
                counterspell=CounterspellProjection(
                    target_value=5,
                    target_mana_value=4,
                    action_mana_cost=2,
                    flexibility=0.6,
                    counterplay_risk=0.5,
                )
            ),
        )
        self.assertEqual(result.components.immediate_value, 5)
        self.assertEqual(result.components.tempo, 2)
        self.assertEqual(result.components.interaction_value, 4)
        self.assertEqual(result.components.risk, 0.5)

    def test_combat(self):
        result = combat.evaluate(
            STATE,
            action(
                combat=CombatProjection(
                    opponent_damage=4,
                    favorable_trade_value=3,
                    unfavorable_trade_value=1,
                    exposed_value=2,
                    controller_damage=1,
                )
            ),
        )
        self.assertEqual(result.components.immediate_value, 4)
        self.assertEqual(result.components.board_value, 3)
        self.assertEqual(result.components.tempo, 1.5)
        self.assertEqual(result.components.risk, 4)

    def test_planeswalker(self):
        result = planeswalker.evaluate(
            STATE,
            action(
                planeswalker=PlaneswalkerProjection(
                    ability_value=2,
                    loyalty_delta=2,
                    board_value=4,
                    survival=0.5,
                    exposed_value=6,
                )
            ),
        )
        self.assertEqual(result.components.immediate_value, 2)
        self.assertEqual(result.components.board_value, 3)
        self.assertEqual(result.components.risk, 3)

    def test_card_advantage(self):
        result = card_advantage.evaluate(
            STATE,
            action(
                card_advantage=CardAdvantageProjection(
                    cards_gained=2,
                    opponent_cards_lost=1,
                    cards_spent=1,
                    selection_value=2,
                )
            ),
        )
        self.assertEqual(result.components.card_advantage, 2.5)

    def test_graveyard(self):
        result = graveyard.evaluate(
            STATE,
            action(
                graveyard=GraveyardProjection(
                    own_setup_value=2,
                    own_recovered_value=3,
                    opponent_value_removed=4,
                    own_value_lost=1,
                )
            ),
        )
        self.assertEqual(result.components.board_value, 4)
        self.assertEqual(result.components.interaction_value, 4)
        self.assertEqual(result.components.future_opportunity_cost, 1)

    def test_lethal(self):
        winning = lethal.evaluate(
            STATE,
            action(
                lethal=LethalProjection(
                    opponent_life_after=0,
                    controller_life_after=1,
                    prevents_opponent_lethal=True,
                )
            ),
        )
        losing = lethal.evaluate(
            STATE,
            action(lethal=LethalProjection(controller_life_after=0)),
        )
        self.assertEqual(winning.components.immediate_value, 125)
        self.assertEqual(losing.components.risk, 100)


if __name__ == "__main__":
    unittest.main()
