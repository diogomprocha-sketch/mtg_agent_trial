"""Configuration for weighted deterministic action scoring."""

from dataclasses import dataclass, fields
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class PolicyWeights:
    immediate_value: float = 1.0
    board_value: float = 1.0
    card_advantage: float = 1.0
    tempo: float = 0.75
    mana_efficiency: float = 0.5
    interaction_value: float = 0.75
    risk: float = 1.0
    future_opportunity_cost: float = 0.5

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{field.name} must be a number")
            if not isfinite(value) or value < 0:
                raise ValueError(f"{field.name} must be finite and non-negative")

    @classmethod
    def from_mapping(cls, values: Mapping[str, float]) -> "PolicyWeights":
        known = {field.name for field in fields(cls)}
        unknown = set(values) - known
        if unknown:
            raise ValueError(f"unknown policy weights: {sorted(unknown)}")
        return cls(**values)
