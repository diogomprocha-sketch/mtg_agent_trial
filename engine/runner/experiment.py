"""Sequential, reproducible Dimir versus Izzet Forge experiments."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from typing import Iterable, Optional

from engine.adapter.decks import (
    apply_sideboard_plan,
    parse_deck,
    parse_sideboard_plan,
)
from engine.runner.runner import FORGE_BUILD, ForgeRunner, GameStatus, SimulationRequest


ROOT = Path(__file__).resolve().parents[2]
DIMIR_MAIN = ROOT / "decks" / "dimir_midrange" / "main.txt"
DIMIR_SIDEBOARD = ROOT / "decks" / "dimir_midrange" / "sideboard.txt"
IZZET_MAIN = ROOT / "decks" / "opponents" / "izzet_spellementals.txt"
IZZET_SIDEBOARD = ROOT / "decks" / "opponents" / "izzet_spellementals_sideboard.txt"
SIDEBOARD_PLAN = ROOT / "data" / "sideboarding" / "izzet_spellementals.json"
COMPLETED = {GameStatus.COMPLETED_WIN, GameStatus.COMPLETED_LOSS}


def run_experiment(
    output_dir: Path,
    *,
    games_per_stage: int,
    first_seed: int,
) -> list[dict]:
    if games_per_stage < 2 or games_per_stage % 2:
        raise ValueError("games_per_stage must be a positive even number")
    existing = (
        [path for path in output_dir.iterdir() if path.name != "validation"]
        if output_dir.exists()
        else []
    )
    if existing:
        raise FileExistsError(f"refusing to mix experiment data in {output_dir}")

    main = parse_deck(DIMIR_MAIN)
    sideboard = parse_deck(DIMIR_SIDEBOARD)
    opponent = parse_deck(IZZET_MAIN)
    opponent_sideboard = parse_deck(IZZET_SIDEBOARD)
    plan = parse_sideboard_plan(SIDEBOARD_PLAN)
    postboard_main, postboard_sideboard = apply_sideboard_plan(
        main, sideboard, plan
    )
    raw_dir = output_dir / "raw_logs"
    raw_dir.mkdir(parents=True, exist_ok=True)

    specs = []
    seed = first_seed
    for stage in ("preboard", "postboard"):
        for play_draw in ("play", "draw"):
            for _ in range(games_per_stage // 2):
                specs.append((stage, play_draw, seed))
                seed += 1

    config = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": FORGE_BUILD,
        "agent_version": "0.1.0",
        "games_requested": len(specs),
        "games_per_stage": games_per_stage,
        "execution": "sequential",
        "seeds": [spec[2] for spec in specs],
        "decklist_hash": main.source_hash,
        "sideboard_hash": sideboard.source_hash,
        "postboard_decklist_hash": postboard_main.source_hash,
        "postboard_sideboard_hash": postboard_sideboard.source_hash,
        "opponent_list_hash": opponent.source_hash,
        "opponent_sideboard_hash": opponent_sideboard.source_hash,
        "sideboard_plan": str(SIDEBOARD_PLAN.relative_to(ROOT)),
        "sideboard_plan_hash": plan.source_hash,
        "trajectory_capture_complete": False,
        "trajectory_limitations": [
            "Opening-hand card identities are not exposed by the Forge 2.0.14 game log.",
            "Complete game-state snapshots are not exposed by the Forge 2.0.14 game log.",
            "Complete legal-action sets are not exposed by the Forge 2.0.14 game log.",
            "Selected actions contain only actions represented by Forge game-log events.",
        ],
    }
    (output_dir / "config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    game_records = []
    games_path = output_dir / "games.jsonl"
    runner = ForgeRunner()
    for index, (stage, play_draw, game_seed) in enumerate(specs, start=1):
        result = runner.run(
            SimulationRequest(
                deck=DIMIR_MAIN,
                sideboard=DIMIR_SIDEBOARD,
                opponent=IZZET_MAIN,
                opponent_sideboard=IZZET_SIDEBOARD,
                sideboard_plan=SIDEBOARD_PLAN if stage == "postboard" else None,
                games=1,
                seed=game_seed,
                timeout_seconds=120,
                output_dir=raw_dir,
                play_draw=play_draw,
            )
        )
        game = result.games[0]
        payload = json.loads(result.result_path.read_text(encoding="utf-8"))
        record = {
            "experiment_game": index,
            "stage": stage,
            "seed": game_seed,
            "requested_play_draw": play_draw,
            "actual_play_draw": game.play_draw,
            "status": game.status.value,
            "winner": game.winner,
            "dimir_win": game.status == GameStatus.COMPLETED_WIN,
            "mulligan_count": game.mulligan_count,
            "game_length_turns": game.game_length_turns,
            "duration_ms": game.duration_ms,
            "decklist_hash": payload["effective_decklist_hash"],
            "sideboard_hash": payload["effective_sideboard_hash"],
            "forge_log_location": str(result.log_path),
            "trajectory_location": game.trajectory_location,
            "trajectory_capture_complete": False,
        }
        with games_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
        game_records.append(record)
        if game.status not in COMPLETED:
            raise RuntimeError(
                f"game {index} seed {game_seed} failed with {game.status.value}; "
                f"see {result.log_path}"
            )

    summary = summarize(game_records)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(
        render_report(summary, config),
        encoding="utf-8",
    )
    return game_records


def summarize(records: list[dict]) -> dict:
    completed = [record for record in records if record["status"] in {
        GameStatus.COMPLETED_WIN.value,
        GameStatus.COMPLETED_LOSS.value,
    }]
    failed = [record for record in records if record not in completed]

    def rate(items: Iterable[dict]) -> dict:
        items = list(items)
        wins = sum(item["dimir_win"] for item in items)
        count = len(items)
        return {
            "games": count,
            "wins": wins,
            "losses": count - wins,
            "win_rate": wins / count if count else None,
            "wilson_95": _wilson(wins, count),
        }

    by_mulligan = defaultdict(list)
    for record in completed:
        by_mulligan[str(record["mulligan_count"])].append(record)

    patterns = {"wins": Counter(), "losses": Counter()}
    for record in completed:
        key = "wins" if record["dimir_win"] else "losses"
        trajectory = Path(record["trajectory_location"])
        for line in trajectory.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            action = event.get("selected_action")
            if action:
                patterns[key][_normalize_action(action)] += 1

    preboard = rate(record for record in completed if record["stage"] == "preboard")
    postboard = rate(record for record in completed if record["stage"] == "postboard")
    return {
        "sample_size": len(completed),
        "failed_games": len(failed),
        "overall": rate(completed),
        "preboard": preboard,
        "postboard": postboard,
        "play": rate(record for record in completed if record["actual_play_draw"] == "play"),
        "draw": rate(record for record in completed if record["actual_play_draw"] == "draw"),
        "mulligan_rate": (
            sum((record["mulligan_count"] or 0) > 0 for record in completed)
            / len(completed)
            if completed
            else None
        ),
        "win_rate_by_mulligan_count": {
            count: rate(items) for count, items in sorted(by_mulligan.items())
        },
        "average_game_length_turns": (
            sum(record["game_length_turns"] for record in completed) / len(completed)
            if completed
            else None
        ),
        "sideboard_impact": (
            postboard["win_rate"] - preboard["win_rate"]
            if postboard["win_rate"] is not None and preboard["win_rate"] is not None
            else None
        ),
        "common_winning_patterns": patterns["wins"].most_common(5),
        "common_losing_patterns": patterns["losses"].most_common(5),
    }


def _wilson(wins: int, count: int) -> Optional[list[float]]:
    if count == 0:
        return None
    z = 1.959963984540054
    proportion = wins / count
    denominator = 1 + z * z / count
    center = (proportion + z * z / (2 * count)) / denominator
    margin = (
        z
        * math.sqrt(proportion * (1 - proportion) / count + z * z / (4 * count * count))
        / denominator
    )
    return [center - margin, center + margin]


def _normalize_action(action: str) -> str:
    return re.sub(r" \(\d+\)", "", action)


def render_report(summary: dict, config: dict) -> str:
    def percent(value: Optional[float]) -> str:
        return "N/A" if value is None else f"{value:.1%}"

    return f"""# Dimir Midrange vs Izzet Spellementals

All results below were produced by local Forge {config['engine_version']} games.
The sample contains {summary['sample_size']} completed games and
{summary['failed_games']} failed games. Failed games are excluded from rates.

| Slice | Games | Wins | Losses | Win rate |
| --- | ---: | ---: | ---: | ---: |
| Overall | {summary['overall']['games']} | {summary['overall']['wins']} | {summary['overall']['losses']} | {percent(summary['overall']['win_rate'])} |
| Pre-board | {summary['preboard']['games']} | {summary['preboard']['wins']} | {summary['preboard']['losses']} | {percent(summary['preboard']['win_rate'])} |
| Post-board | {summary['postboard']['games']} | {summary['postboard']['wins']} | {summary['postboard']['losses']} | {percent(summary['postboard']['win_rate'])} |
| Play | {summary['play']['games']} | {summary['play']['wins']} | {summary['play']['losses']} | {percent(summary['play']['win_rate'])} |
| Draw | {summary['draw']['games']} | {summary['draw']['wins']} | {summary['draw']['losses']} | {percent(summary['draw']['win_rate'])} |

- Mulligan rate: {percent(summary['mulligan_rate'])}
- Average game length: {summary['average_game_length_turns']:.2f} turns
- Sideboard impact: {percent(summary['sideboard_impact'])}
- Overall 95% Wilson interval: {summary['overall']['wilson_95']}

## Common logged action patterns

Winning games: `{summary['common_winning_patterns']}`

Losing games: `{summary['common_losing_patterns']}`

## Trajectory limitation

Forge 2.0.14's stock game log does not expose opening-hand identities, complete
state snapshots, or complete legal-action sets. The JSONL trajectories preserve
all available turn, phase, mulligan, and selected game-log action events and mark
the unavailable fields explicitly. They are not labeled complete trajectories.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--games-per-stage", type=int, required=True)
    parser.add_argument("--first-seed", type=int, required=True)
    args = parser.parse_args()
    run_experiment(
        args.output_dir,
        games_per_stage=args.games_per_stage,
        first_seed=args.first_seed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
