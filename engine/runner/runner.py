"""Subprocess adapter for Forge's verified desktop `sim` entry point."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Optional
from uuid import uuid4
from zipfile import ZipFile

from engine.adapter.decks import (
    DeckList,
    apply_sideboard_plan,
    parse_deck,
    parse_sideboard_plan,
)

FORGE_VERSION = "2.0.14"
FORGE_JAR = "forge-gui-desktop-2.0.14-jar-with-dependencies.jar"
FORGE_BUILD = "2.0.14+mtg-agent.1"
PATCHED_JAR_SHA256 = "061f2de33ff9d4f0ba40fc6a8afc82ec547fe74a0468191d8ec4a331e506ce88"
AGENT_VERSION = "0.1.0"
RESULT_PATTERN = re.compile(
    r"Game Result: Game (?P<game>\d+) ended in "
    r"(?:(?P<draw>a Draw)! Took (?P<draw_duration>\d+) ms\."
    r"|(?P<duration>\d+) ms\. (?P<winner>.+) has won!)"
)
TURN_PATTERN = re.compile(r"^Turn: Turn (?P<turn>\d+) \((?P<player>.+)\)$")
PHASE_PATTERN = re.compile(r"^Phase: (?P<phase>.+)$")
ACTION_PREFIXES = (
    "Add To Stack:",
    "Attackers:",
    "Blockers:",
    "Discard:",
    "Land:",
)
CARD_ARCHIVE_PATH = Path("res/cardsfolder/cardsfolder.zip")
WE_SAY_THEE_NAY_PATH = "w/we_say_thee_nay.txt"
WE_SAY_THEE_NAY_REQUIRED_LINES = {
    "Name:We Say Thee Nay!",
    "ManaCost:1 U",
    "Types:Instant Arcane",
    "K:Teamwork:2",
    "SVar:X:Count$Teamwork.4.2",
}


@dataclass(frozen=True)
class SimulationRequest:
    deck: Path
    opponent: Path
    games: int
    seed: int
    timeout_seconds: int
    output_dir: Path
    sideboard: Optional[Path] = None
    opponent_sideboard: Optional[Path] = None
    sideboard_plan: Optional[Path] = None
    play_draw: Optional[str] = None

    def __post_init__(self) -> None:
        if isinstance(self.games, bool) or not isinstance(self.games, int) or self.games < 1:
            raise ValueError("games must be a positive integer")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, int)
            or self.timeout_seconds < 1
        ):
            raise ValueError("timeout must be a positive integer")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        if self.play_draw not in (None, "play", "draw"):
            raise ValueError("play_draw must be 'play', 'draw', or None")
        if self.play_draw is not None and self.games != 1:
            raise ValueError("explicit play/draw requires one game per runner invocation")


class GameStatus(str, Enum):
    COMPLETED_WIN = "COMPLETED_WIN"
    COMPLETED_LOSS = "COMPLETED_LOSS"
    FAILED_TIMEOUT = "FAILED_TIMEOUT"
    FAILED_CRASH = "FAILED_CRASH"
    FAILED_INVALID = "FAILED_INVALID"


@dataclass(frozen=True)
class GameResult:
    game_number: int
    winner: Optional[str]
    draw: bool
    duration_ms: Optional[int]
    status: GameStatus = GameStatus.FAILED_INVALID
    seed: Optional[int] = None
    play_draw: Optional[str] = None
    game_length_turns: Optional[int] = None
    mulligan_count: Optional[int] = None
    trajectory_location: Optional[str] = None


@dataclass(frozen=True)
class SimulationResult:
    run_id: str
    exit_code: int
    games: tuple[GameResult, ...]
    result_path: Path
    log_path: Path


class ForgeRunner:
    def __init__(self, forge_home: Optional[Path] = None) -> None:
        configured = forge_home or (
            Path(os.environ["MTG_FORGE_HOME"])
            if "MTG_FORGE_HOME" in os.environ
            else Path(__file__).resolve().parents[1] / "forge" / "dist" / FORGE_VERSION
        )
        self.forge_home = configured.resolve()

    def run(self, request: SimulationRequest) -> SimulationResult:
        java = self._java_executable()
        jar = self.forge_home / FORGE_JAR
        if not jar.is_file():
            raise FileNotFoundError(f"Forge executable JAR not found: {jar}")
        if sha256(jar.read_bytes()).hexdigest() != PATCHED_JAR_SHA256:
            raise RuntimeError(
                "Forge executable JAR does not match the tested mtg-agent patch"
            )
        self.verify_we_say_thee_nay()

        main = parse_deck(request.deck)
        sideboard = self._sideboard(request.sideboard, request.deck, opponent=False)
        opponent = parse_deck(request.opponent)
        opponent_sideboard = self._sideboard(
            request.opponent_sideboard,
            request.opponent,
            opponent=True,
        )
        if main.card_count != 60 or opponent.card_count != 60:
            raise ValueError("both main decks must contain exactly 60 cards")
        if sideboard.card_count != 15 or opponent_sideboard.card_count != 15:
            raise ValueError("both sideboards must contain exactly 15 cards")
        original_main_hash = main.source_hash
        original_sideboard_hash = sideboard.source_hash
        sideboard_plan_hash = None
        if request.sideboard_plan is not None:
            sideboard_plan = parse_sideboard_plan(request.sideboard_plan)
            main, sideboard = apply_sideboard_plan(main, sideboard, sideboard_plan)
            sideboard_plan_hash = sideboard_plan.source_hash

        run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
        request.output_dir.mkdir(parents=True, exist_ok=True)
        log_path = request.output_dir / f"{run_id}.forge.log"
        result_path = request.output_dir / f"{run_id}.result.json"

        forge_deck_dir = (
            Path.home()
            / "Library"
            / "Application Support"
            / "Forge"
            / "decks"
            / "constructed"
        )
        forge_deck_dir.mkdir(parents=True, exist_ok=True)
        player_name = f"mtg-agent-{run_id}-player.dck"
        opponent_name = f"mtg-agent-{run_id}-opponent.dck"
        player_path = forge_deck_dir / player_name
        opponent_path = forge_deck_dir / opponent_name

        player_path.write_text(
            main.to_forge_dck("Dimir Midrange", sideboard),
            encoding="utf-8",
        )
        opponent_path.write_text(
            opponent.to_forge_dck("Izzet Spellementals", opponent_sideboard),
            encoding="utf-8",
        )

        command = [
            str(java),
            "-Xmx4096m",
            "-Dio.netty.tryReflectionSetAccessible=true",
            "-Dfile.encoding=UTF-8",
            "-jar",
            str(jar),
            "sim",
            "-d",
            player_name,
            opponent_name,
            "-n",
            str(request.games),
            "-s",
            str(request.seed),
            "-c",
            str(request.timeout_seconds),
        ]
        if request.play_draw is not None:
            command.extend(("-i", "1" if request.play_draw == "play" else "2"))
        completed = None
        timed_out = False
        crashed = False
        try:
            try:
                completed = subprocess.run(
                    command,
                    cwd=self.forge_home,
                    capture_output=True,
                    text=True,
                    timeout=request.timeout_seconds * request.games + 60,
                    check=False,
                )
                output = completed.stdout + completed.stderr
            except subprocess.TimeoutExpired as error:
                timed_out = True
                stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else error.stdout
                stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else error.stderr
                output = (stdout or "") + (stderr or "")
            except OSError as error:
                crashed = True
                output = f"{type(error).__name__}: {error}\n"
        finally:
            player_path.unlink(missing_ok=True)
            opponent_path.unlink(missing_ok=True)

        log_path.write_text(output, encoding="utf-8")
        process_exit_code = (
            -1 if crashed else None if completed is None else completed.returncode
        )
        parsed_games = self._parse_results(output)
        games = self._classify_results(
            parsed_games,
            output=output,
            request=request,
            run_id=run_id,
            output_dir=request.output_dir,
            timed_out=timed_out,
            process_exit_code=process_exit_code,
        )
        failed = any(game.status.value.startswith("FAILED_") for game in games)
        payload = {
            "run_id": run_id,
            "configuration": {
                "games": request.games,
                "seed": request.seed,
                "timeout_seconds": request.timeout_seconds,
                "play_draw": request.play_draw,
                "sideboard_plan": (
                    str(request.sideboard_plan) if request.sideboard_plan else None
                ),
            },
            "decklist_hash": original_main_hash,
            "sideboard_hash": original_sideboard_hash,
            "effective_decklist_hash": main.source_hash,
            "effective_sideboard_hash": sideboard.source_hash,
            "sideboard_plan_hash": sideboard_plan_hash,
            "opponent_list_hash": opponent.source_hash,
            "opponent_sideboard_hash": opponent_sideboard.source_hash,
            "engine_version": FORGE_BUILD,
            "agent_version": AGENT_VERSION,
            "process_exit_code": process_exit_code,
            "games_completed": sum(
                game.status in (GameStatus.COMPLETED_WIN, GameStatus.COMPLETED_LOSS)
                for game in games
            ),
            "result": [asdict(game) for game in games],
            "forge_log_location": str(log_path),
            "trajectory_capture_complete": False,
            "trajectory_limitations": [
                "Forge 2.0.14 does not expose opening-hand card identities in its game log.",
                "Forge 2.0.14 does not expose a complete game-state snapshot per decision.",
                "Forge 2.0.14 does not expose the complete legal-action set per decision.",
                "Selected actions include only actions represented by Forge game-log events.",
            ],
            "normalized_game_log_sha256": (
                self.normalized_game_log_sha256(output) if not failed else None
            ),
        }
        if failed:
            result_path = request.output_dir / f"{run_id}.failure.json"
        result_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        exit_code = 2 if failed else 0
        return SimulationResult(
            run_id=run_id,
            exit_code=exit_code,
            games=games,
            result_path=result_path,
            log_path=log_path,
        )

    @classmethod
    def _classify_results(
        cls,
        parsed_games: tuple[GameResult, ...],
        *,
        output: str,
        request: SimulationRequest,
        run_id: str,
        output_dir: Path,
        timed_out: bool,
        process_exit_code: Optional[int],
    ) -> tuple[GameResult, ...]:
        failure_status = None
        if timed_out or "Stopping slow match as draw" in output:
            failure_status = GameStatus.FAILED_TIMEOUT
        elif process_exit_code not in (None, 0):
            failure_status = GameStatus.FAILED_CRASH
        elif len(parsed_games) != request.games or any(game.draw for game in parsed_games):
            failure_status = GameStatus.FAILED_INVALID

        actual_play_draw, turns, mulligans = cls._log_metadata(output)
        if (
            failure_status is None
            and request.play_draw is not None
            and actual_play_draw != request.play_draw
        ):
            failure_status = GameStatus.FAILED_INVALID
        if "SVar 'Any'" in output:
            failure_status = GameStatus.FAILED_INVALID

        if failure_status is not None:
            return (
                GameResult(
                    game_number=1,
                    winner=None,
                    draw=False,
                    duration_ms=None,
                    status=failure_status,
                    seed=request.seed,
                    play_draw=actual_play_draw,
                    game_length_turns=turns,
                    mulligan_count=mulligans,
                ),
            )

        results = []
        for parsed in parsed_games:
            trajectory_path = output_dir / f"{run_id}.game-{parsed.game_number}.trajectory.jsonl"
            cls._write_trajectory(
                trajectory_path,
                output,
                game_id=f"{run_id}-{parsed.game_number}",
                seed=request.seed,
                play_draw=actual_play_draw,
                winner=parsed.winner,
                game_length_turns=turns,
            )
            results.append(
                GameResult(
                    game_number=parsed.game_number,
                    winner=parsed.winner,
                    draw=False,
                    duration_ms=parsed.duration_ms,
                    status=(
                        GameStatus.COMPLETED_WIN
                        if parsed.winner == "Ai(1)-Dimir Midrange"
                        else GameStatus.COMPLETED_LOSS
                    ),
                    seed=request.seed,
                    play_draw=actual_play_draw,
                    game_length_turns=turns,
                    mulligan_count=mulligans,
                    trajectory_location=str(trajectory_path),
                )
            )
        return tuple(results)

    @staticmethod
    def _log_metadata(output: str) -> tuple[Optional[str], Optional[int], int]:
        turns = []
        first_player = None
        mulligan_count = 0
        for line in output.splitlines():
            turn_match = TURN_PATTERN.match(line)
            if turn_match:
                turns.append(int(turn_match.group("turn")))
                if first_player is None:
                    first_player = turn_match.group("player")
            if (
                line.startswith("Mulligan: Ai(1)-Dimir Midrange has mulliganed")
            ):
                mulligan_count += 1
        play_draw = None
        if first_player is not None:
            play_draw = "play" if first_player == "Ai(1)-Dimir Midrange" else "draw"
        return play_draw, max(turns) if turns else None, mulligan_count

    @staticmethod
    def _write_trajectory(
        path: Path,
        output: str,
        *,
        game_id: str,
        seed: int,
        play_draw: Optional[str],
        winner: Optional[str],
        game_length_turns: Optional[int],
    ) -> None:
        turn = None
        active_player = None
        phase = None
        records = [
            {
                "record_type": "game",
                "game_id": game_id,
                "seed": seed,
                "player": "Dimir Midrange",
                "opponent": "Izzet Spellementals",
                "play_draw": play_draw,
                "opening_hand": None,
                "opening_hand_available": False,
            }
        ]
        for line in output.splitlines():
            turn_match = TURN_PATTERN.match(line)
            if turn_match:
                turn = int(turn_match.group("turn"))
                active_player = turn_match.group("player")
            phase_match = PHASE_PATTERN.match(line)
            if phase_match:
                phase = phase_match.group("phase")
            if line.startswith(("Mulligan:", "Turn:", "Phase:")) or line.startswith(
                ACTION_PREFIXES
            ):
                records.append(
                    {
                        "record_type": "event",
                        "game_id": game_id,
                        "seed": seed,
                        "turn": turn,
                        "phase": phase,
                        "game_state": {
                            "active_player": active_player,
                            "snapshot_complete": False,
                        },
                        "legal_actions": None,
                        "legal_actions_available": False,
                        "selected_action": (
                            line if line.startswith(ACTION_PREFIXES) else None
                        ),
                        "event": line,
                    }
                )
        records.append(
            {
                "record_type": "result",
                "game_id": game_id,
                "seed": seed,
                "winner": winner,
                "game_length_turns": game_length_turns,
            }
        )
        path.write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
            encoding="utf-8",
        )

    def verify_we_say_thee_nay(self) -> None:
        archive = self.forge_home / CARD_ARCHIVE_PATH
        if not archive.is_file():
            raise FileNotFoundError(f"Forge card archive not found: {archive}")
        with ZipFile(archive) as cards:
            try:
                script = cards.read(WE_SAY_THEE_NAY_PATH).decode("utf-8")
            except KeyError as error:
                raise RuntimeError("Forge does not contain We Say Thee Nay!") from error
        lines = set(script.splitlines())
        missing = WE_SAY_THEE_NAY_REQUIRED_LINES - lines
        if missing:
            raise RuntimeError(
                f"Forge We Say Thee Nay! script is incompatible: {sorted(missing)}"
            )

    @staticmethod
    def normalized_game_log_sha256(output: str) -> str:
        start = output.find("Mulligan:")
        end_marker = "Game Result:"
        end = output.rfind(end_marker)
        if start < 0 or end < 0:
            raise ValueError("Forge output does not contain a complete game log")
        end = output.find("\n", end)
        if end < 0:
            end = len(output)
        game_log = output[start:end]
        normalized = re.sub(
            r"Game Result: Game (\d+) ended in \d+ ms\.",
            r"Game Result: Game \1 ended in DURATION ms.",
            game_log,
        )
        return sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _sideboard(
        path: Optional[Path],
        main_path: Path,
        opponent: bool,
    ) -> DeckList:
        if path is None:
            path = (
                main_path.with_name(f"{main_path.stem}_sideboard.txt")
                if opponent
                else main_path.with_name("sideboard.txt")
            )
        if not path.is_file():
            raise FileNotFoundError(f"sideboard not found: {path}")
        return parse_deck(path)

    @staticmethod
    def _parse_results(output: str) -> tuple[GameResult, ...]:
        results = []
        for match in RESULT_PATTERN.finditer(output):
            results.append(
                GameResult(
                    game_number=int(match.group("game")),
                    winner=None if match.group("draw") else match.group("winner"),
                    draw=match.group("draw") is not None,
                    duration_ms=(
                        int(match.group("duration") or match.group("draw_duration"))
                    ),
                )
            )
        return tuple(results)

    @staticmethod
    def _java_executable() -> Path:
        configured = os.environ.get("MTG_JAVA")
        if configured:
            path = Path(configured)
        else:
            discovered = shutil.which("java")
            if discovered and subprocess.run(
                [discovered, "-version"],
                capture_output=True,
                check=False,
            ).returncode == 0:
                path = Path(discovered)
            else:
                path = Path("/opt/homebrew/opt/openjdk@17/bin/java")
        if not path.is_file():
            raise FileNotFoundError("Java 17+ executable not found")
        return path
