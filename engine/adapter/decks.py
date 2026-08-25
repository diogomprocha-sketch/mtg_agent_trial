"""Strict parser for quantity-prefixed decklist files."""

from collections import OrderedDict
from dataclasses import dataclass
from hashlib import sha256
import json
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


@dataclass(frozen=True)
class SideboardPlan:
    opponent_archetype: str
    cards_in: tuple[DeckEntry, ...]
    cards_out: tuple[DeckEntry, ...]
    source_hash: str

    @property
    def card_count(self) -> int:
        return sum(entry.quantity for entry in self.cards_in)


def parse_sideboard_plan(path: Path) -> SideboardPlan:
    raw = path.read_bytes()
    payload = json.loads(raw)
    expected = {"opponent_archetype", "in", "out"}
    if set(payload) != expected:
        raise ValueError(f"{path}: expected exactly {sorted(expected)}")

    def parse_entries(key: str) -> tuple[DeckEntry, ...]:
        value = payload[key]
        if not isinstance(value, list) or not value:
            raise ValueError(f"{path}: {key!r} must be a non-empty list")
        entries = []
        seen = set()
        for item in value:
            if (
                not isinstance(item, dict)
                or set(item) != {"quantity", "card_name"}
                or isinstance(item["quantity"], bool)
                or not isinstance(item["quantity"], int)
                or item["quantity"] < 1
                or not isinstance(item["card_name"], str)
                or not item["card_name"].strip()
            ):
                raise ValueError(f"{path}: invalid {key!r} entry")
            if item["card_name"] in seen:
                raise ValueError(f"{path}: duplicate {key!r} card {item['card_name']!r}")
            seen.add(item["card_name"])
            entries.append(DeckEntry(item["quantity"], item["card_name"]))
        return tuple(entries)

    opponent = payload["opponent_archetype"]
    if not isinstance(opponent, str) or not opponent.strip():
        raise ValueError(f"{path}: opponent_archetype must not be empty")
    plan = SideboardPlan(
        opponent_archetype=opponent,
        cards_in=parse_entries("in"),
        cards_out=parse_entries("out"),
        source_hash=sha256(raw).hexdigest(),
    )
    if plan.card_count != sum(entry.quantity for entry in plan.cards_out):
        raise ValueError(f"{path}: cards in and cards out must have equal counts")
    return plan


def apply_sideboard_plan(
    main: DeckList,
    sideboard: DeckList,
    plan: SideboardPlan,
) -> tuple[DeckList, DeckList]:
    main_counts = OrderedDict((entry.card_name, entry.quantity) for entry in main.entries)
    sideboard_counts = OrderedDict(
        (entry.card_name, entry.quantity) for entry in sideboard.entries
    )

    for entry in plan.cards_out:
        if main_counts.get(entry.card_name, 0) < entry.quantity:
            raise ValueError(f"main deck lacks {entry.quantity} {entry.card_name}")
        main_counts[entry.card_name] -= entry.quantity
        sideboard_counts[entry.card_name] = (
            sideboard_counts.get(entry.card_name, 0) + entry.quantity
        )
    for entry in plan.cards_in:
        if sideboard_counts.get(entry.card_name, 0) < entry.quantity:
            raise ValueError(f"sideboard lacks {entry.quantity} {entry.card_name}")
        sideboard_counts[entry.card_name] -= entry.quantity
        main_counts[entry.card_name] = main_counts.get(entry.card_name, 0) + entry.quantity

    transformed_main = _deck_from_counts(main_counts)
    transformed_sideboard = _deck_from_counts(sideboard_counts)
    if transformed_main.card_count != main.card_count:
        raise ValueError("sideboard plan changed the main-deck size")
    if transformed_sideboard.card_count != sideboard.card_count:
        raise ValueError("sideboard plan changed the sideboard size")
    return transformed_main, transformed_sideboard


def _deck_from_counts(counts: "OrderedDict[str, int]") -> DeckList:
    entries = tuple(
        DeckEntry(quantity, card_name)
        for card_name, quantity in counts.items()
        if quantity > 0
    )
    canonical = "".join(
        f"{entry.quantity} {entry.card_name}\n" for entry in entries
    ).encode("utf-8")
    return DeckList(entries=entries, source_hash=sha256(canonical).hexdigest())


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
