"""Subprocess adapter for Forge's verified desktop `sim` entry point."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
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

from engine.adapter.decks import DeckList, parse_deck

FORGE_VERSION = "2.0.14"
FORGE_JAR = "forge-gui-desktop-2.0.14-jar-with-dependencies.jar"
AGENT_VERSION = "0.1.0"
RESULT_PATTERN = re.compile(
    r"Game Result: Game (?P<game>\d+) ended in "
    r"(?:(?P<draw>a Draw)! Took (?P<draw_duration>\d+) ms\."
    r"|(?P<duration>\d+) ms\. (?P<winner>.+) has won!)"
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


@dataclass(frozen=True)
class GameResult:
    game_number: int
    winner: Optional[str]
    draw: bool
    duration_ms: Optional[int]


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
        try:
            completed = subprocess.run(
                command,
                cwd=self.forge_home,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds * request.games + 60,
                check=False,
            )
        finally:
            player_path.unlink(missing_ok=True)
            opponent_path.unlink(missing_ok=True)

        output = completed.stdout + completed.stderr
        log_path.write_text(output, encoding="utf-8")
        games = self._parse_results(output)
        payload = {
            "run_id": run_id,
            "configuration": {
                "games": request.games,
                "seed": request.seed,
                "timeout_seconds": request.timeout_seconds,
            },
            "decklist_hash": main.source_hash,
            "sideboard_hash": sideboard.source_hash,
            "opponent_list_hash": opponent.source_hash,
            "opponent_sideboard_hash": opponent_sideboard.source_hash,
            "engine_version": FORGE_VERSION,
            "agent_version": AGENT_VERSION,
            "process_exit_code": completed.returncode,
            "games_completed": len(games),
            "result": [asdict(game) for game in games],
            "forge_log_location": str(log_path),
            "trajectory_location": None,
            "trajectory_capture_complete": False,
            "normalized_game_log_sha256": self.normalized_game_log_sha256(output),
        }
        result_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        exit_code = completed.returncode
        if len(games) != request.games:
            exit_code = exit_code or 2
        return SimulationResult(
            run_id=run_id,
            exit_code=exit_code,
            games=games,
            result_path=result_path,
            log_path=log_path,
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
