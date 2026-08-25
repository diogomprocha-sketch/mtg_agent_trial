from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from engine.runner.runner import ForgeRunner, GameStatus, SimulationRequest


ROOT = Path(__file__).resolve().parents[1]
FORGE_HOME = ROOT / "engine" / "forge" / "dist" / "2.0.14"


class ForgeOutputTests(unittest.TestCase):
    def test_parses_wins_and_draws(self):
        output = """
Game Result: Game 1 ended in 1234 ms. Ai(1)-Dimir Midrange has won!
Game Result: Game 2 ended in a Draw! Took 120000 ms.
"""
        results = ForgeRunner._parse_results(output)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].winner, "Ai(1)-Dimir Midrange")
        self.assertEqual(results[0].duration_ms, 1234)
        self.assertTrue(results[1].draw)

    def test_default_forge_home_is_repository_local_distribution(self):
        expected = (
            Path(__file__).resolve().parents[1]
            / "engine"
            / "forge"
            / "dist"
            / "2.0.14"
        )
        self.assertEqual(ForgeRunner().forge_home, expected)

    def test_sideboard_paths_follow_repository_conventions(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            main = root / "main.txt"
            sideboard = root / "sideboard.txt"
            opponent = root / "izzet.txt"
            opponent_sideboard = root / "izzet_sideboard.txt"
            for path in (sideboard, opponent_sideboard):
                path.write_text("15 Island\n", encoding="utf-8")
            self.assertEqual(
                ForgeRunner._sideboard(None, main, opponent=False).card_count,
                15,
            )
            self.assertEqual(
                ForgeRunner._sideboard(None, opponent, opponent=True).card_count,
                15,
            )

    def test_normalized_log_ignores_wall_clock_duration(self):
        first = "Mulligan: kept\nGame Result: Game 1 ended in 10 ms. A has won!\n"
        second = "Mulligan: kept\nGame Result: Game 1 ended in 99 ms. A has won!\n"
        self.assertEqual(
            ForgeRunner.normalized_game_log_sha256(first),
            ForgeRunner.normalized_game_log_sha256(second),
        )

    def test_classifies_timeout_without_counting_a_result(self):
        request = SimulationRequest(
            deck=ROOT / "decks" / "dimir_midrange" / "main.txt",
            opponent=ROOT / "decks" / "opponents" / "izzet_spellementals.txt",
            games=1,
            seed=7,
            timeout_seconds=1,
            output_dir=ROOT / "results",
            play_draw="play",
        )
        games = ForgeRunner._classify_results(
            (),
            output="Stopping slow match as draw\n",
            request=request,
            run_id="timeout-test",
            output_dir=ROOT / "results",
            timed_out=False,
            process_exit_code=0,
        )
        self.assertEqual(games[0].status, GameStatus.FAILED_TIMEOUT)
        self.assertIsNone(games[0].winner)
        self.assertFalse(games[0].draw)

    def test_trajectory_is_structured_and_marks_unavailable_fields(self):
        output = """\
Mulligan: Ai(1)-Dimir Midrange has kept a hand of 7 cards
Turn: Turn 1 (Ai(1)-Dimir Midrange)
Phase: Ai(1)-Dimir Midrange's Main phase, precombat
Land: Ai(1)-Dimir Midrange played Island
Game Result: Game 1 ended in 10 ms. Ai(1)-Dimir Midrange has won!
"""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "trajectory.jsonl"
            ForgeRunner._write_trajectory(
                path,
                output,
                game_id="game-1",
                seed=9,
                play_draw="play",
                winner="Ai(1)-Dimir Midrange",
                game_length_turns=1,
            )
            import json

            records = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
            ]
        self.assertEqual(records[0]["seed"], 9)
        self.assertIsNone(records[0]["opening_hand"])
        self.assertFalse(records[0]["opening_hand_available"])
        land = next(record for record in records if record.get("selected_action"))
        self.assertIsNone(land["legal_actions"])
        self.assertFalse(land["game_state"]["snapshot_complete"])


@unittest.skipUnless(
    (FORGE_HOME / "forge-gui-desktop-2.0.14-jar-with-dependencies.jar").is_file(),
    "Forge 2.0.14 distribution is not installed",
)
class ForgeIntegrationTests(unittest.TestCase):
    def test_distribution_contains_exact_card_and_teamwork_script(self):
        ForgeRunner(FORGE_HOME).verify_we_say_thee_nay()

    def test_seed_12345_completes_and_replays_identically(self):
        with TemporaryDirectory() as directory:
            request = SimulationRequest(
                deck=ROOT / "decks" / "dimir_midrange" / "main.txt",
                sideboard=None,
                opponent=ROOT / "decks" / "opponents" / "izzet_spellementals.txt",
                opponent_sideboard=None,
                games=1,
                seed=12345,
                timeout_seconds=120,
                output_dir=Path(directory),
            )
            first = ForgeRunner(FORGE_HOME).run(request)
            second = ForgeRunner(FORGE_HOME).run(request)
            self.assertEqual(first.exit_code, 0)
            self.assertEqual(second.exit_code, 0)
            self.assertEqual(len(first.games), 1)
            self.assertEqual(len(second.games), 1)
            self.assertEqual(first.games[0].winner, second.games[0].winner)
            first_log = first.log_path.read_text(encoding="utf-8")
            second_log = second.log_path.read_text(encoding="utf-8")
            self.assertEqual(
                ForgeRunner.normalized_game_log_sha256(first_log),
                ForgeRunner.normalized_game_log_sha256(second_log),
            )
            self.assertIn("cast We Say Thee Nay!", first_log)
            self.assertIn("Send countered spell to Graveyard", first_log)

    def test_forced_play_and_draw_change_the_starting_player(self):
        with TemporaryDirectory() as directory:
            positions = []
            for play_draw, seed in (("play", 43101), ("draw", 43102)):
                request = SimulationRequest(
                    deck=ROOT / "decks" / "dimir_midrange" / "main.txt",
                    sideboard=None,
                    opponent=ROOT / "decks" / "opponents" / "izzet_spellementals.txt",
                    opponent_sideboard=None,
                    games=1,
                    seed=seed,
                    timeout_seconds=120,
                    output_dir=Path(directory),
                    play_draw=play_draw,
                )
                result = ForgeRunner(FORGE_HOME).run(request)
                self.assertEqual(result.exit_code, 0)
                self.assertIn(
                    result.games[0].status,
                    (GameStatus.COMPLETED_WIN, GameStatus.COMPLETED_LOSS),
                )
                positions.append(result.games[0].play_draw)
            self.assertEqual(positions, ["play", "draw"])


if __name__ == "__main__":
    unittest.main()
