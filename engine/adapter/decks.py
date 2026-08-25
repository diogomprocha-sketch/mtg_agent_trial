"""Strict parser for quantity-prefixed decklist files."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True)
class DeckEntry:
    quantity: int
    card_name: str


@dataclass(frozen=True)
class DeckList:
    entries: tuple[DeckEntry, ...]
    source_hash: str

    @property
    def card_count(self) -> int:
        return sum(entry.quantity for entry in self.entries)

    @property
    def card_names(self) -> tuple[str, ...]:
        return tuple(entry.card_name for entry in self.entries)

    def unknown_cards(self, supported_cards: set[str]) -> tuple[str, ...]:
        return tuple(
            entry.card_name
            for entry in self.entries
            if entry.card_name not in supported_cards
        )

    def to_forge_dck(self, name: str, sideboard: "DeckList") -> str:
        if not name.strip():
            raise ValueError("Forge deck name must not be empty")
        lines = [
            "[metadata]",
            f"Name={name}",
            "Deck Type=constructed",
            "",
            "[Main]",
        ]
        lines.extend(
            f"{entry.quantity} {entry.card_name}" for entry in self.entries
        )
        lines.extend(("", "[Sideboard]"))
        lines.extend(
            f"{entry.quantity} {entry.card_name}" for entry in sideboard.entries
        )
        return "\n".join(lines) + "\n"


def parse_deck(path: Path) -> DeckList:
    raw = path.read_bytes()
    entries = []
    seen = set()
    for line_number, raw_line in enumerate(
        raw.decode("utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line:
            continue
        quantity_text, separator, card_name = line.partition(" ")
        if not separator or not quantity_text.isdigit() or int(quantity_text) < 1:
            raise ValueError(f"{path}:{line_number}: expected '<quantity> <card name>'")
        if not card_name.strip():
            raise ValueError(f"{path}:{line_number}: card name must not be empty")
        if card_name in seen:
            raise ValueError(f"{path}:{line_number}: duplicate card entry {card_name!r}")
        seen.add(card_name)
        entries.append(DeckEntry(int(quantity_text), card_name))
    if not entries:
        raise ValueError(f"{path}: decklist must not be empty")
    return DeckList(entries=tuple(entries), source_hash=sha256(raw).hexdigest())
