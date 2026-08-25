"""Command-line entry point for one or more Forge AI games."""

import argparse
from pathlib import Path

from .runner import ForgeRunner, SimulationRequest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deck", type=Path, required=True)
    parser.add_argument("--sideboard", type=Path)
    parser.add_argument("--opponent", type=Path, required=True)
    parser.add_argument("--opponent-sideboard", type=Path)
    parser.add_argument("--sideboard-plan", type=Path)
    starting_position = parser.add_mutually_exclusive_group()
    starting_position.add_argument("--play", action="store_true")
    starting_position.add_argument("--draw", action="store_true")
    parser.add_argument("--games", type=int, default=1)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--forge-home", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()

    request = SimulationRequest(
        deck=args.deck,
        sideboard=args.sideboard,
        opponent=args.opponent,
        opponent_sideboard=args.opponent_sideboard,
        sideboard_plan=args.sideboard_plan,
        play_draw="play" if args.play else "draw" if args.draw else None,
        games=args.games,
        seed=args.seed,
        timeout_seconds=args.timeout,
        output_dir=args.output_dir,
    )
    result = ForgeRunner(args.forge_home).run(request)
    print(result.result_path)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
