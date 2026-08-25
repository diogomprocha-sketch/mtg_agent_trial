import json
import math
import unittest

from mtg_agent.policy import (
    ActionProjection,
    ActionType,
    BaselinePolicy,
    GameState,
    ManaProjection,
    PolicyWeights,
    StructuredAction,
    ThreatProjection,
)
from mtg_agent.policy.scoring import ComponentScores


STATE = GameState("state-1", controller_life=20, opponent_life=20)


class ConfigurationTests(unittest.TestCase):
    def test_defaults_are_valid(self):
        self.assertGreater(PolicyWeights().immediate_value, 0)

    def test_mapping_override(self):
        weights = PolicyWeights.from_mapping({"risk": 2.5})
        self.assertEqual(weights.risk, 2.5)
        self.assertEqual(weights.board_value, 1)

    def test_rejects_unknown_non_finite_negative_and_boolean_weights(self):
        with self.assertRaises(ValueError):
            PolicyWeights.from_mapping({"unknown": 1})
        with self.assertRaises(ValueError):
            PolicyWeights(risk=-1)
        with self.assertRaises(ValueError):
            PolicyWeights(risk=math.inf)
        with self.assertRaises(TypeError):
            PolicyWeights(risk=True)

    def test_projection_validation(self):
        with self.assertRaises(ValueError):
            ManaProjection(mana_spent=-1)
        with self.assertRaises(ValueError):
            ThreatProjection(evasion=1.1)


class AggregationTests(unittest.TestCase):
    def test_weighted_formula_subtracts_cost_components(self):
        components = ComponentScores(
            immediate_value=1,
            board_value=2,
            card_advantage=3,
            tempo=4,
            mana_efficiency=5,
            interaction_value=6,
            risk=7,
            future_opportunity_cost=8,
        )
        weights = PolicyWeights(
            immediate_value=1,
            board_value=2,
            card_advantage=3,
            tempo=4,
            mana_efficiency=5,
            interaction_value=6,
            risk=7,
            future_opportunity_cost=8,
        )
        self.assertEqual(components.weighted_total(weights), -22)

    def test_policy_weighted_breakdown_sums_to_total(self):
        policy = BaselinePolicy(PolicyWeights(mana_efficiency=2))
        scored = policy.score_action(
            STATE,
            StructuredAction(
                "spell",
                ActionType.CAST_SPELL,
                ActionProjection(mana=ManaProjection(mana_spent=2, value_generated=5)),
            ),
        )
        self.assertEqual(scored.weighted_components["mana_efficiency"], 6)
        self.assertAlmostEqual(scored.total, sum(scored.weighted_components.values()))
        self.assertEqual(len(scored.evaluations), 9)


class ChoiceTests(unittest.TestCase):
    def test_scores_every_legal_action_and_selects_best(self):
        actions = (
            StructuredAction("pass", ActionType.PASS),
            StructuredAction(
                "threat",
                ActionType.CAST_SPELL,
                ActionProjection(threat=ThreatProjection(power_added=2)),
            ),
            StructuredAction(
                "bigger-threat",
                ActionType.CAST_SPELL,
                ActionProjection(threat=ThreatProjection(power_added=4)),
            ),
        )
        selected, record = BaselinePolicy().choose(STATE, actions)
        self.assertEqual(selected.action_id, "bigger-threat")
        self.assertEqual(len(record.candidates), len(actions))
        self.assertEqual(
            {candidate.action_id for candidate in record.candidates},
            {action.action_id for action in actions},
        )

    def test_tie_break_is_stable_and_independent_of_input_order(self):
        alpha = StructuredAction("alpha", ActionType.PASS)
        zeta = StructuredAction("zeta", ActionType.CHOOSE)
        first, first_record = BaselinePolicy().choose(STATE, (zeta, alpha))
        second, _ = BaselinePolicy().choose(STATE, (alpha, zeta))
        self.assertEqual(first.action_id, "alpha")
        self.assertEqual(second.action_id, "alpha")
        self.assertIn("lexicographically", first_record.tie_break_rule)

    def test_pass_is_legal_and_safe(self):
        passed, record = BaselinePolicy().choose(
            STATE, (StructuredAction("pass", ActionType.PASS),)
        )
        self.assertEqual(passed.action_type, ActionType.PASS)
        self.assertEqual(record.candidates[0].total, 0)

    def test_rejects_empty_and_duplicate_legal_actions(self):
        policy = BaselinePolicy()
        with self.assertRaises(ValueError):
            policy.choose(STATE, ())
        duplicate = StructuredAction("same", ActionType.PASS)
        with self.assertRaises(ValueError):
            policy.choose(STATE, (duplicate, duplicate))

    def test_record_is_structured_deterministic_json(self):
        _, record = BaselinePolicy().choose(
            STATE, (StructuredAction("pass", ActionType.PASS),)
        )
        payload = json.loads(record.to_json())
        self.assertEqual(payload["selected_action_id"], "pass")
        self.assertEqual(payload["state_id"], "state-1")
        self.assertEqual(payload["candidates"][0]["action_type"], "pass")
        self.assertEqual(len(payload["candidates"][0]["evaluations"]), 9)
        self.assertEqual(record.to_json(), record.to_json())


if __name__ == "__main__":
    unittest.main()
