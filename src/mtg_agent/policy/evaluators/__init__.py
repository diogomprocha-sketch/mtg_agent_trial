"""Independent deterministic evaluators."""

from . import (
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

ALL_EVALUATORS = (
    mana.evaluate,
    threat.evaluate,
    removal.evaluate,
    counterspell.evaluate,
    combat.evaluate,
    planeswalker.evaluate,
    card_advantage.evaluate,
    graveyard.evaluate,
    lethal.evaluate,
)

__all__ = ["ALL_EVALUATORS"]
