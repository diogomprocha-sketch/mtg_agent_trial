"""Scoring primitives shared by evaluators and the policy."""

from dataclasses import asdict, dataclass
import json
from typing import Any, Mapping, Union

from .config import PolicyWeights


@dataclass(frozen=True)
class ComponentScores:
    immediate_value: float = 0.0
    board_value: float = 0.0
    card_advantage: float = 0.0
    tempo: float = 0.0
    mana_efficiency: float = 0.0
    interaction_value: float = 0.0
    risk: float = 0.0
    future_opportunity_cost: float = 0.0

    def __add__(self, other: "ComponentScores") -> "ComponentScores":
        return ComponentScores(
            **{
                name: getattr(self, name) + getattr(other, name)
                for name in self.__dataclass_fields__
            }
        )

    def weighted_total(self, weights: PolicyWeights) -> float:
        benefits = (
            self.immediate_value * weights.immediate_value
            + self.board_value * weights.board_value
            + self.card_advantage * weights.card_advantage
            + self.tempo * weights.tempo
            + self.mana_efficiency * weights.mana_efficiency
            + self.interaction_value * weights.interaction_value
        )
        costs = (
            self.risk * weights.risk
            + self.future_opportunity_cost * weights.future_opportunity_cost
        )
        return benefits - costs


@dataclass(frozen=True)
class Evaluation:
    evaluator: str
    components: ComponentScores
    metrics: Mapping[str, Union[float, bool]]


@dataclass(frozen=True)
class ActionScore:
    action_id: str
    action_type: str
    total: float
    raw_components: ComponentScores
    weighted_components: Mapping[str, float]
    evaluations: tuple[Evaluation, ...]


@dataclass(frozen=True)
class ScoringRecord:
    policy_version: str
    state_id: str
    candidates: tuple[ActionScore, ...]
    selected_action_id: str
    tie_break_rule: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
