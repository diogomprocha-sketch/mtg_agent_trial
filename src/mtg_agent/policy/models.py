"""Typed state and action projections supplied by an engine adapter."""

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Optional


def _non_negative(name: str, value: float) -> None:
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and non-negative")


def _unit_interval(name: str, value: float) -> None:
    if not isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be finite and between 0 and 1")


class ActionType(str, Enum):
    CAST_SPELL = "cast_spell"
    ACTIVATE_ABILITY = "activate_ability"
    PLAY_LAND = "play_land"
    DECLARE_ATTACKERS = "declare_attackers"
    DECLARE_BLOCKERS = "declare_blockers"
    CHOOSE = "choose"
    PASS = "pass"


@dataclass(frozen=True)
class GameState:
    state_id: str
    controller_life: int
    opponent_life: int
    turn_number: int = 1

    def __post_init__(self) -> None:
        if not self.state_id:
            raise ValueError("state_id must not be empty")
        if self.turn_number < 1:
            raise ValueError("turn_number must be positive")


@dataclass(frozen=True)
class ManaProjection:
    mana_spent: float = 0.0
    value_generated: float = 0.0
    flexibility_preserved: float = 1.0
    explicit_opportunity_cost: float = 0.0

    def __post_init__(self) -> None:
        _non_negative("mana_spent", self.mana_spent)
        _non_negative("value_generated", self.value_generated)
        _unit_interval("flexibility_preserved", self.flexibility_preserved)
        _non_negative("explicit_opportunity_cost", self.explicit_opportunity_cost)


@dataclass(frozen=True)
class ThreatProjection:
    power_added: float = 0.0
    toughness_added: float = 0.0
    evasion: float = 0.0
    resilience: float = 0.0
    immediate_pressure: float = 0.0
    vulnerability: float = 0.0

    def __post_init__(self) -> None:
        for name in ("power_added", "toughness_added", "immediate_pressure", "vulnerability"):
            _non_negative(name, getattr(self, name))
        _unit_interval("evasion", self.evasion)
        _unit_interval("resilience", self.resilience)


@dataclass(frozen=True)
class RemovalProjection:
    target_value: float = 0.0
    removed_fraction: float = 0.0
    target_mana_value: float = 0.0
    action_mana_cost: float = 0.0
    permanence: float = 0.0
    own_collateral_value: float = 0.0

    def __post_init__(self) -> None:
        for name in ("target_value", "target_mana_value", "action_mana_cost", "own_collateral_value"):
            _non_negative(name, getattr(self, name))
        _unit_interval("removed_fraction", self.removed_fraction)
        _unit_interval("permanence", self.permanence)


@dataclass(frozen=True)
class CounterspellProjection:
    target_value: float = 0.0
    target_mana_value: float = 0.0
    action_mana_cost: float = 0.0
    flexibility: float = 0.0
    counterplay_risk: float = 0.0

    def __post_init__(self) -> None:
        for name in ("target_value", "target_mana_value", "action_mana_cost", "counterplay_risk"):
            _non_negative(name, getattr(self, name))
        _unit_interval("flexibility", self.flexibility)


@dataclass(frozen=True)
class CombatProjection:
    opponent_damage: float = 0.0
    favorable_trade_value: float = 0.0
    unfavorable_trade_value: float = 0.0
    exposed_value: float = 0.0
    controller_damage: float = 0.0

    def __post_init__(self) -> None:
        for name in (
            "opponent_damage",
            "favorable_trade_value",
            "unfavorable_trade_value",
            "exposed_value",
            "controller_damage",
        ):
            _non_negative(name, getattr(self, name))


@dataclass(frozen=True)
class PlaneswalkerProjection:
    ability_value: float = 0.0
    loyalty_delta: float = 0.0
    board_value: float = 0.0
    survival: float = 1.0
    exposed_value: float = 0.0

    def __post_init__(self) -> None:
        for name in ("ability_value", "board_value", "exposed_value"):
            _non_negative(name, getattr(self, name))
        if not isfinite(self.loyalty_delta):
            raise ValueError("loyalty_delta must be finite")
        _unit_interval("survival", self.survival)


@dataclass(frozen=True)
class CardAdvantageProjection:
    cards_gained: float = 0.0
    opponent_cards_lost: float = 0.0
    cards_spent: float = 0.0
    selection_value: float = 0.0

    def __post_init__(self) -> None:
        for name in ("cards_gained", "opponent_cards_lost", "cards_spent", "selection_value"):
            _non_negative(name, getattr(self, name))


@dataclass(frozen=True)
class GraveyardProjection:
    own_setup_value: float = 0.0
    own_recovered_value: float = 0.0
    opponent_value_removed: float = 0.0
    own_value_lost: float = 0.0

    def __post_init__(self) -> None:
        for name in (
            "own_setup_value",
            "own_recovered_value",
            "opponent_value_removed",
            "own_value_lost",
        ):
            _non_negative(name, getattr(self, name))


@dataclass(frozen=True)
class LethalProjection:
    opponent_life_after: Optional[int] = None
    controller_life_after: Optional[int] = None
    prevents_opponent_lethal: bool = False


@dataclass(frozen=True)
class ActionProjection:
    mana: ManaProjection = field(default_factory=ManaProjection)
    threat: ThreatProjection = field(default_factory=ThreatProjection)
    removal: RemovalProjection = field(default_factory=RemovalProjection)
    counterspell: CounterspellProjection = field(default_factory=CounterspellProjection)
    combat: CombatProjection = field(default_factory=CombatProjection)
    planeswalker: PlaneswalkerProjection = field(default_factory=PlaneswalkerProjection)
    card_advantage: CardAdvantageProjection = field(default_factory=CardAdvantageProjection)
    graveyard: GraveyardProjection = field(default_factory=GraveyardProjection)
    lethal: LethalProjection = field(default_factory=LethalProjection)


@dataclass(frozen=True)
class StructuredAction:
    action_id: str
    action_type: ActionType
    projection: ActionProjection = field(default_factory=ActionProjection)

    def __post_init__(self) -> None:
        if not self.action_id:
            raise ValueError("action_id must not be empty")
