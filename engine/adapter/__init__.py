"""Adapters between external engines and agent-owned data."""

from .decks import DeckEntry, DeckList, parse_deck

__all__ = ["DeckEntry", "DeckList", "parse_deck"]
