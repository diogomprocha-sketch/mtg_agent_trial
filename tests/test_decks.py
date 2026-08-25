from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from engine.adapter.decks import parse_deck


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "decks" / "dimir_midrange" / "main.txt"
SIDEBOARD = ROOT / "decks" / "dimir_midrange" / "sideboard.txt"
IZZET_MAIN = ROOT / "decks" / "opponents" / "izzet_spellementals.txt"
IZZET_SIDEBOARD = (
    ROOT / "decks" / "opponents" / "izzet_spellementals_sideboard.txt"
)

EXPECTED_MAIN = (
    (4, "Island"),
    (4, "Swamp"),
    (1, "Spell Snare"),
    (4, "Watery Grave"),
    (1, "Spell Pierce"),
    (4, "Spyglass Siren"),
    (2, "Tishana's Tidebinder"),
    (2, "Bitter Triumph"),
    (2, "Restless Reef"),
    (2, "Shoot the Sheriff"),
    (3, "Enduring Curiosity"),
    (4, "Floodpits Drowner"),
    (4, "Kaito, Bane of Nightmares"),
    (4, "Gloomlake Verge"),
    (2, "Soulstone Sanctuary"),
    (2, "Wan Shi Tong, Librarian"),
    (4, "Requiting Hex"),
    (4, "Dream Beavers"),
    (2, "We Say Thee Nay!"),
    (2, "The Wondrous Wasp"),
    (3, "Hidden Lair"),
)

EXPECTED_SIDEBOARD = (
    (2, "Flashfreeze"),
    (4, "Duress"),
    (1, "Spell Snare"),
    (2, "Annul"),
    (1, "Qarsi Revenant"),
    (3, "Strategic Betrayal"),
    (2, "Raven Eagle"),
)

EXPECTED_IZZET_MAIN = (
    (3, "Burst Lightning"),
    (3, "Traumatic Critique"),
    (4, "Prismari Charm"),
    (2, "Impractical Joke"),
    (4, "Sunderflock"),
    (2, "Spell Pierce"),
    (4, "Steam Vents"),
    (4, "Spirebluff Canal"),
    (4, "Riverpyre Verge"),
    (2, "Get Out"),
    (4, "Hearth Elemental"),
    (4, "Opt"),
    (1, "Stormcarved Coast"),
    (3, "Winternight Stories"),
    (1, "Multiversal Passage"),
    (1, "Spell Snare"),
    (4, "Sleight of Hand"),
    (4, "Eddymurk Crab"),
    (6, "Island"),
)

EXPECTED_IZZET_SIDEBOARD = (
    (2, "Annul"),
    (1, "Flashfreeze"),
    (1, "Sear"),
    (2, "Shore Up"),
    (1, "Ral, Crackling Wit"),
    (2, "Spell Snare"),
    (4, "Colorstorm Stallion"),
    (2, "Hydro-Man, Fluid Felon"),
)


class DeckParsingTests(unittest.TestCase):
    def test_exact_dimir_main_deck_is_preserved_and_has_sixty_cards(self):
        deck = parse_deck(MAIN)
        self.assertEqual(
            tuple((entry.quantity, entry.card_name) for entry in deck.entries),
            EXPECTED_MAIN,
        )
        self.assertEqual(deck.card_count, 60)

    def test_exact_dimir_sideboard_is_preserved_and_has_fifteen_cards(self):
        deck = parse_deck(SIDEBOARD)
        self.assertEqual(
            tuple((entry.quantity, entry.card_name) for entry in deck.entries),
            EXPECTED_SIDEBOARD,
        )
        self.assertEqual(deck.card_count, 15)

    def test_source_hash_is_stable(self):
        self.assertEqual(
            parse_deck(MAIN).source_hash,
            "ecb3dfde9db58b66905f889ed1c73402abe571ec4121340920e9181a63915547",
        )
        self.assertEqual(
            parse_deck(SIDEBOARD).source_hash,
            "b18745d0c178930f66d8f3d1917e60e92d7b8260533715244a94fb6cdb0eb12c",
        )

    def test_parser_rejects_malformed_and_duplicate_entries(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "deck.txt"
            path.write_text("invalid\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_deck(path)
            path.write_text("1 Island\n2 Island\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_deck(path)

    def test_card_validation_reports_unsupported_cards_without_substitution(self):
        deck = parse_deck(SIDEBOARD)
        supported = set(deck.card_names) - {"Qarsi Revenant"}
        self.assertEqual(deck.unknown_cards(supported), ("Qarsi Revenant",))

    def test_exact_izzet_tournament_list_is_sixty_plus_fifteen(self):
        main = parse_deck(IZZET_MAIN)
        sideboard = parse_deck(IZZET_SIDEBOARD)
        self.assertEqual(
            tuple((entry.quantity, entry.card_name) for entry in main.entries),
            EXPECTED_IZZET_MAIN,
        )
        self.assertEqual(
            tuple((entry.quantity, entry.card_name) for entry in sideboard.entries),
            EXPECTED_IZZET_SIDEBOARD,
        )
        self.assertEqual(main.card_count, 60)
        self.assertEqual(sideboard.card_count, 15)
        self.assertEqual(
            main.source_hash,
            "75e3e9a0108867fb711c425a93c3ac6390b610c8d8a403409f41edb12a146461",
        )
        self.assertEqual(
            sideboard.source_hash,
            "7ef7b481b251016ee11e9305a4c6957c43b2bda5d782803ecc44e62b626b140c",
        )


if __name__ == "__main__":
    unittest.main()
