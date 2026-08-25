"""Deterministic weighted policy over legal structured actions."""

from dataclasses import fields
from typing import Iterable, Optional

from .config import PolicyWeights
from .evaluators import ALL_EVALUATORS
from .models import GameState, StructuredAction
from .scoring import ActionScore, ComponentScores, ScoringRecord

POLICY_VERSION = "deterministic-baseline-v1"
TIE_BREAK_RULE = "highest_total_then_lexicographically_smallest_action_id"


class BaselinePolicy:
    def __init__(self, weights: Optional[PolicyWeights] = None) -> None:
        self.weights = weights or PolicyWeights()

    def score_action(self, state: GameState, action: StructuredAction) -> ActionScore:
        evaluations = tuple(evaluator(state, action) for evaluator in ALL_EVALUATORS)
        raw = sum(
            (evaluation.components for evaluation in evaluations),
            start=ComponentScores(),
        )
        weighted = {}
        for field in fields(raw):
            name = field.name
            sign = -1.0 if name in {"risk", "future_opportunity_cost"} else 1.0
            weighted[name] = sign * getattr(raw, name) * getattr(self.weights, name)
        return ActionScore(
            action_id=action.action_id,
            action_type=action.action_type.value,
            total=sum(weighted.values()),
            raw_components=raw,
            weighted_components=weighted,
            evaluations=evaluations,
        )

    def choose(
        self,
        state: GameState,
        legal_actions: Iterable[StructuredAction],
    ) -> tuple[StructuredAction, ScoringRecord]:
        actions = tuple(legal_actions)
        if not actions:
            raise ValueError("at least one legal action, including pass when legal, is required")
        action_by_id = {action.action_id: action for action in actions}
        if len(action_by_id) != len(actions):
            raise ValueError("legal action IDs must be unique")

        candidates = tuple(self.score_action(state, action) for action in actions)
        selected = min(candidates, key=lambda score: (-score.total, score.action_id))
        record = ScoringRecord(
            policy_version=POLICY_VERSION,
            state_id=state.state_id,
            candidates=candidates,
            selected_action_id=selected.action_id,
            tie_break_rule=TIE_BREAK_RULE,
        )
        return action_by_id[selected.action_id], record
